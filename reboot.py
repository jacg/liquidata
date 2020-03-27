from operator   import itemgetter, attrgetter
from functools  import reduce, wraps
from contextlib import contextmanager
from argparse   import Namespace
from asyncio    import Future

import itertools as it
import copy


# TODO: out.X(foldfn)    out(foldfn)  for direct return?

# TODO: return single value rather than namespace, when appropriate (implicit
#       when only one out? or explicit choice?). Implicit naming of flow's
#       sink.

# TODO: return namedtuple rather than namespace? Would allow unpacking.

# TODO: Now that get is called slot,  use `get.a.b` as itemgetter('a','b')

# TODO: missing arg-lambda features
#         arg.a > 3;          arg[0] > 3;          arg.a > arg.b          arg.a  ; arg.a.b  arg[0,1]
# lambda x: x.a > 3; lambda x: x:[0] > 3; lambda a,b : a >     b; attrgetter('a');

# TODO: something like Haskell's on or Python's key. Where is it useful beyond
#       filter? Maybe this is where {pred:key} would be used?

# TODO: (a,b,c) without args or put should just be a pipe

# TODO: print_every(n)  [slice(None, None, n), print]

# TODO: test close_all for take, drop & co

# TODO, dropwhile / since / after

# TODO: Find public name for FlatMap

# TODO: find public interface for Slice

# TODO: A [::] syntax for slice? Can we do better than `slice[start:stop:step]`? what about close_all?

# TODO: Extend `args` & `put` to work on namedtuples, Namespaces, sequences.
#       [Give it a mutate option? Don't bother, just switch to persistent data
#       structures]

# TODO: `pick.x, f` works. Think about what `pick.x(f)` could mean.

# TODO: args-put syntax for turning atomic stream into namespace

# TODO: operator module containing curried operators. Names uppercase or with
#       trailing underscore: standard: `gt`; ours: `GT` or `gt_`

# TODO: fill slots in pipe.fn at call time: pipe.fn(not only here)(data, but also here)

# TODO: count-filter: implicit {} in out: out.NAME({predicate}) -> .passed & .stopped

# TODO: string as implicit pick

# TODO: get inside out

# TODO: call / bind:   bind(1, get.a, key=get.b)(f) -> f(1, a, key=b)

# TODO: spy(side-effect),  spy.X(result-sink) as synonyms for
#          [side-effect], [out.X(result-sink)] ????

# TODO: option to pipe.fn to assume that the pipe is a map, and therefore
# return the first (hopefully existent and only) thing yielded.

# TODO: send down one branch or other depending on predicate. Dispatch. Match

# TODO: monads?

class _Pipe:

    def __init__(self, components):
        self._components = tuple(map(decode_implicits, components))
        last = self._components[-1]
        if isinstance(last, _Map):
            last.__class__ = _Sink

    def coroutine_and_outputs(self, bindings):
        cor_out_pairs = tuple(c.coroutine_and_outputs(bindings) for c in self._components)
        coroutines = map(itemgetter(0), cor_out_pairs)
        out_groups = map(itemgetter(1), cor_out_pairs)
        return combine_coroutines(coroutines), it.chain(*out_groups)


class flow:

    def __init__(self, *components):
        self._pipe = _Pipe(components)

    def __call__(self, source, **bindings):
        coroutine, outputs = self._pipe.coroutine_and_outputs(bindings)
        push(source, coroutine)
        outputs = tuple(outputs)
        return Namespace(**{name: future.result() for name, future in outputs})


######################################################################
#    Component types                                                 #
######################################################################

class _Component:
    pass


def component(loop):

    def __init__(self, fn):
        self._fn = fn

    def coroutine_and_outputs(self, bindings):
        if loop.__name__ == '_Sink': return coroutine(loop(self._fn))(), ()
        else                       : return coroutine(loop(self._fn))  , ()

    ns = dict(__init__=__init__, coroutine_and_outputs=coroutine_and_outputs)

    return type(loop.__name__, (_Component,), ns)


@component
def _Sink(fn):
    def sink_loop():
        while True:
            fn(*(yield))
    return sink_loop


@component
def _Map(fn):
    def map_loop(downstream):
        with closing(downstream):
            while True:
                downstream.send((fn(*(yield)),))
    return map_loop


@component
def FlatMap(fn):
    def flatmap_loop(downstream):
        with closing(downstream):
            while True:
                for item in fn(*(yield)):
                    downstream.send((item,))
    return flatmap_loop


@component
def _Filter(predicate):
    def filter_loop(downstream):
        with closing(downstream):
            while True:
                args = yield
                if predicate(*args):
                    downstream.send(args)
    return filter_loop


class _Branch(_Component):

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


class _Output(_Component):

    def __init__(self, name, sink=None):
        self._name = name
        self._sink = sink

    def coroutine_and_outputs(self, bindings):
        future = Future()
        coroutine = self._sink.make_coroutine(future)
        return coroutine, ((self._name, future),)

    class Name(_Component):

        def __init__(self, name):
            self.name = name

        def __call__(self, sink, initial=None):
            if not isinstance(sink, _Component):
                # TODO: issue warning/error if initial is not None
                sink = _Fold(sink, initial=initial)
            # TODO: set as implicit count filter?
            return _Output(self.name, sink)

        def coroutine_and_outputs(self, bindings):
            def append(the_list, element):
                the_list.append(element)
                return the_list
            collect_into_list = _Fold(append, [])
            return _Output(self.name, collect_into_list).coroutine_and_outputs(bindings)


class _Slot(_Component):

    def __init__(self, name):
        self.name = name

    def coroutine_and_outputs(self, bindings):
        return decode_implicits(bindings[self.name]).coroutine_and_outputs(bindings)

class _MultipleNames:

    def __init__(self, *names):
        self.names = names

    def __getattr__(self, name):
        return type(self)(*self.names, name)

class _Pick(_MultipleNames, _Component):

    def coroutine_and_outputs(self, bindings):
        return _Map(itemgetter(*self.names)).coroutine_and_outputs(bindings)


class _On(_Component):

    def __init__(self, name):
        self.name = name

    def __call__(self, *ARGS):
        return tuple(it.chain([getattr(args, self.name)],
                              ARGS,
                              [getattr(put, self.name)]))


class _Args(_MultipleNames): pass
class _Put (_MultipleNames): pass

DEBUG = False

def debug(x):
    if DEBUG:
        print(x)

class _ArgsPut(_Component):

    def __init__(self, *components):
        cs = list(components)
        self.args = cs.pop(0).names if isinstance(cs[ 0], _Args) else ()
        self.put  = cs.pop( ).names if isinstance(cs[-1], _Put ) else ()
        self.pipe_fn = pipe(*cs).fn()
        debug(f'components: {cs}')
        debug(f'self.args: {self.args}')
        debug(f'self.put: {self.put}')

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
                    debug(f'incoming: {incoming}')
                    args = get_args(incoming)
                    debug(f'argsXXX: {args}')
                    generated_returns = self.pipe_fn(*args)
                    debug(f'generated_returns: {generated_returns}')
                    for returned in generated_returns:
                        debug(f'make_return: {make_return}')
                        debug(f'returned: {returned}')
                        # TODO: eliminate unnecessary first copy?
                        outgoing = make_return(copy.copy(incoming), returned)
                        debug(f'outgoing: {outgoing}')
                        downstream.send((outgoing,))
        return args_put_loop, ()




class _Name:

    def __init__(self, callable):
        self.callable = callable

    def __getattr__(self, name):
        return self.callable(name)


out  = _Name(_Output.Name)
slot = _Name(_Slot)
pick = _Name(_Pick)
on   = _Name(_On)
args = _Name(_Args)
put  = _Name(_Put)


class _Fold(_Component):

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


class pipe:

    def __init__(self, *components):
        # TODO: should disallow branches (unless we implement joins)
        self._components = components

    def fn  (self, **bindings): return pipe._Fn(self._components, bindings)
    def pipe(self, **bindings): return FlatMap (self.fn(        **bindings))

    class _Fn:

        def __init__(self, components, bindings):
            self._pipe = _Pipe(it.chain(components, [_Sink(self.accept_result)]))
            self._coroutine, _ = self._pipe.coroutine_and_outputs(bindings)

        def __call__(self, *args):
            self._returns = []
            self._coroutine.send(args)
            return tuple(self._returns)

        def accept_result(self, item):
            self._returns.append(item)


class Slice(_Component):

    def __init__(self, *args, close_all=False):
        spec = slice(*args)
        start, stop, step = spec.start, spec.stop, spec.step
        if start is not None and start <  0: raise ValueError('slice requires start >= 0')
        if stop  is not None and stop  <  0: raise ValueError('slice requires stop >= 0')
        if step  is not None and step  <= 0: raise ValueError('slice requires step > 0')

        if start is None: start = 0
        if step  is None: step  = 1
        if stop  is None: stopper = it.count()
        else            : stopper = range((stop - start + step - 1) // step)
        self.spec = slice(start, stop, step)
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


class _Arg:

    @classmethod
    def install_binary_op(cls, op):

        from operator import sub, floordiv, truediv
        swap = sub, floordiv, truediv

        # TODO: set __name__ etc
        def __op__(self, rhs):
            def implementation(lhs):
                return op(lhs, rhs)
            return implementation

        def swapped(self, rhs):
            def implementation(lhs):
                return op(rhs, lhs)
            return implementation

        setattr(cls,  f'__{op.__name__}__', __op__)
        setattr(cls, f'__r{op.__name__}__', __op__ if op not in swap else swapped)

    @classmethod
    def install_unary_op(cls, op):
        def __op__(self):
            def implementation(operand):
                return op(operand)
            return implementation

        setattr(cls,  f'__{op.__name__}__', __op__)

    def __getitem__(self, index_or_key):
        return itemgetter(index_or_key)

    def __getattr__(self, name):
        return attrgetter(name)

    def __call__(self, *args, **kwds):
        def implementation(fn):
            return fn(*args, **kwds)
        return implementation


from operator import lt, gt, le, ge, eq, ne, add, sub, mul, floordiv, truediv
for op in           (lt, gt, le, ge, eq, ne, add, sub, mul, floordiv, truediv):
    _Arg.install_binary_op(op)

from operator import neg, pos
for op in           (neg, pos):
    _Arg.install_unary_op(op)

arg = _Arg()

######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def decode_implicits(it):
    if isinstance(it, _Component): return it
    if isinstance(it, pipe)      : return it.pipe()
    if isinstance(it, list     ) : return _Branch(*it)
    if isinstance(it, tuple    ) : return _ArgsPut(*it)
    if isinstance(it, set      ) : return _Filter(next(iter(it)))
    else                         : return _Map(it)


def push(source, pipe):
    for item in source:
        try:
            pipe.send((item,))
        except StopPipeline:
            break
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

######################################################################

def take(n, **kwds): return Slice(None, n, **kwds)
def drop(n, **kwds): return Slice(n, None, **kwds)


@component
def until(predicate):
    def until_loop(downstream):
        with closing(downstream):
            while True:
                args = yield
                if predicate(*args):
                    break
                else:
                    downstream.send(args)
            while True:
                yield
    return until_loop


def while_(predicate): return until(lambda x: not predicate(x))
