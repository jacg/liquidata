import string

from pytest import raises
from pytest import mark
parametrize = mark.parametrize


from hypothesis            import given
from hypothesis.strategies import tuples
from hypothesis.strategies import integers
from hypothesis.strategies import none
from hypothesis.strategies import one_of


def test_simplest_pipeline():
# ANCHOR: simplest
    from dataflow import sink, push

    # Some dummy data
    the_source = list(range(20))

    # In this example the sink will simply collect the data it
    # receives, into a list.
    result = []

    # sink makes a sink out of a plain Python function.
    the_sink = sink(result.append)

    # Use df.push to feed the source into the pipe.
    push(source=the_source, pipe=the_sink)

    assert result == the_source
# ANCHOR_END: simplest


def test_map_and_pipe():
    # The pipelines start to become interesting when the data are
    # transformed in some way. 'map' transforms every item passing
    # through the pipe by applying the supplied operation.
# ANCHOR: map
    from dataflow import map as dmap, sink, push, pipe

    # Some data transformation, expressed as a plain Python function, which we
    # would like to use in a pipe
    def the_operation(n):
        return n*n

    # df.map turns the function into a pipe component
    square = dmap(the_operation)

    # Some dummy data ...
    the_data = list(range(1,11))

    # ... and a sink for collecting the transformed data
    result = []
    the_sink = sink(result.append)

    # Use df.pipe to connect the square component to the sink, and feed the
    # data into the pipe with df.push
    push(source = the_data,
         pipe   = pipe(square, the_sink))

    assert result == list(map(the_operation, the_data))
# ANCHOR_END: map


def test_longer_pipeline():
    from dataflow import sink, push, pipe, map as dmap

    # Pipelines can have arbitrary lengths

    the_source = list(range(1,11))

    result = []
    the_sink = sink(result.append)

    push(source = the_source,
         pipe   = pipe(dmap(lambda n:n+1),
                       dmap(lambda n:n*2),
                       dmap(lambda n:n-3),
                       dmap(lambda n:n/4),
                       the_sink))

    assert result == [ (((n+1)*2)-3)/4 for n in the_source ]


def test_fork_implicit_pipes():
    from dataflow import map as dmap, sink, push, fork, pipe

    # Arguments can be pipes or tuples.
    # Tuples get implicitly converted into pipes

    the_source = list(range(10, 20))
    add_1      = dmap(lambda x: 1 + x)

    implicit_pipe_collector = []; implicit_pipe_sink = sink(implicit_pipe_collector.append)
    explicit_pipe_collector = []; explicit_pipe_sink = sink(explicit_pipe_collector.append)

    push(source = the_source,
         pipe   = fork(     (add_1, implicit_pipe_sink),
                        pipe(add_1, explicit_pipe_sink)))

    assert implicit_pipe_collector == explicit_pipe_collector == [1 + x for x in the_source]


def test_filter():
# ANCHOR: filter
    from dataflow import filter as dfilter, sink, push, pipe

    # A predicate expressed as a plain function
    def the_predicate(n):
        return n % 2

    # Turn the predicate into a pipeline component with df.filter
    odd = dfilter(the_predicate)

    # Some dummy data ...
    the_data = list(range(20, 30))

    # ... and a sink for collecting the filtered data
    result = []
    the_sink = sink(result.append)

    # df.filter's result can be used in pipes
    push(source = the_data,
         pipe   = pipe(odd, the_sink))

    # df.filter is the dataflow equivalent of Python's builtin filter
    assert result == list(filter(the_predicate, the_data))
# ANCHOR_END: filter


def test_count():

    from dataflow import count, push

    # 'count' is an example of a sink which only produces a result
    # once the stream of data flowing into the pipeline has been
    # closed. Such results are retrieved from futures which are
    # created at the time a 'count' instance is created: a namedtuple
    # containing the sink and its corresponding future is returned.

    count = count()

    the_source = list(range(30,40))

    push(source = the_source,
         pipe   = count.sink)

    assert count.future.result() == len(the_source)

# 'push' provides a higher-level interface to using such futures:
# it optionally accepts a future, a tuple of futures or a mapping
# of futures. It returns the result of the future, a tuple of
# their results or a namespace with the results, respectively.
def test_push_result_single():
# ANCHOR: push-result-single
    from dataflow import count, push

    # Some dummy data
    the_source = list(range(100))

    # df.count is a sink factory. It creates a sink which counts how many
    # values it is fed. Once the stream has been closed, it places the final
    # result in its corresponding future.
    count = count()

    # df.count returns a namedtuple ...
    assert isinstance(count, tuple)

    # ... which contains a future as its first element ...
    assert count.future is count[0]

    # ... and a sink as the second element.
    assert count.sink is count[1]

    result = push(source = the_source,
                  # The sink can be used to cap a pipe
                  pipe   = count.sink,
                  # The future can be used to specify the return value of df.push
                  result = count.future)

    # When push finishes streaming data into its pipe, it will extract the
    # value it is supposed to return from the future it was given.
    assert result == len(the_source)
# ANCHOR_END: push-result-single


def test_push_futures_tuple():
    from dataflow import count, push, fork, pipe, filter as dfilter

    the_source = list(range(100))
    count_all  = count()
    count_odd  = count()


    result = push(source = the_source,
                  pipe   = fork(                            count_all.sink,
                                pipe(dfilter(lambda n:n%2), count_odd.sink)),
                  result = (count_odd.future, count_all.future))

    all_count = len(the_source)
    odd_count = all_count // 2
    assert result == (odd_count, all_count)


def test_push_futures_mapping():
    from dataflow import count, push, fork, pipe, filter as dfilter

    count_all = count()
    count_odd = count()

    the_source = list(range(100))

    result = push(source = the_source,
                  pipe   = fork(                            count_all.sink,
                                pipe(dfilter(lambda n:n%2), count_odd.sink)),
                  result = dict(odd = count_odd.future,
                                all = count_all.future))

    all_count = len(the_source)
    assert result.odd == all_count // 2
    assert result.all == all_count


def test_reduce():
# ANCHOR: reduce
    from dataflow import reduce as dreduce, push

    # Some dummy data, for testing
    the_data = list(range(15))

    # A binary function which returns the sum of its arguments
    from operator import add
    # Alternatively, we could have defined this ourselves as
    # def add(a, b):
    #     return a + b

    # df.reduce can be used to turn a binary function into a sink factory
    df_sum = dreduce(add, initial=0)

    # The factory returns a namedtuple containing a future and sink
    ssum = df_sum()

    result = push(source = the_data,
                  # The sink can be used to cap a pipe
                  pipe   = ssum.sink,
                  # The future can be used to specify the return value of push
                  result = ssum.future)
    # The component we created is the dataflow equivalent of Python's builtin
    # sum
    assert result == sum(the_data)
# ANCHOR_END: reduce


@mark.xfail
def test_sum():
    raise NotImplementedError


def test_stop_when():
    from dataflow import count, push, fork, stop_when

    # 'stop_when' can be used to stop all branches of the network
    # immediately.

    countfuture, count = count()

    limit, step = 10, 2

    import itertools

    result = push(source = itertools.count(start=0, step=step),
                  pipe   = fork(stop_when(lambda n:n==limit),
                                count),
                     result = countfuture)

    assert result == limit // step


def test_stateful_stop_when():
    from dataflow import coroutine_send, count, push, fork, stop_when

    @coroutine_send
    def n_items_seen(n):
        yield # Will stop here on construction
        for _ in range(n):
            yield False
        yield True

    countfuture, count = count()

    import itertools
    limit, step = 10, 2

    result = push(source = itertools.count(start=0, step=step),
                  pipe   = fork(stop_when(n_items_seen(limit)),
                                count),
                  result = countfuture)

    assert result == limit


def test_spy():
# ANCHOR: spy
    from dataflow import sink, spy, push, pipe

    # Some data for testing
    the_data = list(range(50, 60))

    # A sink to collect everything that reaches the end of the pipe
    reached_the_end = []; the_sink = sink(reached_the_end.append)
    # A spy to observe (and collect) everything mid-pipe
    spied           = []; the_spy  = spy (          spied.append)

    push(source = the_data,
         # Insert the spy into the pipe before the sink
         pipe   = pipe(the_spy, the_sink))

    # The spy saw all the data flowing through the pipe ...
    assert           spied == the_data
    # ... but didn't affect what was seen downstream
    assert reached_the_end == the_data
# ANCHOR_END: spy


def test_spy_count():
    from dataflow import count, spy_count, push, pipe

    # count is a component that can be needed in the middle
    # of a pipeline. However, because it is a sink it needs
    # to be plugged into a spy. Thus, the component spy_count
    # provides a comfortable interface to access the future
    # and spy objects in a single line.

    the_source = list(range(20))

    count     = count()
    spy_count = spy_count()

    result = push(source = the_source,
                  pipe   = pipe(spy_count.spy ,
                                count.sink),
                  result = dict(from_count     =     count.future,
                                from_spy_count = spy_count.future))

    assert result.from_count == result.from_spy_count == len(the_source)


def test_fork_and_branch():
# ANCHOR: fork_and_branch
    from dataflow import sink, map as dmap, pipe, fork, branch, push

    # Some pipeline components
    c1 = []; C1 = sink(c1.append)
    c2 = []; C2 = sink(c2.append)
    e1 = []; E1 = sink(e1.append)
    e2 = []; E2 = sink(e2.append)

    A = dmap(lambda n:n+1)
    B = dmap(lambda n:n*2)
    D = dmap(lambda n:n*3)

    # graph1 and graph2 are eqivalent networks. graph1 is constructed with
    # fork ...
    graph1 = pipe(A, fork((B,C1),
                          (D,E1)))
    # ... while graph2 is built with branch.
    graph2 = pipe(A, branch(B,C2), D,E2)

    # Feed the same data into the two networks.
    the_data = list(range(10, 50, 4))
    push(source=the_data, pipe=graph1)
    push(source=the_data, pipe=graph2)

    # Confirm that both networks produce the same results.
    assert c1 == c2
    assert e1 == e2
# ANCHOR_END: fork_and_branch


def test_branch_closes_sideways():
    from dataflow import sink, push, pipe, branch

    the_source = range(10)
    branch_result = []; the_branch_sink = sink(branch_result.append)
    main_result   = []; the_main_sink   = sink(  main_result.append)

    push(source = the_source,
         pipe   = pipe(branch(the_branch_sink),
                                the_main_sink))

    with raises(StopIteration):
        the_branch_sink.send(99)


def test_chain_pipes():
    from dataflow import sink, map as dmap, push, pipe

    # Pipelines must end in sinks. If the last component of a pipe is
    # not a sink, the pipe may be used as a component in a bigger
    # pipeline, but it will be impossible to feed any data into it
    # until it is connected to some other component which ends in a
    # sink.

    # Some basic pipeline components
    s1 = []; sink1 = sink(s1.append)
    s2 = []; sink2 = sink(s2.append)

    A = dmap(lambda n:n+1)
    B = dmap(lambda n:n*2)
    C = dmap(lambda n:n-3)

    # Two different ways of creating equivalent networks: one of them
    # groups the basic components into sub-pipes
    graph1 = pipe(     A, B,       C, sink1)
    graph2 = pipe(pipe(A, B), pipe(C, sink2))

    # Feed the same data into the two networks
    the_source = list(range(40))

    push(source=the_source, pipe=graph1)
    push(source=the_source, pipe=graph2)

    # Confirm that both networks produce the same results.
    assert s1 == s2


def test_reuse_unterminated_pipes():
    from dataflow import map as dmap, pipe, sink, branch, push

    # Open-ended pipes must be connected to a sink before they can
    # receive any input. Open-ended pipes are reusable components: any
    # such pipe can be used in different points in the same or
    # different networks. They are completely independent.

    def add(n):
        return dmap(lambda x:x+n)

    A,B,C,D,E,X,Y,Z = 1,2,3,4,5,6,7,8

    component = pipe(add(X),
                     add(Y),
                     add(Z))

    s1 = []; sink1 = sink(s1.append)
    s2 = []; sink2 = sink(s2.append)

    # copmonent is being reused twice in this network
    graph = pipe(add(A),
                 branch(add(B), component, add(C), sink1),
                 add(D), component, add(E), sink2)

    the_source = list(range(10,20))
    push(source=the_source, pipe=graph)

    assert s1 == [ n + A + B + X + Y + Z + C for n in the_source ]
    assert s2 == [ n + A + D + X + Y + Z + E for n in the_source ]


def test_reuse_terminated_pipes():
    from dataflow import map as dmap, sink, pipe, branch, push

    # Sink-terminated pipes are also reusable, but do note that if
    # such components are reused in the same graph, the sink at the
    # end of the component will receive inputs from more than one
    # branch: they share the sink; the branches are joined.

    def add(n):
        return dmap(lambda x:x+n)

    A,B,C,X,Y,Z = 1,2,3,4,5,6

    collected_by_sinks = []; sink1 = sink(collected_by_sinks.append)

    component = pipe(add(X),
                     add(Y),
                     add(Z),
                     sink1)

    graph = pipe(add(A),
                 branch(add(B), component),
                        add(C), component)

    the_source = list(range(10,20))
    push(source=the_source, pipe=graph)

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
    import dataflow as df

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
    import dataflow as df

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
    import dataflow as df
    with raises(ValueError):
        df.slice(*args)


def test_pipes_must_end_in_a_sink():
    import dataflow as df

    the_source    = range(10)
    sinkless_pipe = df.map(abs)

    with raises(df.IncompletePipe):
        df.push(source = the_source,
                pipe   = sinkless_pipe)


def test_count_filter():
    from dataflow import count_filter, sink, push, pipe

    # count_filter provides a future/filter pair.
    # This is a simple interface to keep track of
    # how many entries satisfy the predicate and
    # how many are filtered out.

    the_source  = list(range(21))
    predicate   = lambda n: n % 2

    odd      = count_filter(predicate)
    filtered = []; the_sink = sink(filtered.append)

    result = push(source = the_source,
                  pipe   = pipe(odd.filter, the_sink),
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
    import dataflow as df
    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    result = []; the_sink = df.sink(result.append, args="x")

    df.push(source = the_source,
            pipe   = the_sink  )

    assert result == list(letters)


def test_map_with_namespace_args_out():
    import dataflow as df
    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    make_upper_case = df.map(str.upper, args="x", out="upper_x")

    result = []; the_sink = df.sink(result.append, args="upper_x")

    df.push(source = the_source,
            pipe   = df.pipe(make_upper_case, the_sink))

    assert result == list(letters.upper())


def test_map_with_namespace_item():
    import dataflow as df

    # item replaces the input with the output

    letters         = string.ascii_lowercase
    the_source      = (dict(i=i, x=x) for i, x in enumerate(letters))
    make_upper_case = df.map(str.upper, item="x")

    result = []; the_sink = df.sink(result.append, args="x")

    df.push(source = the_source,
            pipe   = df.pipe(make_upper_case, the_sink))

    assert result == list(letters.upper())


def test_filter_with_namespace():
    import dataflow as df
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
    import dataflow as df
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    result = []; the_sink = df.sink(result.append)
    df.push(source = the_source,
            pipe   = df.pipe("x", the_sink))

    assert result == the_source_elements


def test_implicit_element_picking_in_fork():
    import dataflow as df
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    left  = [];  left_sink = df.sink( left.append)
    right = []; right_sink = df.sink(right.append)

    df.push(source = the_source,
            pipe   = df.fork(("x",  left_sink),
                             ("y", right_sink)))

    assert left == [-i for i in right] == the_source_elements


def test_implicit_element_picking_in_branch():
    import dataflow as df
    the_source_elements = list(range(10))
    the_source          = (dict(x=i, y=-i) for i in the_source_elements)

    left  = [];  left_sink = df.sink( left.append)
    right = []; right_sink = df.sink(right.append)

    df.push(source = the_source,
            pipe   = df.pipe(df.branch("x",  left_sink),
                             right_sink))

    assert left == [-i["y"] for i in right] == the_source_elements
