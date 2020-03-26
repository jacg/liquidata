from operator  import itemgetter, lt
from functools import reduce
from itertools import chain
from argparse  import Namespace

from pytest import mark, raises
xfail = mark.xfail
TODO = mark.xfail(reason='TODO')
parametrize = mark.parametrize

from hypothesis            import given
from hypothesis            import assume
from hypothesis.strategies import tuples
from hypothesis.strategies import integers
from hypothesis.strategies import none
from hypothesis.strategies import one_of, sampled_from


def test_trivial():
    from reboot import flow
    data = list(range(10))
    result = []
    net = flow(result.append)
    net(data)
    assert result == data


def test_map():
    from reboot import flow
    data = list(range(10))
    f, = symbolic_functions('f')
    result = []
    net = flow(f, result.append)
    net(data)
    assert result == list(map(f, data))


def test_filter():
    from reboot import flow
    data = list(range(10))
    result = []
    net = flow({odd}, result.append)
    net(data)
    assert result == list(filter(odd, data))


def test_branch():
    from reboot import flow
    data = list(range(10))
    branch, main = [], []
    net = flow([branch.append], main.append)
    net(data)
    assert main   == data
    assert branch == data


def test_integration_1():
    from reboot import flow, arg as _
    data = range(20)
    f, g, h = square, (_ +  1), (_ +   2)
    a, b, c = odd   , (_ > 50), (_ < 100)
    s, t    = [], []
    net = flow(f,
               {a},
               [g, {b}, s.append],
               h,
               {c},
               t.append)
    net(data)
    assert s == list(filter(b, map(g, filter(a, map(f, data)))))
    assert t == list(filter(c, map(h, filter(a, map(f, data)))))


def test_fold_and_return():
    from reboot import flow, out
    data = range(3)
    net = flow(out.total(sym_add))
    assert net(data).total == reduce(sym_add, data)


def test_fold_with_initial_value():
    from reboot import flow, out
    data = range(3)
    net = flow(out.total(sym_add, 99))
    assert net(data).total == reduce(sym_add, data, 99)


def test_return_value_from_branch():
    from reboot import flow, out
    data = range(3)
    net = flow([out.branch(sym_add)],
                out.main  (sym_mul))
    result = net(data)
    assert result.main   == reduce(sym_mul, data)
    assert result.branch == reduce(sym_add, data)


def test_implicit_collect_into_list():
    from reboot import flow, out
    data = range(3)
    net = flow(out.everything)
    assert net(data).everything == list(data)


def test_nested_branches():
    from reboot import flow, out
    f,g,h,i = symbolic_functions('fghi')
    data = range(3)
    net = flow([[f, out.BB], g, out.BM],
                [h, out.MB], i, out.MM )
    res = net(data)
    assert res.BB == list(map(f, data))
    assert res.BM == list(map(g, data))
    assert res.MB == list(map(h, data))
    assert res.MM == list(map(i, data))


def test_get_implicit_map():
    from reboot import flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = flow(get.A, out.B)
    assert net(data, A=f).B == list(map(f, data))


def test_get_implicit_filter():
    from reboot import flow, get, out
    data = list(range(6))
    f = odd
    net = flow(get.A, out.B)
    assert net(data, A={f}).B == list(filter(f, data))


@TODO
def test_implicit_filter_get():
    from reboot import flow, get, out
    data = list(range(6))
    f = odd
    net = flow({get.A}, out.B)
    assert net(data, A=f).B == list(filter(f, data))


def test_get_in_branch():
    from reboot import flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = flow([get.A, out.branch], out.main)
    r = net(data, A=f)
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_get_branch():
    from reboot import flow, get, out
    data = list(range(3))
    f, = symbolic_functions('f')
    net = flow(get.A, out.main)
    r = net(data, A=[f, out.branch])
    assert r.main   ==             data
    assert r.branch == list(map(f, data))


def test_flat_map():
    from reboot import flow, FlatMap, out
    data = range(4)
    f = range
    net = flow(FlatMap(f), out.X)
    assert net(data).X == list(chain(*map(f, data)))


@TODO
def test_get_implicit_sink():
    from reboot import flow, get, out
    data = list(range(3))
    f = sym_add
    net = flow(out.OUT(get.SINK))
    assert net(data, SINK=f).OUT == reduce(f, data)


def test_pipe_as_function():
    from reboot import pipe
    f,g = symbolic_functions('fg')
    pipe_fn = pipe(f,g).fn()
    assert pipe_fn(6) == (g(f(6)),)


def test_pipe_as_multi_arg_function():
    from reboot import pipe
    f, = symbolic_functions('f')
    pipe_fn = pipe(sym_add, f).fn()
    assert pipe_fn(6,7) == (f(sym_add(6,7)),)


def test_pipe_on_filter():
    from reboot import pipe, FlatMap
    f = odd
    pipe_fn = pipe({f}).fn()
    assert pipe_fn(3) == (3,)
    assert pipe_fn(4) == ()


def test_pipe_on_flatmap():
    from reboot import pipe, FlatMap
    f = range
    pipe_fn = pipe(FlatMap(f)).fn()
    assert pipe_fn(3) == (0,1,2)
    assert pipe_fn(5) == (0,1,2,3,4)


def test_pipe_with_get_as_function():
    from reboot import pipe, get
    f,g,h = symbolic_functions('fgh')
    pipe = pipe(f, get.FN)
    pipe_g = pipe.fn(FN=g)
    pipe_h = pipe.fn(FN=h)
    assert pipe_g(6) == (g(f(6)),)
    assert pipe_h(7) == (h(f(7)),)


def test_pipe_as_component():
    from reboot import pipe, flow, out
    data = range(3,6)
    a,b,f,g = symbolic_functions('abfg')
    pipe = pipe(f, g).pipe()
    net = flow(a, pipe, b, out.X)
    assert net(data).X == list(map(b, map(g, map(f, map(a, data)))))


def test_pick_item():
    from reboot import flow, pick, out
    names = 'abc'
    values = range(3)
    f, = symbolic_functions('f')
    data = [dict((name, value) for name in names) for value in values]
    net = flow(pick.a, f, out.X)
    assert net(data).X == list(map(f, values))


def test_pick_multiple_items():
    from reboot import flow, pick, out
    names = 'abc'
    ops = tuple(symbolic_functions(names))
    values = range(3)
    data = [{name:op(N) for (name, op) in zip(names, ops)} for N in values]
    net = flow(pick.a.b, out.X)
    assert net(data).X == list(map(itemgetter('a', 'b'), data))


def test_on_item():
    from reboot import flow, on, out
    names = 'abc'
    f, = symbolic_functions('f')
    values = range(3)
    data = [{name:N for name in names} for N in values]
    net = flow(on.a(f), out.X)
    expected = [d.copy() for d in data]
    for d in expected:
        d['a'] = f(d['a'])
    assert net(data).X == expected


def namespace_source(keys='abc', length=3):
    indices = range(length)
    return [{key:f'{key}{i}' for key in keys} for i in indices]


def test_args_single():
    from reboot import flow, args, out
    data = namespace_source()
    f, = symbolic_functions('f')
    net = flow((args.c, f), out.X)
    assert net(data).X == list(map(f, map(itemgetter('c'), data)))


def test_args_many():
    from reboot import flow, args, out
    data = namespace_source()
    net = flow((args.a.b, sym_add), out.X)
    expected = list(map(sym_add, map(itemgetter('a'), data),
                                 map(itemgetter('b'), data)))
    assert net(data).X == expected

def test_put_single():
    from reboot import flow, put, out
    data = namespace_source()
    f, = symbolic_functions('f')
    net = flow((itemgetter('b'), f, put.xxx), out.X)
    expected = [d.copy() for d in data]
    for d in expected:
        d['xxx'] = f(d['b'])
    assert net(data).X == expected


def test_put_many():
    from reboot import flow, put, out
    data = namespace_source()
    l,r = symbolic_functions('lr')
    def f(x):
        return l(x), r(x)
    net = flow((f, put.left.right), out.X)
    expected = [d.copy() for d in data]
    for d in expected:
        d['left' ], d['right'] = f(d)
    assert net(data).X == expected


def test_args_single_put_single():
    from reboot import flow, args, put, out
    data = namespace_source()
    f, = symbolic_functions('f')
    net = flow((args.b, f, put.result), out.X)
    expected = [d.copy() for d in data]
    for d in expected:
        d['result'] = f(d['b'])
    assert net(data).X == expected


def test_args_single_put_many():
    from reboot import flow, args, put, out
    l,r = symbolic_functions('lr')
    def f(x):
        return l(x), r(x)
    data = namespace_source()
    net = flow((args.c, f, put.l.r), out.X)
    expected = [d.copy() for d in data]
    for d in expected:
        result = f(d['c'])
        d['l'], d['r'] = result
    assert net(data).X == expected


def test_args_single_filter():
    from reboot import flow, args, out, arg as _
    data = (dict(a=1, b=2),
            dict(a=3, b=3),
            dict(a=2, b=1),
            dict(a=8, b=9))
    net = flow((args.b, {_ > 2}), out.X)
    expected = list(filter(_ > 2, map(itemgetter('b'), data)))
    assert net(data).X == expected


@TODO
def test_args_many_filter():
    from reboot import flow, args, out
    data = (dict(a=1, b=2),
            dict(a=3, b=3),
            dict(a=2, b=1),
            dict(a=8, b=9))
    net = flow((args.a.b, {lt}), out.X)
    expected = (dict(a=1, b=2),
                dict(a=8, b=9))
    assert net(data).X == expected


def test_args_single_flatmap():
    from reboot import flow, FlatMap, args, out
    data = (dict(a=1, b=2),
            dict(a=0, b=3),
            dict(a=3, b=1))
    net = flow((args.a, FlatMap(lambda n:n*[n])), out.X)
    assert net(data).X == [1,3,3,3]


def test_args_many_flatmap():
    from reboot import flow, FlatMap, args, out
    data = (dict(a=1, b=9),
            dict(a=0, b=8),
            dict(a=3, b=7))
    net = flow((args.a.b, FlatMap(lambda a,b:a*[b])), out.X)
    assert net(data).X == [9,7,7,7]



small_ints         = integers(min_value=0, max_value=15)
small_ints_nonzero = integers(min_value=1, max_value=15)
slice_arg          = one_of(none(), small_ints)
slice_arg_nonzero  = one_of(none(), small_ints_nonzero)

@given(one_of(tuples(small_ints),
              tuples(small_ints, small_ints),
              tuples(slice_arg,  slice_arg, slice_arg_nonzero)))
def test_slice_downstream(spec):

    from reboot import flow, Slice, out
    data = list('abcdefghij')
    net = flow(Slice(*spec), out.X)
    result = net(data).X
    specslice = slice(*spec)
    assert result == data[specslice]
    assert result == data[specslice.start : specslice.stop : specslice.step]


# slice takes an optional argument close_all. If this argument
# is False (default), slice will close the innermost branch in
# which the component is plugged in after the component iterates
# over all its entries. However, when set to True, the behaviour
# is to close the outermost pipeline, resulting in a full stop of
# the data flow.
@parametrize("close_all", (False, True))
def test_slice_close_all(close_all):
    from reboot import Slice, flow, out

    data = list(range(20))
    n_elements = 5
    the_slice = Slice(n_elements, close_all=close_all)

    net = flow([the_slice, out.branch], out.main)
    result = net(data)

    if close_all:
        assert result.branch == data[:n_elements]
        assert result.main   == data[:n_elements]
    else:
        assert result.branch == data[:n_elements]
        assert result.main   == data


@parametrize('args',
             ((      -1,),
              (None, -1),
              (-1, None),
              (None, None, -1),
              (None, None,  0),
             ))
def test_slice_raises_ValueError(args):
    from reboot import Slice
    with raises(ValueError):
        Slice(*args)


from operator import   eq, ne, lt, gt, le, ge, add, sub, mul, floordiv, truediv
binops = sampled_from((eq, ne, lt, gt, le, ge, add, sub, mul, floordiv, truediv))

@given(binops, integers(), integers())
def test_arg_as_lambda_binary(op, lhs, rhs):
    assume(op not in (truediv, floordiv) or rhs != 0)
    from reboot import arg

    a  =           op(arg, rhs)
    ar =           op(lhs, arg)
    b  = lambda x: op(x  , rhs)
    br = lambda x: op(lhs, x)
    assert a (lhs) == b (lhs)
    assert ar(rhs) == br(rhs)


from operator import  neg, pos
unops = sampled_from((neg, pos))

@given(unops, integers())
def test_arg_as_lambda_binary(op, operand):
    from reboot import arg

    a  =           op(arg)
    b  = lambda x: op(x)
    assert a(operand) == b(operand)


def test_arg_as_lambda_getitem():
    from reboot import arg
    data = 'abracadabra'
    assert (arg[3])(data) == (lambda x: x[3])(data)


@xfail(reason="__getitem__ can't distinguish x[a,b] from x[(a,b)]")
def test_arg_as_lambda_get_multilple_items():
    from reboot import arg
    data = 'abracadabra'
    assert (arg[3,9,4])(data) == (lambda x: (x[3], x[9], x[4]))(data)


def test_arg_as_lambda_getattr():
    from reboot import arg
    data = Namespace(a=1, b=2)
    assert (arg.a)(data) == (lambda x: x.a)(data)


def test_arg_as_lambda_call_single_arg():
    from reboot import arg
    def square(x):
        return x * x
    assert (arg(3))(square) == (lambda x: x(3))(square)


def test_arg_as_lambda_call_two_args():
    from reboot import arg
    assert (arg(2,3))(add) == (lambda x: x(2,3))(add)


def test_arg_as_lambda_call_keyword_args():
    from reboot import arg
    assert (arg(a=6, b=7))(dict) == (lambda x: x(a=6, b=7))(dict)


def test_take():
    from reboot import flow, take, out
    data = 'abracadabra'
    net = flow(take(5), out.X)(data).X == ''.join(data[:5])


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
