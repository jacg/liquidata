from functools import reduce
from itertools import chain

from pytest import mark
xfail = mark.xfail


def test_trivial():
    from reboot import Network, Sink
    data = list(range(10))
    result = []
    net = Network(Sink(result.append))
    net(data)
    assert result == data


def test_map():
    from reboot import Network, Map, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Network(Map(f), Sink(result.append))
    net(data)
    assert result == list(map(f, data))


def test_implicit_map():
    from reboot import Network, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Network(f, Sink(result.append))
    net(data)
    assert result == list(map(f, data))


def test_filter():
    from reboot import Network, Filter, Sink
    data = list(range(10))
    result = []
    net = Network(Filter(odd), Sink(result.append))
    net(data)
    assert result == list(filter(odd, data))


def test_implicit_filter():
    from reboot import Network, Filter, Sink
    data = list(range(10))
    result = []
    net = Network({odd}, Sink(result.append))
    net(data)
    assert result == list(filter(odd, data))


def test_implicit_sink():
    from reboot import Network
    data = list(range(10))
    result = []
    net = Network((result.append,))
    net(data)
    assert result == data


def test_branch():
    from reboot import Network, Branch, Sink
    data = list(range(10))
    branch, main = [], []
    net = Network(Branch(Sink(branch.append)), (main.append,))
    net(data)
    assert main   == data
    assert branch == data


def test_implicit_branch():
    from reboot import Network
    data = list(range(10))
    branch, main = [], []
    net = Network([(branch.append,)], (main.append,))
    net(data)
    assert main   == data
    assert branch == data

def test_integration_1():
    from reboot import Network
    data = range(20)
    f, g, h = square, addN(1), addN(2)
    a, b, c = odd   , gtN(50), ltN(100)
    s, t    = [], []
    net = Network(f,
                  {a},
                  [g, {b}, (s.append,)],
                  h,
                  {c},
                  (t.append,))
    net(data)
    assert s == list(filter(b, map(g, filter(a, map(f, data)))))
    assert t == list(filter(c, map(h, filter(a, map(f, data)))))


def test_fold_and_return():
    from reboot import Network, out, Fold
    data = range(10)
    net = Network(out.total(Fold(sym_add)))
    assert net(data).total == reduce(sym_add, data)


def test_fold_with_initial_value():
    from reboot import Network, out, Fold
    data = range(3)
    net = Network(out.total(Fold(sym_add, 99)))
    assert net(data).total == reduce(sym_add, data, 99)


def test_return_value_from_branch():
    from reboot import Network, out, Fold
    data = range(3)
    net = Network([out.branch(Fold(sym_add))],
                   out.main  (Fold(sym_mul)))
    result = net(data)
    assert result.main   == reduce(sym_mul, data)
    assert result.branch == reduce(sym_add, data)


def test_implicit_fold():
    from reboot import Network, out
    data = range(3)
    net = Network(out.total(sym_add))
    assert net(data).total == reduce(sym_add, data)


def test_implicit_fold_with_initial_value():
    from reboot import Network, out
    data = range(3)
    net = Network(out.total(sym_add, 99))
    assert net(data).total == reduce(sym_add, data, 99)


def test_implicit_collect_into_list():
    from reboot import Network, out
    data = range(3)
    net = Network(out.everything)
    assert net(data).everything == list(data)


def test_nested_branches():
    from reboot import Network, out
    f,g,h,i = symbolic_functions('fghi')
    data = range(3)
    net = Network([[f, out.BB], g, out.BM],
                   [h, out.MB], i, out.MM )
    res = net(data)
    assert res.BB == list(map(f, data))
    assert res.BM == list(map(g, data))
    assert res.MB == list(map(h, data))
    assert res.MM == list(map(i, data))


def test_get_implicit_map():
    from reboot import Network, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Network(get.A, out.B)
    assert net(data, A=f).B == list(map(f, data))


def test_get_implicit_filter():
    from reboot import Network, get, out
    data = list(range(6))
    f = odd
    net = Network(get.A, out.B)
    assert net(data, A={f}).B == list(filter(f, data))


def test_get_in_branch():
    from reboot import Network, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Network([get.A, out.branch], out.main)
    r = net(data, A=f)
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_get_branch():
    from reboot import Network, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Network(get.A, out.main)
    r = net(data, A=[f, out.branch])
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_flat_map():
    from reboot import Network, FlatMap, out
    data = range(4)
    f = range
    net = Network(FlatMap(f), out.X)
    assert net(data).X == list(chain(*map(f, data)))


@xfail(reason="Needs work. Other features more important now")
def test_get_implicit_sink():
    from reboot import Network, get, out
    data = list(range(3))
    f = sym_add
    net = Network(out.OUT(get.SINK))
    assert net(data, SINK=f).OUT == reduce(f, data)


def test_open_pipe_as_function():
    from reboot import OpenPipe
    f,g = symbolic_functions('fg')
    pipe_fn = OpenPipe(f,g).fn()
    assert pipe_fn(6) == (g(f(6)),)


def test_open_pipe_with_get_as_function():
    from reboot import OpenPipe, get
    f,g,h = symbolic_functions('fgh')
    pipe = OpenPipe(f, get.FN)
    pipe_g = pipe.fn(FN=g)
    pipe_h = pipe.fn(FN=h)
    assert pipe_g(6) == (g(f(6)),)
    assert pipe_h(7) == (h(f(7)),)



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
