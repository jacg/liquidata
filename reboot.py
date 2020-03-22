from functools import reduce, wraps


class Network:

    def __init__(self, *components):
        self._components = components

    def __call__(self):
        source, *pipe_components = self._components
        pipe_coroutines = tuple(map(fresh_coroutine, pipe_components))
        pipe = combine_coroutines(pipe_coroutines)

        for item in source:
            pipe.send(item)
        pipe.close()


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


class Sink(Component):

    def __init__(self, fn):
        self._fn = fn

    def fresh_coroutine(self):
        def sink_loop():
            while True:
                self._fn((yield))
        return coroutine(sink_loop)()


######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def convert_to_component(it):
    if isinstance(it, Component): return it
    # if isinstance(it, list     ): return Branch(*it)
    # if isinstance(it, tuple    ): return Fold  (*it)
    # if isinstance(it, set      ): return Filter(next(iter(it)))
    # else                        : return Map(it)

def fresh_coroutine(component):
    return component.fresh_coroutine()

def combine_coroutines(coroutines):
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
