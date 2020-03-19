from collections import deque
from contextlib  import contextmanager
from functools   import reduce
from functools   import wraps

class source:

    def __init__(self, iterable=None, *, pipe=None):
        self._source = iterable
        # appended to the source by operators `-` and `+`
        self._pipe   = deque() if pipe is None else pipe

    # TODO: reimplement all of these operators with multimethods
    def __sub__(self, other):
        if isinstance(other, pipe):
            return self._extend_pipe_with_pipe(other)
        if isinstance(other, sink):
            return ready(source=self, sink=other)
        if isinstance(other, source):
            raise TypeError
        return self._extend_pipe_with_coroutine(_fn_to_map_pipe(other))

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self._extend_pipe_with_coroutine(_fn_to_filter_pipe(other))

    def __rshift__(self, other):
        if isinstance(other, (source, pipe)):
            raise TypeError
        return ready(source=self, sink=sink(other))

    def __truediv__(self, other):
        sink_function  = other._fn if isinstance(other, sink) else other
        sink_coroutine = _fn_to_sink_coroutine(sink_function)
        return self._extend_pipe_with_coroutine(_coroutine_to_branch_coroutine(sink_coroutine))

    def _extend_pipe_with_coroutine(self, coroutine):
        extended_pipe = self._pipe.copy()
        extended_pipe.appendleft(coroutine)
        return source(iterable=self._source, pipe=extended_pipe)

    def _extend_pipe_with_pipe(self, the_pipe):
        extended_pipe = the_pipe._pipe + self._pipe
        return source(iterable=self._source, pipe=extended_pipe)


class pipe:

    def __init__(self, fn=None, *, pipe=None):
        self._pipe = deque() if pipe is None else pipe
        if fn:
            self._pipe.appendleft(_fn_to_map_pipe(fn))

    def __sub__(self, other, *, upstream=False):
        if isinstance(other, source):
            raise TypeError
        if isinstance(other, sink):
            return other._extend_pipe_with_pipe(self)
        return self._extend_pipe_with_coroutine(_fn_to_map_pipe(other), upstream=upstream)

    def __rsub__(self, other):
        return self.__sub__(other, upstream=True)

    def __rshift__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return sink(1)

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self._extend_pipe_with_coroutine(_fn_to_filter_pipe(other))

    def __radd__(self, other):
        if isinstance(other, sink):
            raise TypeError
        return self

    def __truediv__(self, other):
        sink_function  = other._fn if isinstance(other, sink) else other
        sink_coroutine = _fn_to_sink_coroutine(sink_function)
        return self._extend_pipe_with_coroutine(_coroutine_to_branch_coroutine(sink_coroutine))

    def _extend_pipe_with_coroutine(self, coroutine, *, upstream=False):
        extended_pipe = self._pipe.copy()
        if upstream: extended_pipe.append    (coroutine)
        else       : extended_pipe.appendleft(coroutine)
        return pipe(pipe=extended_pipe)


class sink:

    def __init__(self, fn, *, pipe=None):
        self._pipe = deque() if pipe is None else pipe
        self._fn   = fn

    def __sub__(self, _):
        raise TypeError

    def __rsub__(self, other):
        return self._extend_pipe_with_coroutine(_fn_to_map_pipe(other))

    def __radd__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

    def __rrshift__(self, other):
        if isinstance(other, (pipe, sink)):
            raise TypeError
        return self

    def _extend_pipe_with_pipe(self, the_pipe):
        extended_pipe = the_pipe._pipe + self._pipe
        return sink(self._fn, pipe=extended_pipe)

    def _extend_pipe_with_coroutine(self, coroutine):
        extended_pipe = self._pipe.copy()
        extended_pipe.append(coroutine)
        return sink(self._fn, pipe=extended_pipe)


class ready:

    def __init__(self, source, sink):
        self._source = source._source
        all_pipe_coroutines = sink._pipe + source._pipe
        all_pipe_coroutines.appendleft(_fn_to_sink_coroutine(sink._fn))
        self._pipe   = reduce(_apply, all_pipe_coroutines)

    def __call__(self):
        for item in self._source:
            self._pipe.send(item)


def _apply(arg, fn):
    return fn(arg)


def _fn_to_map_pipe(op):
    def map_loop(target):
        with closing(target):
            while True:
                target.send(op((yield)))
    return coroutine(map_loop)


def _fn_to_filter_pipe(predicate):
    def filter_loop(target):
        with closing(target):
            while True:
                val = yield
                if predicate(val):
                    target.send(val)
    return coroutine(filter_loop)


def _fn_to_sink_coroutine(effect) -> 'coroutine':
    def sink_loop():
        while True:
            effect((yield))
    return coroutine(sink_loop)()


def _coroutine_to_branch_coroutine(sideways : 'coroutine') -> 'coroutine':
    @coroutine
    def branch_loop(downstream):
        with closing(sideways), closing(downstream):
            while True:
                val = yield
                sideways  .send(val)
                downstream.send(val)
    return branch_loop


@contextmanager
def closing(target):
    try:     yield
    finally: target.close()


def coroutine(generator_function):
    @wraps(generator_function)
    def proxy(*args, **kwds):
        coroutine = generator_function(*args, **kwds)
        next(coroutine)
        return coroutine
    return proxy
