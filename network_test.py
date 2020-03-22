from operator  import add, mul
from functools import reduce

import network as nw

from pytest import raises, mark

xfail=mark.xfail


def test_trivial_network():
    from network import network, out
    the_data = 'xyz'
    net = network(the_data, out.X(sym_add))
    assert net().X == reduce(sym_add, the_data)


def test_use_function_to_map():
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


def test_cannot_run_network_without_source():
    data = 'xyz'
    f, = symbolic_functions('f')
    net = nw.network(f, nw.out.X(sym_add))
    with raises(nw.NoSourceAtFrontOfPipe): # TODO: message text match
        net()

def test_NoSource_kind_of_NetIncomplete():
    assert issubclass(nw.NoSourceAtFrontOfPipe,
                       nw.NetworkIncomplete)


def test_NoSink_kind_of_NetIncomplete():
    assert issubclass(nw.NoSinkAtEndOfPipe,
                       nw.NetworkIncomplete)


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


def test_get_source():
    from network import network, out, get
    data1 = 'xyz'
    data2 = 'abcd'
    net = network(get.IN, out.X(sym_add))
    assert net(IN=data1).X == reduce(sym_add, data1)
    assert net(IN=data2).X == reduce(sym_add, data2)


def test_get_map():
    from network import network, out, get
    data = 'xyz'
    f,g = symbolic_functions('fg')
    net = network(data, get.fn, out.X(sym_add))
    assert net(fn=f).X == reduce(sym_add, map(f, data))
    assert net(fn=g).X == reduce(sym_add, map(g, data))


@xfail(reason='Needs more thought')
def test_get_sink():
    from network import network, out, get, fold
    the_data = 'xyz'
    net = network(the_data, out.X(get.SINK))
    assert net(SINK=fold(sym_add)).X == reduce(sym_add, the_data)
    assert net(SINK=fold(sym_mul)).X == reduce(sym_mul, the_data)


@xfail(reason='Needs more thought')
def test_get_source_argument():
    from network import network, get, out
    data1 = 'xyz'
    data2 = 'abcd'
    net = network(get.IN, out.X(sym_add))
    assert net(IN=data1).X == reduce(sym_add, data1)
    assert net(IN=data2).X == reduce(sym_add, data2)


def test_fold_without_initial():
    data = range

def test_fold_with_initial():
    pass

def test_side_effect_sink():
    pass

def test_side_effect_sink_with_return():
    pass




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
