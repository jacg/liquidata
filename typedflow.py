
class source:

    # TODO: reimplement all of these operators with multimethods
    def __sub__(self, other):
        if isinstance(other, pipe):
            return self
        if isinstance(other, sink):
            return ready()
        if isinstance(other, source):
            raise TypeError
        return self

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

    def __rshift__(self, other):
        if isinstance(other, (source, pipe)):
            raise TypeError
        return ready()

class pipe:

    def __sub__(self, other):
        if isinstance(other, source):
            raise TypeError
        if isinstance(other, sink):
            return other
        return self

    __rsub__ = __sub__

    def __rshift__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return sink()

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

class sink:

    def __sub__(self, _):
        raise TypeError

    def __rsub__(self, other):
        return self

    def __rrshift__(self, other):
        if isinstance(other, (pipe, sink)):
            raise TypeError
        return sink()

class ready:
    pass
