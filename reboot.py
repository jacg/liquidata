from operator   import itemgetter
from functools  import reduce, wraps
from contextlib import contextmanager
from itertools  import chain
from argparse   import Namespace
from asyncio    import Future


class Network:

    def __init__(self, *components):
        self._components = tuple(map(decode_implicits, components))

    def __call__(self, source):
        coroutine, outputs = self.coroutine_and_outputs()
        push(source, coroutine)
        outputs = tuple(outputs)
        print(outputs)
        return Namespace(**{name: future.result() for name, future in outputs})

    def coroutine_and_outputs(self):
        cor_out_pairs = tuple(map(meth.coroutine_and_outputs, self._components))
        coroutines = map(itemgetter(0), cor_out_pairs)
        out_groups = map(itemgetter(1), cor_out_pairs)
        return combine_coroutines(coroutines), chain(*out_groups)


# components:
#
# map
# filter
# sink:   fold, side-effect, side-effect with result
# branch
# get
# out
# call

######################################################################
#    Component types                                                 #
######################################################################

class Component:
    pass

class Sink(Component):

    def __init__(self, fn):
        self._fn = fn

    def coroutine_and_outputs(self):
        def sink_loop():
            while True:
                self._fn((yield))
        return coroutine(sink_loop)(), ()


class Map(Component):

    def __init__(self, fn):
        self._fn = fn

    def coroutine_and_outputs(self):
        def map_loop(target):
                with closing(target):
                    while True:
                        target.send(self._fn((yield)))
        return coroutine(map_loop), ()


class Filter(Component):

    def __init__(self, predicate):
        self._predicate = predicate

    def coroutine_and_outputs(self):
        predicate = self._predicate
        def filter_loop(target):
            with closing(target):
                while True:
                    val = yield
                    if predicate(val):
                        target.send(val)
        return coroutine(filter_loop), ()


class Branch(Component):

    def __init__(self, *components):
        self._components = tuple(map(decode_implicits, components))

    def coroutine_and_outputs(self):
        sideways, outputs = Network.coroutine_and_outputs(self)
        @coroutine
        def branch_loop(downstream):
            with closing(sideways), closing(downstream):
                while True:
                    val = yield
                    sideways  .send(val)
                    downstream.send(val)
        return branch_loop, outputs


class Output(Component):

    class make:

        def __getattribute__(self, name):
            return Output(name)

    def __init__(self, name, sink=None):
        self._name = name
        self._sink = sink

    def __call__(self, sink_with_return_value, initial=None):
        if not isinstance(sink_with_return_value, Component):
            sink_with_return_value = Fold(sink_with_return_value, initial=initial)
        # TODO: set as implicit count filter?
        return Output(self._name, sink_with_return_value)

    def coroutine_and_outputs(self):
        future = Future()
        coroutine = self._sink.make_coroutine(future)
        return coroutine, ((self._name, future),)

out = Output.make()


class Fold(Component):

    # TODO: future-sinks should not appear at toplevel, as they must be wrapped
    # in an output. Detect and report error at conversion from implicit

    def __init__(self, fn, initial=None):
        self._fn = fn
        self._initial = initial

    def make_coroutine(self, future):
        binary_function = self._fn
        @coroutine
        def reduce_loop(future):
            if self._initial is None:
                try:
                    accumulator = (yield)
                except StopIteration:
                    # TODO: message about not being able to run on an empty stream.
                    # Try to link it to variable names in the network?
                    pass
            else:
                accumulator = self._initial
            try:
                while True:
                    accumulator = binary_function(accumulator, (yield))
            finally:
                future.set_result(accumulator)
        return reduce_loop(future)


######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def decode_implicits(it):
    if isinstance(it, Component): return it
    if isinstance(it, list     ): return Branch(*it)
    if isinstance(it, tuple    ): return Sink  (*it)
    if isinstance(it, set      ): return Filter(next(iter(it)))
    else                        : return Map(it)


class dispatch:

    def __getattribute__(self, name):
        return lambda obj: getattr(obj, name)()
meth = dispatch()


def push(source, pipe):
    for item in source:
        pipe.send(item)
    pipe.close()


def combine_coroutines(coroutines):
    coroutines = tuple(coroutines)
    if not coroutines:
        raise Exception('Need at least one coroutine')
    if not hasattr(coroutines[-1], 'close'):
        raise Exception(f'No sink at end of {coroutines}')
    def apply(arg, fn):
        return fn(arg)
    return reduce(apply, reversed(coroutines))


def coroutine(generator_function):
    @wraps(generator_function)
    def proxy(*args, **kwds):
        the_coroutine = generator_function(*args, **kwds)
        next(the_coroutine)
        return the_coroutine
    return proxy


@contextmanager
def closing(target):
    try:     yield
    finally: target.close()
