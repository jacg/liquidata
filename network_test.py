import network as nw

from pytest import raises


def test_cannot_run_empty_network():
    net = nw.network()
    with raises(nw.NetworkIncomplete) as e:
        net()
    assert e.value.unbound_variables == {"IN", "OUT"}
