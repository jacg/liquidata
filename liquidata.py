from operator    import itemgetter, attrgetter
from functools   import reduce, wraps
from collections import namedtuple
from contextlib  import contextmanager
from argparse    import Namespace
from asyncio     import Future

import itertools as it
import copy



# TODO: Think carefully about what `use` should be. Test it.

# TODO: pipe.fn(RETURN_STRATEGY)  Exception or tuple

# TODO: make `star` (and consequently `*`) work reliably for all components

# TODO: named branches: out.X([...])

# TODO: add `keep` and `lose` as explicit names for filter and its complement

# TODO: grouping utilities

# TODO: count-filter: implicit {} in out: out.NAME({predicate}) -> .passed & .stopped

# TODO: send down one branch or other depending on predicate. dispatch, match, divert, split

# TODO: test for new exception types: SinkMissing, NeedAtLeastOneCoroutine

# TODO: think about whether `into` or `_Fold` should be the default `out`.

# TODO: find constant-space implementation of into

# TODO: implement _Fold in terms of into(reduce(...)), but only once into is constant-space

# TODO: automatic reinitialization of pipe.fn() after exception or other close.

# TODO: return namedtuple rather than namespace? Would allow unpacking.

# TODO: missing arg-lambda features
#         arg.a > 3;          arg[0] > 3;          arg.a > arg.b          arg.a  ; arg.a.b  arg[0,1]
# lambda x: x.a > 3; lambda x: x:[0] > 3; lambda a,b : a >     b; attrgetter('a');

# TODO: (a,b,c) without args or put should just be a pipe

# TODO: print_every(n)  [slice(None, None, n), print]

# TODO: test close_all for take, drop & co

# TODO, dropwhile / since / after

# TODO: Find public name for flat

# TODO: find public interface for Slice

# TODO: A [::] syntax for slice? Can we do better than `slice[start:stop:step]`? what about close_all?

# TODO: Give user choice whether sink or out is the default at end of pipe.
#       - pipe(source(s), ...) ; pipe(...)(s)
#       - pipe vs flow or some other name

# TODO: `get` and `item` distinguish between namespaces and dict; put assumes
#       namespaces. Give `put` a sibling? Make put detect automatically?

# TODO: utility for turning atomic stream into namespace

# TODO: operator module containing curried operators. Names uppercase or with
#       trailing underscore: standard: `gt`; ours: `GT` or `gt_`

# TODO: spy(side-effect),  spy.X(result-sink) as synonyms for
#          [side-effect], [out.X(result-sink)] ????

# TODO: add pipe.fn(Exception) alongside pipe.fn() and pipe.fn(tuple)

# TODO: typecheck: an alternative to __call__ which, rather than compiling and
#       composing coroutines, tries to perform typechecking on the composition
#       of the components.

# TODO: monads?


class pipe:

    def __new__(cls, *components):
        self = super().__new__(cls)
        if isinstance(components[0], source):
            self.__init__(*components[1:])
            return self(components[0].it)
        return self

    def __init__(self, *components):
        self._components = components

    def coroutine_and_outputs(self):
        decoded_components = map(decode_implicits, self._components)
        cor_out_pairs = tuple(c.coroutine_and_outputs() for c in decoded_components)
        coroutines = map(itemgetter(0), cor_out_pairs)
        out_groups = map(itemgetter(1), cor_out_pairs)
        return combine_coroutines(coroutines), it.chain(*out_groups)

    def __call__(self, source):
        coroutine, outputs = self.ensure_capped().coroutine_and_outputs()
        push(source, coroutine)
        return self.collect_returns(outputs)

    @staticmethod
    def collect_returns(outputs):
        outputs = tuple(outputs)
        returns = tuple(filter(lambda o: o.name == 'return', outputs))
        out_ns  = Namespace(**{o.name: o.future.result() for o in outputs})
        if len(vars(out_ns)) == len(returns) == 1:
            return vars(out_ns)['return']
        setattr(out_ns, 'return', tuple(r.future.result() for r in returns))
        return out_ns

    def pipe(self):
        return flat(self.fn(tuple))

    def fn(self, many=None):
        the_function = pipe._Fn(self._components)
        if many is tuple:
            return the_function
        def fn(*args):
            result = the_function(*args)
            if len(result) == 1: return result[0]
            if len(result)  > 1: return Many(result)
            else               : return Void
        return fn

    def ensure_capped(self):
        last = self._components[-1]
        is_capped = (isinstance(last, (sink, _Return, _Return.Name)) or
                     isinstance(last, _Name) and last.constructor == _Return.Name)
        return self if is_capped else pipe(*self._components, out)

    class _Fn:

        def __init__(self, components):
            self._pipe = pipe(*it.chain(components, [sink(self.accept_result)]))
            self._coroutine, _ = self._pipe.coroutine_and_outputs()

        def __call__(self, *args):
            self._returns = []
            self._coroutine.send(args)
            return tuple(self._returns)

        def accept_result(self, item):
            self._returns.append(item)

######################################################################
#    Component types                                                 #
######################################################################

class _Source(type):

    def __rrshift__(cls, other):
        return cls(other)

    __lshift__ = __rrshift__


class source(metaclass=_Source):

    def __init__(self, iterable):
        self.it = iterable


class _Component:
    pass


def component(loop):

    def __init__(self, *args):
        self._args = args

    def coroutine_and_outputs(self):
        if loop.__name__ == 'sink': return coroutine(loop(*self._args))(), ()
        else                      : return coroutine(loop(*self._args))  , ()

    def star(self):
        first, *rest = self._args
        return type(self)(_star(first), *rest)

    ns = dict(__init__=__init__, coroutine_and_outputs=coroutine_and_outputs, star=star)

    return type(loop.__name__, (_Component,), ns)


@component
def sink(fn):
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
def flat(fn):
    def flat_loop(downstream):
        with closing(downstream):
            while True:
                for item in fn(*(yield)):
                    downstream.send((item,))
    return flat_loop


@component
def join():
    def join_loop(downstream):
        with closing(downstream):
            while True:
                upstream, = yield
                for item in upstream:
                    downstream.send((item,))
    return join_loop
join = join()


@component
def _Filter(predicate, key=None):
    if key is None:
        key = lambda x:x
    def filter_loop(downstream):
        with closing(downstream):
            while True:
                args = yield
                if predicate(key(*args)):
                    downstream.send(args)
    return filter_loop


class _Branch(_Component):

    def __init__(self, *components):
        self._pipe = pipe(*components)

    def coroutine_and_outputs(self):
        sideways, outputs = self._pipe.ensure_capped().coroutine_and_outputs()
        @coroutine
        def branch_loop(downstream):
            with closing(sideways), closing(downstream):
                while True:
                    args = yield
                    sideways  .send(args)
                    downstream.send(args)
        return branch_loop, outputs


class into:

    def __init__(self, consumer):
        self.consumer = consumer


class _Return(_Component):

    def __init__(self, name, sink=None, initial=None, key=None):
        self._name = name

        if       isinstance(sink, set       ): sink = _CountFilter(sink, key=key)
        elif     isinstance(sink, into      ): sink = into_consumer(sink.consumer)
        elif not isinstance(sink, _Component): sink = _Fold(sink, initial=initial)
        # TODO: issue warning/error if initial is not None
        # TODO: set as implicit count filter?
        self._sink = sink

    def coroutine_and_outputs(self):
        future = Future()
        coroutine = self._sink.make_coroutine(future)
        return coroutine, (NamedFuture(self._name, future),)

    class Name(_Component):

        def __init__(self, name):
            self.name = name

        def __call__(self, *args, **kwds):
            return _Return(self.name, *args, **kwds)

        def coroutine_and_outputs(self):
            return _Return(self.name, into_consumer()).coroutine_and_outputs()

        @classmethod
        def no_name_given(cls, sink=into(list), *args, **kwds):
            return cls('return')(sink, *args, **kwds)


class _MultipleNames:

    def __init__(self, *names):
        self.names = names

    def __getattr__(self, name):
        return type(self)(*self.names, name)


class _On(_Component):

    def __init__(self, name):
        self.name = name

    def __call__(self, *components):
        return (getattr(get, self.name), components) >> getattr(put, self.name)


class _Put (_Component, _MultipleNames):

    def __rrshift__(self, action):
        self.pipe_fn = pipe(action).fn(tuple)
        return self

    __lshift__ = __rrshift__

    def coroutine_and_outputs(self):

        def attach_each_to_namespace(namespace, returned):
            for name, value in zip(self.names, returned):
                setattr(namespace, name, value)
            return namespace

        def attach_it_to_namespace(namespace, it):
            setattr(namespace, self.names[0], it)
            return namespace

        if len(self.names) > 1: make_return = attach_each_to_namespace
        else                  : make_return = attach_it_to_namespace

        @coroutine
        def put_loop(downstream):
            with closing(downstream):
                while True:
                    incoming_namespace, = (yield)
                    returns = self.pipe_fn(incoming_namespace)
                    for returned in returns:
                        outgoing_namespace = make_return(copy.copy(incoming_namespace), returned)
                        downstream.send((outgoing_namespace,))
        return put_loop, ()

DEBUG = False

def debug(x):
    if DEBUG:
        print(x)


class _Get:

    def __getattr__(self, name):
        return _Get.Attr(name)

    def __getitem__(self, key):
        return _Get.Item(key)

    class Attr:

        def __init__(self, name):
            self.names = [name]

        def __getattr__(self, name):
            self.names.append(name)
            return self

        def __call__(self, it):
            return attrgetter(*self.names)(it)

        def __mul__(self, action):
            if len(self.names) == 1:
                return (self,      action )
            return     (self, star(action))

        __rmul__ = __mul__

    class Item:

        def __init__(self, key):
            self.keys = [key]

        def __getitem__(self, key):
            self.keys.append(key)
            return self

        def __call__(self, it):
            return itemgetter(*self.keys)(it)


class _Item(_MultipleNames):

    def __call__(self, it):
        return itemgetter(*self.names)(it)

    __mul__ = _Get.Attr.__mul__

    __rmul__ = __mul__


class _NAME(_MultipleNames):

    def __call__(self, *items):
        if len(self.names) != 1:
            items = items[0]
        assert len(self.names) == len(items)
        return Namespace(**{n: i for (n,i) in zip(self.names, items)})


class _Name(_Component):

    def __init__(self, constructor):
        self.constructor = constructor

    def __getattr__(self, name):
        return self.constructor(name)

    def __call__(self, *args, **kwds):
        return self.constructor.no_name_given(*args, **kwds)

    def coroutine_and_outputs(self):
        return self.constructor.no_name_given().coroutine_and_outputs()

out  = _Name(_Return.Name)
on   = _Name(_On)
put  = _Name(_Put)
get  = _Get()
item = _Name(_Item)
name = _Name(_NAME)


class _Fold(_Component):

    # TODO: future-sinks should not appear at toplevel, as they must be wrapped
    # in an output. Detect and report error at conversion from implicit

    def __init__(self, fn, initial=None, consumer=lambda x:x):
        self._fn = fn
        self._initial = initial
        self._consumer = consumer

    def make_coroutine(self, future):
        binary_function = self._fn
        @coroutine
        def fold_loop(future):
            if self._initial is None:
                try:
                    accumulator, = (yield)
                except StopIteration:
                    # TODO: message about not being able to run on an empty stream.
                    pass
            else:
                accumulator = self._initial
            try:
                while True:
                    accumulator = binary_function(accumulator, *(yield))
            finally:
                future.set_result(self._consumer(accumulator))
        return fold_loop(future)


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

    def coroutine_and_outputs(self):
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
for op in           (neg, pos, abs):
    _Arg.install_unary_op(op)

arg = _Arg()

######################################################################

# Most component names don't have to be used explicitly, because plain python
# types have implicit interpretations as components
def decode_implicits(it):
    if isinstance(it, _Component): return it
    if isinstance(it, pipe      ): return it.pipe()
    if isinstance(it, list      ): return _Branch(*it)
    if isinstance(it, tuple     ): return  pipe(*it).pipe()
    if isinstance(it, set       ): return _Filter( next(iter(it)))
    if isinstance(it, dict      ): return _Filter(*next(iter(it.items())))
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
        raise NeedAtLeastOneCoroutine
    if not hasattr(coroutines[-1], 'close'):
        raise SinkMissing(f'No sink at end of {coroutines}')
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


def into_consumer(consumer=list):
    def append(the_list, element):
        the_list.append(element)
        return the_list
    return _Fold(append, [], consumer)


def star(fn):
    fn = decode_implicits(fn)
    if isinstance(fn, _Map):
        fn = fn._args[0]
    if isinstance(fn, (flat, _Filter)):
        return fn.star()
    return _star(fn)

def _star(fn):
    def star(args):
        return fn(*args)
    return star

# TODO: this was quickly added for use in the tutorial. It requires careful
#       thought about how general it can be and what the cleanest interface is.
#       It is still untested!
def use(fn, *args, **kwds):
    def use(arg1):
        return fn(arg1, *args, **kwds)
    return use

######################################################################

class LiquiDataException(Exception): pass
class SinkMissing            (LiquiDataException): pass
class NeedAtLeastOneCoroutine(LiquiDataException): pass

######################################################################

class Many(tuple):

    def __str__(self):
        if self: return f'Many{tuple(self)}'
        else   : return 'Void'

    def __repr__(self):
        if self: return f'Many({tuple(self)})'
        else   : return 'Void'

Void = Many()

NamedFuture = namedtuple('NamedFuture', 'name, future')
