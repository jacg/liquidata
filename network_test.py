from operator  import add, mul
from functools import reduce

import network as nw

from pytest import raises


def test_cannot_run_empty_network():
    net = nw.network()
    with raises(nw.NetworkIncomplete) as e:
        net()


def test_cannot_run_network_without_sink():
    net = nw.network(nw.src([]))
    with raises(nw.NetworkIncomplete): # TODO: message text match
        net()


def test_cannot_run_network_without_source():
    net = nw.network(nw.sink(lambda _:None))
    with raises(nw.NetworkIncomplete): # TODO: message text match
        net()


def test_trivial_network():
    the_data = 'xyz'
    net = nw.network(nw.src(the_data), nw.out.X(nw.fold(sym_add)))
    assert net().X == reduce(sym_add, the_data)


def test_set_sink_at_run_time():
    the_data = 'xyz'
    net = nw.network(nw.src(the_data), nw.out.X(nw.get.OUT))
    assert net(OUT=nw.fold(sym_add)).X == reduce(sym_add, the_data)
    assert net(OUT=nw.fold(sym_mul)).X == reduce(sym_mul, the_data)


def test_set_source_at_run_time_source_in_get():
    data1 = 'xyz'
    data2 = 'abcd'
    net = nw.network(nw.get.IN, nw.out.X(nw.fold(sym_add)))
    assert net(IN=nw.src(data1)).X == reduce(sym_add, data1)
    assert net(IN=nw.src(data2)).X == reduce(sym_add, data2)

def test_set_source_at_run_time_get_in_source():
    data1 = 'xyz'
    data2 = 'abcd'
    net = nw.network(nw.src(nw.get.IN), nw.fold(sym_add))
    assert net(IN=data1) == reduce(sym_add, data1)
    assert net(IN=data2) == reduce(sym_add, data2)


def test_implicit_map():
    data = 'xyz'
    f, = symbolic_functions('f')
    net = nw.network(nw.src(data), f, nw.out.X(nw.fold(sym_add)))
    assert net().X == reduce(sym_add, map(f, data))


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
