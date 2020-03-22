

def test_trivial():
    from reboot import Network, Sink
    data = list(range(10))
    result = []
    net = Network(data, Sink(result.append))
    net()
    assert result == data


def test_map():
    from reboot import Network, Map, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Network(data, Map(f), Sink(result.append))
    net()
    assert result == list(map(f, data))


def test_implicit_map():
    from reboot import Network, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Network(data, f, Sink(result.append))
    net()
    assert result == list(map(f, data))


def test_filter():
    from reboot import Network, Filter, Sink
    data = list(range(10))
    result = []
    net = Network(data, Filter(odd), Sink(result.append))
    net()
    assert result == list(filter(odd, data))


def test_implicit_filter():
    from reboot import Network, Filter, Sink
    data = list(range(10))
    result = []
    net = Network(data, {odd}, Sink(result.append))
    net()
    assert result == list(filter(odd, data))


def test_implicit_sink():
    from reboot import Network
    data = list(range(10))
    result = []
    net = Network(data, (result.append,))
    net()
    assert result == data


def test_branch():
    from reboot import Network, Branch, Sink
    data = list(range(10))
    branch, main = [], []
    net = Network(data, Branch(Sink(branch.append)), (main.append,))
    net()
    assert main   == data
    assert branch == data


###################################################################
# Guinea pig functions for use in graphs constructed in the tests #
###################################################################

def symbolic_apply(f ): return lambda x   : f'{f}({x})'
def symbolic_binop(op): return lambda l, r: f'({l} {op} {r})'
def symbolic_functions(names): return map(symbolic_apply, names)
sym_add = symbolic_binop('+')
sym_mul = symbolic_binop('*')

def square(n): return n * n
def mulN(N): return lambda x: x * N
def addN(N): return lambda x: x + N
def  gtN(N): return lambda x: x > N
def  ltN(N): return lambda x: x < N

def odd (n): return n % 2 != 0
def even(n): return n % 2 == 0
