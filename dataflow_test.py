import string

import dataflow as df

from pytest import raises
from pytest import mark
parametrize = mark.parametrize


from hypothesis            import given
from hypothesis.strategies import tuples
from hypothesis.strategies import integers
from hypothesis.strategies import none
from hypothesis.strategies import one_of


def test_simplest_pipeline():

    # The simplest possible pipeline has one source directly connected
    # to one sink.

    # We avoid using a lazy source so that we can compare the result
    # with the input
    the_source = list(range(20))

    # In this example the sink will simply collect the data it
    # receives, into a list.
    result = []
    the_sink = df.sink(result.append)

    # Use 'push' to feed the source into the pipe.
    df.push(source=the_source, pipe=the_sink)

    assert result == the_source


def test_fork():

    # Dataflows can be split with 'fork'

    the_source = list(range(10, 20))

    left  = [];  left_sink = df.sink( left.append)
    right = []; right_sink = df.sink(right.append)

    df.push(source = the_source,
            pipe   = df.fork( left_sink,
                             right_sink))

    assert left == right == the_source



def test_map():

    # The pipelines start to become interesting when the data are
    # transformed in some way. 'map' transforms every item passing
    # through the pipe by applying the supplied operation.

    def the_operation(n): return n*n
    square = df.map(the_operation)

    the_source = list(range(1,11))

    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = square(the_sink))

    assert result == list(map(the_operation, the_source))


def test_pipe():

    # The basic syntax requires any element of a pipeline to be passed
    # as argument to the one that precedes it. This looks strange to
    # the human reader, especially when using parametrized
    # components. 'pipe' allows construction of pipes from a sequence
    # of components.

    # Using 'pipe', 'test_map' could have been written like this:

    def the_operation(n): return n*n
    square = df.map(the_operation)

    the_source = list(range(1,11))

    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = df.pipe(square, the_sink))

    assert result == list(map(the_operation, the_source))


def test_longer_pipeline():

    # Pipelines can have arbitrary lengths

    the_source = list(range(1,11))

    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = df.pipe(df.map(lambda n:n+1),
                             df.map(lambda n:n*2),
                             df.map(lambda n:n-3),
                             df.map(lambda n:n/4),
                             the_sink))

    assert result == [ (((n+1)*2)-3)/4 for n in the_source ]


def test_fork_implicit_pipes():

    # Arguments can be pipes or tuples.
    # Tuples get implicitly converted into pipes

    the_source = list(range(10, 20))
    add_1      = df.map(lambda x: 1 + x)

    implicit_pipe_collector = []; implicit_pipe_sink = df.sink(implicit_pipe_collector.append)
    explicit_pipe_collector = []; explicit_pipe_sink = df.sink(explicit_pipe_collector.append)

    df.push(source = the_source,
            pipe   = df.fork(       (add_1, implicit_pipe_sink),
                             df.pipe(add_1, explicit_pipe_sink)))

    assert implicit_pipe_collector == explicit_pipe_collector == [1 + x for x in the_source]


def test_filter():

    # 'filter' can be used to eliminate data

    def the_predicate(n): return n % 2
    odd = df.filter(the_predicate)

    the_source = list(range(20, 30))

    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = df.pipe(odd, the_sink))

    assert result == list(filter(the_predicate, the_source))


def test_count():

    # 'count' is an example of a sink which only produces a result
    # once the stream of data flowing into the pipeline has been
    # closed. Such results are retrieved from futures which are
    # created at the time a 'count' instance is created: a namedtuple
    # containing the sink and its corresponding future is returned.

    count = df.count()

    the_source = list(range(30,40))

    df.push(source = the_source,
            pipe   = count.sink)

    assert count.future.result() == len(the_source)

# 'push' provides a higher-level interface to using such futures:
# it optionally accepts a future, a tuple of futures or a mapping
# of futures. It returns the result of the future, a tuple of
# their results or a namespace with the results, respectively.
def test_push_futures_single():
    the_source = list(range(100))
    count      = df.count()

    result = df.push(source = the_source,
                     pipe   = df.pipe(count.sink),
                     result = count.future)

    assert result == len(the_source)


def test_push_futures_tuple():
    the_source = list(range(100))
    count_all  = df.count()
    count_odd  = df.count()


    result = df.push(source = the_source,
                     pipe   = df.fork(                                 count_all.sink,
                                      df.pipe(df.filter(lambda n:n%2), count_odd.sink)),
                     result = (count_odd.future, count_all.future))

    all_count = len(the_source)
    odd_count = all_count // 2
    assert result == (odd_count, all_count)


def test_push_futures_mapping():
    count_all = df.count()
    count_odd = df.count()

    the_source = list(range(100))

    result = df.push(source = the_source,
                     pipe   = df.fork(                                 count_all.sink,
                                      df.pipe(df.filter(lambda n:n%2), count_odd.sink)),
                     result = dict(odd = count_odd.future,
                                   all = count_all.future))

    all_count = len(the_source)
    assert result.odd == all_count // 2
    assert result.all == all_count


def test_reduce():

    # 'reduce' provides a high-level way of creating future-sinks such
    # as 'count'

    # Make a component just like df.sum
    from operator import add
    total = df.reduce(add, initial=0)

    # Create two instances of it, which will be applied to different
    # (forked) sub-streams in the network
    total_all = total()
    total_odd = total()

    N = 15
    the_source = list(range(N))

    result = df.push(source = the_source,
                     pipe   = df.fork(                                 total_all.sink,
                                      df.pipe(df.filter(lambda n:n%2), total_odd.sink)),
                     result = (total_all.future, total_odd.future))

    sum_all, sum_odd = sum(the_source), (N // 2) ** 2
    assert result == (sum_all, sum_odd)


@mark.xfail
def test_sum():
    raise NotImplementedError


def test_stop_when():

    # 'stop_when' can be used to stop all branches of the network
    # immediately.

    countfuture, count = df.count()

    limit, step = 10, 2

    import itertools

    result = df.push(source = itertools.count(start=0, step=step),
                     pipe   = df.fork(df.stop_when(lambda n:n==limit),
                                      count),
                     result = (countfuture,))

    assert result == (limit // step,)


def test_stateful_stop_when():

    @df.coroutine_send
    def n_items_seen(n):
        yield # Will stop here on construction
        for _ in range(n):
            yield False
        yield True

    countfuture, count = df.count()

    import itertools
    limit, step = 10, 2

    result = df.push(source = itertools.count(start=0, step=step),
                     pipe   = df.fork(df.stop_when(n_items_seen(limit)),
                                      count),
                     result = (countfuture,))

    assert result == (limit,)


def test_spy():

    # 'spy' performs an operation on the data streaming through the
    # pipeline, without changing what is seen downstream. An obvious
    # use of this would be to insert a 'spy(print)' at some point in
    # the pipeline to observe the data flow through that point.

    the_source = list(range(50, 60))

    result = []; the_sink = df.sink(result.append)
    spied  = []; the_spy  = df.spy ( spied.append)

    df.push(source = the_source,
            pipe   = df.pipe(the_spy, the_sink))

    assert spied == result == the_source


def test_spy_count():

    # count is a component that can be needed in the middle
    # of a pipeline. However, because it is a sink it needs
    # to be plugged into a spy. Thus, the component spy_count
    # provides a comfortable interface to access the future
    # and spy objects in a single line.

    the_source = list(range(20))

    count     = df.count()
    spy_count = df.spy_count()

    result = df.push(source = the_source,
                     pipe   = df.pipe(spy_count.spy ,
                                          count.sink),
                     result = dict(from_count     =     count.future,
                                   from_spy_count = spy_count.future))

    assert result.from_count == result.from_spy_count == len(the_source)


def test_branch():

    # 'branch', like 'spy', allows you to insert operations on a copy
    # of the stream at any point in a network. In contrast to 'spy'
    # (which accepts a single plain operation), 'branch' accepts an
    # arbitrary number of pipeline components, which it combines into
    # a pipeline. It provides a more convenient way of constructing
    # some graphs that would otherwise be constructed with 'fork'.

    # Some pipeline components
    c1 = []; C1 = df.sink(c1.append)
    c2 = []; C2 = df.sink(c2.append)
    e1 = []; E1 = df.sink(e1.append)
    e2 = []; E2 = df.sink(e2.append)

    A = df.map(lambda n:n+1)
    B = df.map(lambda n:n*2)
    D = df.map(lambda n:n*3)

    # Two eqivalent networks, one constructed with 'fork' the other
    # with 'branch'.
    graph1 = df.pipe(A, df.fork(df.pipe(B,C1),
                                df.pipe(D,E1)))

    graph2 = df.pipe(A, df.branch(B,C2), D,E2)

    # Feed the same data into the two networks.
    the_source = list(range(10, 50, 4))
    df.push(source=the_source, pipe=graph1)
    df.push(source=the_source, pipe=graph2)

    # Confirm that both networks produce the same results.
    assert c1 == c2
    assert e1 == e2


def test_branch_closes_sideways():
    the_source = range(10)
    branch_result = []; the_branch_sink = df.sink(branch_result.append)
    main_result   = []; the_main_sink   = df.sink(  main_result.append)

    df.push(source = the_source,
            pipe   = df.pipe(df.branch(the_branch_sink),
                             the_main_sink))

    with raises(StopIteration):
        the_branch_sink.send(99)


def test_chain_pipes():

    # Pipelines must end in sinks. If the last component of a pipe is
    # not a sink, the pipe may be used as a component in a bigger
    # pipeline, but it will be impossible to feed any data into it
    # until it is connected to some other component which ends in a
    # sink.

    # Some basic pipeline components
    s1 = []; sink1 = df.sink(s1.append)
    s2 = []; sink2 = df.sink(s2.append)

    A = df.map(lambda n:n+1)
    B = df.map(lambda n:n*2)
    C = df.map(lambda n:n-3)

    # Two different ways of creating equivalent networks: one of them
    # groups the basic components into sub-pipes
    graph1 = df.pipe(        A, B,          C, sink1)
    graph2 = df.pipe(df.pipe(A, B), df.pipe(C, sink2))

    # Feed the same data into the two networks
    the_source = list(range(40))

    df.push(source=the_source, pipe=graph1)
    df.push(source=the_source, pipe=graph2)

    # Confirm that both networks produce the same results.
    assert s1 == s2


def test_reuse_unterminated_pipes():

    # Open-ended pipes must be connected to a sink before they can
    # receive any input. Open-ended pipes are reusable components: any
    # such pipe can be used in different points in the same or
    # different networks. They are completely independent.

    def add(n):
        return df.map(lambda x:x+n)

    A,B,C,D,E,X,Y,Z = 1,2,3,4,5,6,7,8

    component = df.pipe(add(X),
                        add(Y),
                        add(Z))

    s1 = []; sink1 = df.sink(s1.append)
    s2 = []; sink2 = df.sink(s2.append)

    # copmonent is being reused twice in this network
    graph = df.pipe(add(A),
                    df.branch(add(B), component, add(C), sink1),
                    add(D), component, add(E), sink2)

    the_source = list(range(10,20))
    df.push(source=the_source, pipe=graph)

    assert s1 == [ n + A + B + X + Y + Z + C for n in the_source ]
    assert s2 == [ n + A + D + X + Y + Z + E for n in the_source ]


def test_reuse_terminated_pipes():

    # Sink-terminated pipes are also reusable, but do note that if
    # such components are reused in the same graph, the sink at the
    # end of the component will receive inputs from more than one
    # branch: they share the sink; the branches are joined.

    def add(n):
        return df.map(lambda x:x+n)

    A,B,C,X,Y,Z = 1,2,3,4,5,6

    collected_by_sinks = []; sink1 = df.sink(collected_by_sinks.append)

    component = df.pipe(add(X),
                        add(Y),
                        add(Z),
                        sink1)

    graph = df.pipe(add(A),
                    df.branch(add(B), component),
                              add(C), component)

    the_source = list(range(10,20))
    df.push(source=the_source, pipe=graph)

    route1 = [ n + A + B + X + Y + Z for n in the_source ]
    route2 = [ n + A + C + X + Y + Z for n in the_source ]

    def intercalate(a,b):
        return [ x for pair in zip(a,b) for x in pair ]

    assert collected_by_sinks == intercalate(route1, route2)


small_ints         = integers(min_value=0, max_value=15)
small_ints_nonzero = integers(min_value=1, max_value=15)
slice_arg          = one_of(none(), small_ints)
slice_arg_nonzero  = one_of(none(), small_ints_nonzero)

@given(one_of(tuples(small_ints),
              tuples(small_ints, small_ints),
              tuples(slice_arg,  slice_arg, slice_arg_nonzero)))
def test_slice_downstream(spec):

    the_source = list('abcdefghij')
    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = df.pipe(df.slice(*spec), the_sink))

    specslice = slice(*spec)
    assert result == the_source[specslice]
    assert result == the_source[specslice.start : specslice.stop : specslice.step]


# slice takes an optional argument close_all. If this argument
# is False (default), slice will close the innermost branch in
# which the component is plugged in after the component iterates
# over all its entries. However, when set to True, the behaviour
# is to close the outermost pipeline, resulting in a full stop of
# the data flow.
@parametrize("close_all", (False, True))
def test_slice_close_all(close_all):
    the_source = list(range(20))
    n_elements = 5
    slice      = df.slice(n_elements, close_all=close_all)

    result_branch = []; sink_branch = df.sink(result_branch.append)
    result_main   = []; sink_main   = df.sink(result_main  .append)

    df.push(source = the_source,
            pipe   = df.pipe(df.branch(slice, sink_branch),
                             sink_main))

    if close_all:
        assert result_branch == the_source[:n_elements]
        assert result_main   == the_source[:n_elements]
    else:
        assert result_branch == the_source[:n_elements]
        assert result_main   == the_source


@parametrize('args',
             ((      -1,),
              (None, -1),
              (-1, None),
              (None, None, -1),
              (None, None,  0),
             ))
def test_slice_raises_ValueError(args):
    with raises(ValueError):
        df.slice(*args)


def test_pipes_must_end_in_a_sink():
    the_source    = range(10)
    sinkless_pipe = df.map(abs)

    with raises(df.IncompletePipe):
        df.push(source = the_source,
                pipe   = sinkless_pipe)


def test_count_filter():

    # count_filter provides a future/filter pair.
    # This is a simple interface to keep track of
    # how many entries satisfy the predicate and
    # how many are filtered out.

    the_source  = list(range(21))
    predicate   = lambda n: n % 2

    odd      = df.count_filter(predicate)
    filtered = []; the_sink = df.sink(filtered.append)

    result = df.push(source = the_source,
                     pipe   = df.pipe(odd.filter, the_sink),
                     result = odd.future)

    expected_result = list(filter(predicate, the_source))

    assert filtered        ==                       expected_result
    assert result.n_passed ==                   len(expected_result)
    assert result.n_failed == len(the_source) - len(expected_result)


# In dataflow, the source can also generate more complex
# data structures. Hence, the same entry can gather
# different types of data in a single object.
# A useful manner of organizing the data is using some
# kind of namespace that labels each node of information.
# In order to work more comfortably in this scenario,
# most of the basic components in dataflow take optional
# arguments that allow the user to specify which node of
# information the component should use. The output of
# the component can be put back under the same or a
# different label.
def test_sink_with_namespace():
    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    result = []; the_sink = df.sink(result.append, args="x")

    df.push(source = the_source,
            pipe   = the_sink  )

    assert result == list(letters)


def test_map_with_namespace_args_out():
    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    make_upper_case = df.map(str.upper, args="x", out="upper_x")

    result = []; the_sink = df.sink(result.append, args="upper_x")

    df.push(source = the_source,
            pipe   = df.pipe(make_upper_case, the_sink))

    assert result == list(letters.upper())


def test_map_with_namespace_item():

    # item replaces the input with the output

    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    make_upper_case = df.map(str.upper, item="x")

    result = []; the_sink = df.sink(result.append, args="x")

    df.push(source = the_source,
            pipe   = df.pipe(make_upper_case, the_sink))

    assert result == list(letters.upper())


def test_filter_with_namespace():
    vowels     = "aeiou"
    the_source = (dict(i=i, x=x) for i, x in enumerate(string.ascii_lowercase))
    vowel      = df.filter(lambda s: s in vowels, args="x")

    result = []; the_sink = df.sink(result.append, args="x")

    df.push(source = the_source,
            pipe   = df.pipe(vowel, the_sink))

    assert result == list(vowels)


# When the first element of a pipe is a string, it
# is interpreted as a component that takes an item
# from the common namespace and pushes it through
# the pipe. This also works with forks and branches.

def test_implicit_element_picking_in_pipe():
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    result = []; the_sink = df.sink(result.append)
    df.push(source = the_source,
            pipe   = df.pipe("x", the_sink))

    assert result == the_source_elements


def test_implicit_element_picking_in_fork():
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    left  = [];  left_sink = df.sink( left.append)
    right = []; right_sink = df.sink(right.append)

    df.push(source = the_source,
            pipe   = df.fork(("x",  left_sink),
                             ("y", right_sink)))

    assert left == [-i for i in right] == the_source_elements


def test_implicit_element_picking_in_branch():
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    left  = [];  left_sink = df.sink( left.append)
    right = []; right_sink = df.sink(right.append)

    df.push(source = the_source,
            pipe   = df.pipe(df.branch("x",  left_sink),
                             right_sink))

    assert left == [-i["y"] for i in right] == the_source_elements


def test_implicit_pipe():
    # The push argument pipe can be given implicitly
    # (ie as a tuple of operations)
    def the_operation(n): return n*n
    square = df.map(the_operation)

    the_source = list(range(1,11))

    result = []
    the_sink = df.sink(result.append)

    df.push(source = the_source,
            pipe   = (square, the_sink))

    assert result == list(map(the_operation, the_source))
