import network as nw

from pytest import raises


def test_cannot_run_empty_network():
    net = nw.network()
    with raises(nw.NetworkIncomplete) as e:
        net()
    assert e.value.unbound_variables == {"IN", "OUT"}


def test_cannot_run_network_without_sink():
    net = nw.network()
    net.add_source([])
    with raises(nw.NetworkIncomplete) as e:
        net()
    assert e.value.unbound_variables == {"OUT",}


def test_cannot_run_network_without_source():
    net = nw.network()
    net.add_sink(lambda _: None)
    with raises(nw.NetworkIncomplete) as e:
        net()
    assert e.value.unbound_variables == {"IN",}
