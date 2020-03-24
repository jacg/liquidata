from operator  import itemgetter
from functools import reduce
from itertools import chain

from pytest import mark
xfail = mark.xfail


def test_trivial():
    from reboot import Flow, Sink
    data = list(range(10))
    result = []
    net = Flow(Sink(result.append))
    net(data)
    assert result == data


def test_map():
    from reboot import Flow, Map, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Flow(Map(f), Sink(result.append))
    net(data)
    assert result == list(map(f, data))


def test_implicit_map():
    from reboot import Flow, Sink
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = Flow(f, Sink(result.append))
    net(data)
    assert result == list(map(f, data))


def test_filter():
    from reboot import Flow, Filter, Sink
    data = list(range(10))
    result = []
    net = Flow(Filter(odd), Sink(result.append))
    net(data)
    assert result == list(filter(odd, data))


def test_implicit_filter():
    from reboot import Flow, Filter, Sink
    data = list(range(10))
    result = []
    net = Flow({odd}, Sink(result.append))
    net(data)
    assert result == list(filter(odd, data))


def test_implicit_sink():
    from reboot import Flow
    data = list(range(10))
    result = []
    net = Flow((result.append,))
    net(data)
    assert result == data


def test_branch():
    from reboot import Flow, Branch, Sink
    data = list(range(10))
    branch, main = [], []
    net = Flow(Branch(Sink(branch.append)), (main.append,))
    net(data)
    assert main   == data
    assert branch == data


def test_implicit_branch():
    from reboot import Flow
    data = list(range(10))
    branch, main = [], []
    net = Flow([(branch.append,)], (main.append,))
    net(data)
    assert main   == data
    assert branch == data


def test_integration_1():
    from reboot import Flow
    data = range(20)
    f, g, h = square, addN(1), addN(2)
    a, b, c = odd   , gtN(50), ltN(100)
    s, t    = [], []
    net = Flow(f,
               {a},
               [g, {b}, (s.append,)],
               h,
               {c},
               (t.append,))
    net(data)
    assert s == list(filter(b, map(g, filter(a, map(f, data)))))
    assert t == list(filter(c, map(h, filter(a, map(f, data)))))


def test_fold_and_return():
    from reboot import Flow, out, Fold
    data = range(10)
    net = Flow(out.total(Fold(sym_add)))
    assert net(data).total == reduce(sym_add, data)


def test_fold_with_initial_value():
    from reboot import Flow, out, Fold
    data = range(3)
    net = Flow(out.total(Fold(sym_add, 99)))
    assert net(data).total == reduce(sym_add, data, 99)


def test_return_value_from_branch():
    from reboot import Flow, out, Fold
    data = range(3)
    net = Flow([out.branch(Fold(sym_add))],
                out.main  (Fold(sym_mul)))
    result = net(data)
    assert result.main   == reduce(sym_mul, data)
    assert result.branch == reduce(sym_add, data)


def test_implicit_fold():
    from reboot import Flow, out
    data = range(3)
    net = Flow(out.total(sym_add))
    assert net(data).total == reduce(sym_add, data)


def test_implicit_fold_with_initial_value():
    from reboot import Flow, out
    data = range(3)
    net = Flow(out.total(sym_add, 99))
    assert net(data).total == reduce(sym_add, data, 99)


def test_implicit_collect_into_list():
    from reboot import Flow, out
    data = range(3)
    net = Flow(out.everything)
    assert net(data).everything == list(data)


def test_nested_branches():
    from reboot import Flow, out
    f,g,h,i = symbolic_functions('fghi')
    data = range(3)
    net = Flow([[f, out.BB], g, out.BM],
                [h, out.MB], i, out.MM )
    res = net(data)
    assert res.BB == list(map(f, data))
    assert res.BM == list(map(g, data))
    assert res.MB == list(map(h, data))
    assert res.MM == list(map(i, data))


def test_get_implicit_map():
    from reboot import Flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Flow(get.A, out.B)
    assert net(data, A=f).B == list(map(f, data))


def test_get_implicit_filter():
    from reboot import Flow, get, out
    data = list(range(6))
    f = odd
    net = Flow(get.A, out.B)
    assert net(data, A={f}).B == list(filter(f, data))


@xfail
def test_implicit_filter_get():
    from reboot import Flow, get, out
    data = list(range(6))
    f = odd
    net = Flow({get.A}, out.B)
    assert net(data, A=f).B == list(filter(f, data))


def test_get_in_branch():
    from reboot import Flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Flow([get.A, out.branch], out.main)
    r = net(data, A=f)
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_get_branch():
    from reboot import Flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = Flow(get.A, out.main)
    r = net(data, A=[f, out.branch])
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_flat_map():
    from reboot import Flow, FlatMap, out
    data = range(4)
    f = range
    net = Flow(FlatMap(f), out.X)
    assert net(data).X == list(chain(*map(f, data)))


@xfail(reason="Needs work. Other features more important now")
def test_get_implicit_sink():
    from reboot import Flow, get, out
    data = list(range(3))
    f = sym_add
    net = Flow(out.OUT(get.SINK))
    assert net(data, SINK=f).OUT == reduce(f, data)


def test_open_pipe_as_function():
    from reboot import OpenPipe
    f,g = symbolic_functions('fg')
    pipe_fn = OpenPipe(f,g).fn()
    assert pipe_fn(6) == (g(f(6)),)


def test_open_pipe_on_filter():
    from reboot import OpenPipe, FlatMap
    f = odd
    pipe_fn = OpenPipe({f}).fn()
    assert pipe_fn(3) == (3,)
    assert pipe_fn(4) == ()


def test_open_pipe_on_flatmap():
    from reboot import OpenPipe, FlatMap
    f = range
    pipe_fn = OpenPipe(FlatMap(f)).fn()
    assert pipe_fn(3) == (0,1,2)
    assert pipe_fn(5) == (0,1,2,3,4)


def test_open_pipe_with_get_as_function():
    from reboot import OpenPipe, get
    f,g,h = symbolic_functions('fgh')
    pipe = OpenPipe(f, get.FN)
    pipe_g = pipe.fn(FN=g)
    pipe_h = pipe.fn(FN=h)
    assert pipe_g(6) == (g(f(6)),)
    assert pipe_h(7) == (h(f(7)),)


def test_open_pipe_as_component():
    from reboot import OpenPipe, Flow, out
    data = range(3,6)
    a,b,f,g = symbolic_functions('abfg')
    pipe = OpenPipe(f, g).pipe()
    net = Flow(a, pipe, b, out.X)
    assert net(data).X == list(map(b, map(g, map(f, map(a, data)))))


def test_pick_item():
    from reboot import Flow, pick, out
    names = 'abc'
    values = range(3)
    f, = symbolic_functions('f')
    data = [dict((name, value) for name in names) for value in values]
    net = Flow(pick.a, f, out.X)
    assert net(data).X == list(map(f, values))


def test_pick_multiple_items():
    from reboot import Flow, pick, out
    names = 'abc'
    ops = tuple(symbolic_functions(names))
    values = range(3)
    data = [{name:op(N) for (name, op) in zip(names, ops)} for N in values]
    net = Flow(pick.a.b, out.X)
    assert net(data).X == list(map(itemgetter('a', 'b'), data))


def test_on_item():
    from reboot import Flow, on, out
    names = 'abc'
    f, = symbolic_functions('f')
    values = range(3)
    data = [{name:N for name in names} for N in values]
    expected = [d.copy() for d in data]
    for d in expected:
        d['a'] = f(d['a'])
    net = Flow(on.a(f), out.X)
    assert net(data).X == expected

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
