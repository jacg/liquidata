from operator  import add, mul
from functools import reduce

import network as nw

from pytest import raises


def test_cannot_run_empty_network():
    net = nw.network()
    with raises(nw.NetworkIncomplete) as e:
        net()
    assert e.value.unbound_variables == {"IN", "OUT"}


def test_cannot_run_network_without_sink():
    net = nw.network(nw.src([]))
    with raises(nw.NetworkIncomplete) as e: # TODO: message text match
        net()
    assert e.value.unbound_variables == {"OUT", }


def test_cannot_run_network_without_source():
    net = nw.network(nw.sink(lambda _:None))
    with raises(nw.NetworkIncomplete) as e: # TODO: message text match
        net()
    assert e.value.unbound_variables == {"IN", }


def test_trivial_network():
    the_data = list(range(10))
    net = nw.network(nw.src(the_data), nw.fold(add))
    assert net() == sum(the_data)


def test_set_sink_at_run_time():
    the_data = list(range(1, 10))
    net = nw.network(nw.src(the_data))
    assert net(OUT=nw.fold(add)) == reduce(add, the_data)
    assert net(OUT=nw.fold(mul)) == reduce(mul, the_data)


def test_set_source_at_run_time():
    data1 = range(10)
    data2 = range(2, 40, 3)
    net = nw.network(nw.fold(add))
    assert net(IN=data1) == reduce(add, data1)
    assert net(IN=data2) == reduce(add, data2)


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
