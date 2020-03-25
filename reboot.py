from operator   import itemgetter, attrgetter
from functools  import reduce, wraps
from contextlib import contextmanager
from argparse   import Namespace
from asyncio    import Future

import itertools as it
import copy

# TODO: fill slots in OpenPipe.fn at call time: OpenPipe.fn(not only here)(data, but also here)

# TODO: count-filter: implicit {} in out: out.NAME({predicate}) -> .passed & .stopped

# TODO: string as implicit pick

# TODO: get inside out

# TODO: call


class _Pipe:

    def __init__(self, components):
        self._components = tuple(map(decode_implicits, components))
        last = self._components[-1]
        if isinstance(last, Map):
            last.__class__ = Sink

    def coroutine_and_outputs(self, bindings):
        cor_out_pairs = tuple(c.coroutine_and_outputs(bindings) for c in self._components)
        coroutines = map(itemgetter(0), cor_out_pairs)
        out_groups = map(itemgetter(1), cor_out_pairs)
        return combine_coroutines(coroutines), it.chain(*out_groups)


class Flow:

    def __init__(self, *components):
        self._pipe = _Pipe(components)

    def __call__(self, source, **bindings):
        coroutine, outputs = self._pipe.coroutine_and_outputs(bindings)
        push(source, coroutine)
        outputs = tuple(outputs)
        print(outputs)
        return Namespace(**{name: future.result() for name, future in outputs})


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

    def coroutine_and_outputs(self, bindings):
        @coroutine
        def sink_loop():
            while True:
                self._fn(*(yield))
        return sink_loop(), ()


class Map(Component):

    def __init__(self, fn):
        self._fn = fn

    def coroutine_and_outputs(self, bindings):
        @coroutine
        def map_loop(target):
                with closing(target):
                    while True:
                        target.send((self._fn(*(yield)),))
        return map_loop, ()


class FlatMap(Component):

    def __init__(self, fn):
        self._fn = fn

    def coroutine_and_outputs(self, bindings):
        @coroutine
        def flatmap_loop(target):
                with closing(target):
                    while True:
                        for item in self._fn(*(yield)):
                            target.send((item,))
        return flatmap_loop, ()


class Filter(Component):

    def __init__(self, predicate):
        self._predicate = predicate

    def coroutine_and_outputs(self, bindings):
        predicate = self._predicate
        @coroutine
        def filter_loop(target):
            with closing(target):
                while True:
                    args = yield
                    if predicate(*args):
                        target.send(args)
        return filter_loop, ()


class Branch(Component):

    def __init__(self, *components):
        self._pipe = _Pipe(components)

    def coroutine_and_outputs(self, bindings):
        sideways, outputs = self._pipe.coroutine_and_outputs(bindings)
        @coroutine
        def branch_loop(downstream):
            with closing(sideways), closing(downstream):
                while True:
                    args = yield
                    sideways  .send(args)
                    downstream.send(args)
        return branch_loop, outputs


class Output(Component):

    def __init__(self, name, sink=None):
        self._name = name
        self._sink = sink

    def coroutine_and_outputs(self, bindings):
        future = Future()
        coroutine = self._sink.make_coroutine(future)
        return coroutine, ((self._name, future),)

    class Name(Component):

        def __init__(self, name):
            self.name = name

        def __call__(self, sink, initial=None):
            if not isinstance(sink, Component):
                # TODO: issue warning/error if initial is not None
                sink = Fold(sink, initial=initial)
            # TODO: set as implicit count filter?
            return Output(self.name, sink)

        def coroutine_and_outputs(self, bindings):
            def append(the_list, element):
                the_list.append(element)
                return the_list
            collect_into_list = Fold(append, [])
            return Output(self.name, collect_into_list).coroutine_and_outputs(bindings)


class Input(Component):

    def __init__(self, name):
        self.name = name

    def coroutine_and_outputs(self, bindings):
        return decode_implicits(bindings[self.name]).coroutine_and_outputs(bindings)

class MultipleNames:

    def __init__(self, *names):
        self.names = names

    def __getattr__(self, name):
        return type(self)(*self.names, name)

class Pick(MultipleNames, Component):

    def coroutine_and_outputs(self, bindings):
        return Map(itemgetter(*self.names)).coroutine_and_outputs(bindings)


class On(Component):

    def __init__(self, name):
        self.name = name

    def __call__(self, *components):
        # TODO: shoudn't really mutate self
        self.process_one_item = OpenPipe(*components).fn()
        return self

    def coroutine_and_outputs(self, bindings):
        @coroutine
        def on_loop(downstream):
            with closing(downstream):
                while True:
                    namespace, = (yield)
                    for returned in self.process_one_item(namespace[self.name]):
                        updated_namespace = namespace.copy()
                        updated_namespace[self.name] = returned
                        downstream.send((updated_namespace,))
        return on_loop, ()


class Args(MultipleNames): pass
class Put (MultipleNames): pass

class ArgsPut(Component):

    def __init__(self, *components):
        cs = list(components)
        self.args = cs.pop(0).names if isinstance(cs[ 0], Args) else ()
        self.put  = cs.pop( ).names if isinstance(cs[-1], Put ) else ()
        self.pipe_fn = OpenPipe(*cs).fn()
        print(f'self.args: {self.args}')
        print(f'self.put: {self.put}')

    def coroutine_and_outputs(self, bindings):

        def attach_each_to_namespace(namespace, returned):
            for name, value in zip(self.put, returned):
                namespace[name] = value
            return namespace
        def attach_it_to_namespace(namespace, it):
            namespace[self.put[0]] = it
            return namespace
        def return_directly(_, returned): return returned

        def         wrap_in_tuple(x): return (x              ,)
        def get_and_wrap_in_tuple(x): return (x[self.args[0]],)

        if   len(self.args)  > 1: get_args = itemgetter(*self.args)
        elif len(self.args) == 1: get_args = get_and_wrap_in_tuple
        else                    : get_args =         wrap_in_tuple

        if   len(self.put)  > 1: make_return = attach_each_to_namespace
        elif len(self.put) == 1: make_return = attach_it_to_namespace
        else                   : make_return = return_directly

        @coroutine
        def args_put_loop(downstream):
            with closing(downstream):
                while True:
                    incoming, = (yield)
                    print(f'incoming: {incoming}')
                    args = get_args(incoming)
                    print(f'argsXXX: {args}')
                    generated_returns = self.pipe_fn(*args)
                    print(f'generated_returns: {generated_returns}')
                    for returned in generated_returns:
                        print(f'make_return: {make_return}')
                        print(f'returned: {returned}')
                        # TODO: eliminate unnecessary first copy?
                        outgoing = make_return(copy.copy(incoming), returned)
                        print(f'outgoing: {outgoing}')
                        downstream.send((outgoing,))
        return args_put_loop, ()




class Name:

    def __init__(self, callable):
        self.callable = callable

    def __getattr__(self, name):
        return self.callable(name)


out  = Name(Output.Name)
get  = Name(Input)
pick = Name(Pick)
on   = Name(On)
args = Name(Args)
put  = Name(Put)

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
                    accumulator, = (yield)
                except StopIteration:
                    # TODO: message about not being able to run on an empty stream.
                    # Try to link it to variable names in the network?
                    pass
            else:
                accumulator = self._initial
            try:
                while True:
                    accumulator = binary_function(accumulator, *(yield))
            finally:
                future.set_result(accumulator)
        return reduce_loop(future)


class OpenPipe:

    def __init__(self, *components):
        # TODO: should disallow branches (unless we implement joins)
        self._components = components

    def fn  (self, **bindings): return OpenPipe._Fn(self._components, bindings)
    def pipe(self, **bindings): return FlatMap     (self.fn(        **bindings))

    class _Fn:

        def __init__(self, components, bindings):
            self._pipe = _Pipe(it.chain(components, [Sink(self.accept_result)]))
            self._coroutine, _ = self._pipe.coroutine_and_outputs(bindings)

        def __call__(self, *args):
            self._returns = []
            self._coroutine.send(args)
            return tuple(self._returns)

        def accept_result(self, item):
            self._returns.append(item)




class Slice(Component):

    def __init__(self, *args, close_all=False):
        spec = slice(*args)
        start, stop, step = spec.start, spec.stop, spec.step
        print(f"spec 0: {spec}")
        if start is not None and start <  0: raise ValueError('slice requires start >= 0')
        if stop  is not None and stop  <  0: raise ValueError('slice requires stop >= 0')
        if step  is not None and step  <= 0: raise ValueError('slice requires step > 0')

        if start is None: start = 0
        if step  is None: step  = 1
        if stop  is None: stopper = it.count()
        else            : stopper = range((stop - start + step - 1) // step)
        self.spec = slice(start, stop, step)
        print(f"spec 1: {self.spec}")
        self.stopper = stopper
        self.close_all = close_all

    def coroutine_and_outputs(self, bindings):
        start, stop, step = attrgetter('start', 'stop', 'step')(self.spec)
        stopper, close_all = attrgetter('stopper', 'close_all')(self)
        @coroutine
        def slice_loop(downstream):
            with closing(downstream):
                for _ in range(start)           : yield
                for _ in stopper:
                    downstream.send((yield))
                    for _ in range(step - 1)    : yield

                yield

                if close_all: raise StopPipeline
                while True:
                    yield
        return slice_loop, ()

######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def decode_implicits(it):
    if isinstance(it, Component): return it
    if isinstance(it, list     ): return Branch(*it)
    if isinstance(it, tuple    ): return ArgsPut(*it)
    if isinstance(it, set      ): return Filter(next(iter(it)))
    else                        : return Map(it)


def push(source, pipe):
    for item in source:
        pipe.send((item,))
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

######################################################################

class StopPipeline(Exception): pass
