from functools  import reduce, wraps
from contextlib import contextmanager
from itertools  import chain
from argparse   import Namespace
from asyncio    import Future


class Network:

    def __init__(self, *components):
        self._components = tuple(map(decode_implicits, components))

    def __call__(self, source):
        pipe, outputs = components_to_single_coroutine_and_outputs(self._components)
        push(source, pipe)
        return Namespace(**{name: future.result() for name, future in outputs.items()})


DEBUG = True

def debug(*args, **kwds):
    if DEBUG: print(*args, **kwds)

def components_to_single_coroutine_and_outputs(components):
    pass                                                                                ; debug(f'components    {components}')
    components_with_futures = tuple(map(meth.inject_futures  , components))             ; debug(f'with_futures  {components_with_futures}')
    outputs                 = tuple(map(meth.get_outputs     , components_with_futures)); debug(f'outputs       {outputs}')
    coroutines              = tuple(map(meth.fresh_coroutine , components_with_futures)); debug(f'coroutines    {coroutines}')
    unified_coroutine       = combine_coroutines(              coroutines)              ; debug(f'unified       {unified_coroutine}')
    return unified_coroutine, dict(chain(*outputs))


# components:
#
# source
# map
# filter
# sink:   fold, side-effect, side-effect with result
# branch
# get
# put
# call

######################################################################
#    Component types                                                 #
######################################################################

class Component:

    def fresh_coroutine(self):
        raise NotImplementedError

    def set_gets(self, available_names):
        # Must not mutate self: return a modified copy, if needed
        return self

    def unresolved_gets(self):
        pass

    def inject_futures(self):
        return self

    def get_outputs(self):
        return ()

class Sink(Component):

    def __init__(self, fn):
        self._fn = fn

    def fresh_coroutine(self):
        def sink_loop():
            while True:
                self._fn((yield))
        return coroutine(sink_loop)()


class Map(Component):

    def __init__(self, fn):
        self._fn = fn

    def fresh_coroutine(self):
        def map_loop(target):
                with closing(target):
                    while True:
                        target.send(self._fn((yield)))
        return coroutine(map_loop)


class Filter(Component):

    def __init__(self, predicate):
        self._predicate = predicate

    def fresh_coroutine(self):
        predicate = self._predicate
        def filter_loop(target):
            with closing(target):
                while True:
                    val = yield
                    if predicate(val):
                        target.send(val)
        return coroutine(filter_loop)


class Branch(Component):

    def __init__(self, *components):
        self._components = tuple(map(decode_implicits, components))

    def fresh_coroutine(self):
        sideways = combine_coroutines(tuple(map(meth.fresh_coroutine, self._components)))
        @coroutine
        def branch_loop(downstream):
            with closing(sideways), closing(downstream):
                while True:
                    val = yield
                    sideways  .send(val)
                    downstream.send(val)
        return branch_loop

    def inject_futures(self): return Branch(*map(meth.inject_futures, self._components))
    def get_outputs   (self): return  chain(*map(meth.get_outputs   , self._components))


class Output(Component):

    class make:

        def __getattribute__(self, name):
            return Output(name)

    def __init__(self, name, sink=None):
        self._name = name
        self._sink = sink

    def __call__(self, sink_with_return_value):
        if not isinstance(sink_with_return_value, Component):
            sink_with_return_value = Fold(sink_with_return_value)
        return Output(self._name, sink_with_return_value)

    def inject_futures(self):
        return OutputWithFuture(self._name, self._sink)

out = Output.make()


class OutputWithFuture(Component):

    def __init__(self, name, sink):
        self._name = name
        self._sink = sink
        self._future = Future()

    def inject_futures(self):
        raise Exception('Future already injected')

    def fresh_coroutine(self):
        return self._sink.fresh_coroutine_from_future(self._future)

    def get_outputs(self):
        return ((self._name, self._future),)

class Fold(Component):

    def __init__(self, fn, initial=None):
        self._fn = fn
        self._initial = initial

    def inject_futures(self):
        raise Exception("Injecting futures into a Fold should be done by the Output that wraps it")

    def fresh_coroutine_from_future(self, future):
    #def reduce_factory(binary_function, initial=None):
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


    def TODO(self):
        # Future sinks should not appear at the top level. Come up with a name
        # for this method and hook into it somewhere, probably before
        # decode_implicits
        raise Exception('Fold must be wrapped in an out, otherwise the output will be lost')


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
