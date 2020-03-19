from collections import deque
from contextlib  import contextmanager
from functools   import reduce
from functools   import wraps

class source:

    def __init__(self, iterable=None, pipe=None):
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

    def __sub__(self, other):
        if isinstance(other, source):
            raise TypeError
        if isinstance(other, sink):
            return other
        return self._extend_pipe_with_coroutine(_fn_to_map_pipe(other))

    __rsub__ = __sub__

    def __rshift__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return sink(1)

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

    def __radd__(self, other):
        if isinstance(other, sink):
            raise TypeError
        return self

    def _extend_pipe_with_coroutine(self, coroutine):
        extended_pipe = self._pipe.copy()
        extended_pipe.appendleft(coroutine)
        return pipe(pipe=extended_pipe)


class sink:

    def __init__(self, fn):
        self._pipe = deque()
        self._sink = _fn_to_sink(fn)

    def __sub__(self, _):
        raise TypeError

    def __rsub__(self, other):
        return self

    def __radd__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

    def __rrshift__(self, other):
        if isinstance(other, (pipe, sink)):
            raise TypeError
        return self


class ready:

    def __init__(self, source=None, sink=None):
        self._source = source._source
        xxx = source._pipe
        yyy = sink._pipe
        zzz = yyy + xxx
        zzz.appendleft(sink._sink)
        self._pipe   = reduce(_apply, zzz)

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


def _fn_to_sink(effect):
    def sink_loop():
        while True:
            effect((yield))
    return coroutine(sink_loop)()


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
