from functools  import reduce, wraps
from contextlib import contextmanager
from itertools  import chain
from argparse   import Namespace


class Network:

    def __init__(self, *components):
        self._components = components

    def __call__(self):
        source, *raw_components = self._components
        pipe, outputs = raw_components_to_single_coroutine_and_outputs(raw_components)

        for item in source:
            pipe.send(item)
        pipe.close()

        return Namespace(**{name: future.result() for name, future in outputs})



def raw_components_to_single_coroutine_and_outputs(raw_components):
    pipe_components = map(implicit_to_component, raw_components)
    components_with_futures = tuple(map(meth.inject_futures, pipe_components))
    outputs = dict(chain(*map(meth.get_outputs, components_with_futures)))
    pipe_coroutines = tuple(map(meth.fresh_coroutine, components_with_futures))
    pipe = combine_coroutines(pipe_coroutines)
    return pipe, outputs


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
        pass

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
        self._components = components

    def fresh_coroutine(self):
        sideways, _ = raw_components_to_single_coroutine_and_outputs(self._components)
        @coroutine
        def branch_loop(downstream):
            with closing(sideways), closing(downstream):
                while True:
                    val = yield
                    sideways  .send(val)
                    downstream.send(val)
        return branch_loop


######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def implicit_to_component(it):
    if isinstance(it, Component): return it
    if isinstance(it, list     ): return Branch(*it)
    if isinstance(it, tuple    ): return Sink  (*it)
    if isinstance(it, set      ): return Filter(next(iter(it)))
    else                        : return Map(it)


class dispatch:

    def __getattribute__(self, name):
        return lambda obj: getattr(obj, name)()
meth = dispatch()


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
