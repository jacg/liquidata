from operator  import add, mul
from functools import reduce

import network as nw

from pytest import raises, mark

xfail=mark.xfail


def test_trivial_network():
    from network import network, out, fold
    the_data = 'xyz'
    net = network(the_data, out.X(fold(sym_add)))
    assert net().X == reduce(sym_add, the_data)


def test_implicit_fold():
    from network import network, out
    the_data = 'xyz'
    net = network(the_data, out.X(sym_add))
    assert net().X == reduce(sym_add, the_data)


def test_fold_with_initial_value():
    from network import network, out
    the_data = 'xyz'
    initial = "initial"
    net = network(the_data, out.X(sym_add, initial))
    assert net().X == reduce(sym_add, the_data, initial)


def test_set_out_name_externally():
    from network import network, out
    the_data = 'xyz'
    sum_into_X = out.X(sym_add)
    net = network(the_data, sum_into_X)
    assert net().X == reduce(sym_add, the_data)


def test_get_sink_get_in_out():
    from network import network, out, get, fold
    the_data = 'xyz'
    net = network(the_data, out.X(get.OUT))
    assert net(OUT=fold(sym_add)).X == reduce(sym_add, the_data)
    assert net(OUT=fold(sym_mul)).X == reduce(sym_mul, the_data)


def test_get_sink_out_in_get():
    from network import network, out, get, fold
    the_data = 'xyz'
    net = network(the_data, out.X(get.OUT))
    assert net(OUT=fold(sym_add)).X == reduce(sym_add, the_data)
    assert net(OUT=fold(sym_mul)).X == reduce(sym_mul, the_data)


def test_get_source():
    from network import network, out, get
    data1 = 'xyz'
    data2 = 'abcd'
    net = network(get.IN, out.X(sym_add))
    assert net(IN=data1).X == reduce(sym_add, data1)
    assert net(IN=data2).X == reduce(sym_add, data2)


@xfail(reason='Needs more thought')
def test_get_source_argument():
    from network import network, get, out
    data1 = 'xyz'
    data2 = 'abcd'
    net = network(get.IN, out.X(sym_add))
    assert net(IN=data1).X == reduce(sym_add, data1)
    assert net(IN=data2).X == reduce(sym_add, data2)


def test_implicit_map():
    from network import network, out
    data = 'xyz'
    f, = symbolic_functions('f')
    net = network(data, f, out.X(sym_add))
    assert net().X == reduce(sym_add, map(f, data))


def test_cannot_run_empty_network():
    net = nw.network()
    with raises(nw.NetworkIncomplete) as e:
        net()


def test_cannot_run_network_without_sink():
    data = 'xyz'
    f, = symbolic_functions('f')
    net = nw.network(data, f)
    with raises(nw.NoSinkAtEndOfPipe): # TODO: message text match
        net()
    with raises(nw.NetworkIncomplete):
        net()


def test_cannot_run_network_without_source():
    data = 'xyz'
    f, = symbolic_functions('f')
    net = nw.network(f, nw.out.X(sym_add))
    with raises(nw.NoSourceAtFrontOfPipe): # TODO: message text match
        net()
    with raises(nw.NetworkIncomplete):
        net()
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
