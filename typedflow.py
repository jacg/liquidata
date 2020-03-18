
class source:

    def __rshift__(self, other):
        if isinstance(other, (source)):
            raise TypeError
        if isinstance(other, sink):
            return ready()
        return self

class pipe:

    def __sub__(self, other):
        if isinstance(other, (source, sink)):
            raise TypeError
        return self

    __rsub__ = __sub__

    def __rshift__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

    __rrshift__ = __rshift__

    def __add__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

class sink:

    def __rrshift__(self, other):
        if isinstance(other, (source, pipe, sink)):
            raise TypeError
        return self

class ready:
    pass
