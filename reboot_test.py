

def test_trivial():
    from reboot import Network, Sink
    data = list(range(10))
    result = []
    net = Network(data, Sink(result.append))
    net()
    assert result == data
