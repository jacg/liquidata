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
