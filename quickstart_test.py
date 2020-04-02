from liquidata   import *
from testhelpers import *

a,b,c,f,g,h = symbolic_functions('abcfgh')
abc012 = namespace_source()

def test_quickstart():

    # ANCHOR: guinea_pigs
    assert        f  (3)       == 'f(3)'
    assert        f(g(4))      == 'f(g(4))'
    assert sym_add(  2 ,   3)  == '(2 + 3)'
    assert sym_mul(f(2), g(3)) == '(f(2) * g(3))'
    # ANCHOR_END: guinea_pigs

    # ANCHOR: function_composition
    doit = pipe(f, g, h)
    assert doit(range(3)) == ['h(g(f(0)))', 'h(g(f(1)))', 'h(g(f(2)))']
    # ANCHOR_END: function_composition
    # ANCHOR: equivalence_to_multiple_maps
    piped  = pipe(    f,     g,     h)(range(10))
    mapped = list(map(h, map(g, map(f, range(10)))))
    assert piped == mapped
    # ANCHOR_END: equivalence_to_multiple_maps

    # ANCHOR: filter
    assert pipe( odd )(range(4)) == [False, True, False, True]
    assert pipe({odd})(range(4)) == [         1 ,          3 ]
    # ANCHOR_END: filter

    # ANCHOR: join
    assert pipe(join)(['abc', '', 'd', 'efg'])       == list('abcdefg')
    assert pipe(lambda n: n*str(n), join)([3,1,0,2]) == list('333122')
    assert pipe(range, join)(range(4))               == [0, 0,1, 0,1,2]
    assert pipe(flat(range))(range(4))               == [0, 0,1, 0,1,2]
    # ANCHOR_END: join

    # ANCHOR: fold
    assert pipe(out(sym_add))('xyzw') == '(((x + y) + z) + w)'
    assert pipe(out(sym_add))('xyzw') == reduce(sym_add, 'xyzw')
    # ANCHOR_END: fold

    # ANCHOR: fold_with_initial
    assert pipe(out(sym_add, 'A'))('xyz') == '(((A + x) + y) + z)'
    assert pipe(out(sym_add, 'A'))('xyz') == reduce(sym_add, 'xyz', 'A')
    # ANCHOR_END: fold_with_initial

    # ANCHOR: side_effects
    result = []
    pipe(f, sink(result.append))(range(3))
    assert result == list(map(f, range(3)))
    # ANCHOR_END: side_effects

    # ANCHOR: branch
    side = []
    main = pipe(f,
                [g, sink(side.append)],  # This is a branch
                h)(range(3))
    assert side == ['g(f(0))', 'g(f(1))', 'g(f(2))']
    assert main == ['h(f(0))', 'h(f(1))', 'h(f(2))']
    # ANCHOR_END: branch

    # ANCHOR: named_outs
    result = pipe(f,
                  [g, out.side],  # This is a branch
                  h,
                  out.main)(range(3))
    assert result.side == ['g(f(0))', 'g(f(1))', 'g(f(2))']
    assert result.main == ['h(f(0))', 'h(f(1))', 'h(f(2))']
    # ANCHOR_END: named_outs

    # ANCHOR: spy
    spy1, spy2 = [], []
    pipe(f, [sink(spy1.append)], g)
    #pipe(f,   spy(spy2.append) , g)

    pipe(f, [out.X], g)
    #pipe(f,  spy.X , g)
    # ANCHOR_END: spy

    # ANCHOR: name_single
    # Make a namespace containing one name out of a single value
    one = pipe(name.x)(range(3))
    two = list(Namespace(x=n) for n in range(3))
    assert one == two

    # Make a namespace containing two names, out of a 2-tuple
    data = [(1,2), (3,4), (9,8)]
    one = pipe(name.a.b)(data)
    two = list(Namespace(a=a, b=b) for (a,b) in data)
    assert one == two
    # ANCHOR_END: name_single

    # ANCHOR: get_as_attrgetter
    ns = name.a.b.c('xyz')
    assert get.b  (ns) == attrgetter('b')     (ns)
    assert get.a.c(ns) == attrgetter('a', 'c')(ns)

    expected = [('a0', 'c0'), ('a1', 'c1'), ('a2', 'c2')]
    assert pipe(    get    .a   .c)  (abc012) == expected
    assert pipe(attrgetter('a', 'c'))(abc012) == expected
    # ANCHOR_END: get_as_attrgetter

    # ANCHOR: abc012
    assert abc012 == [Namespace(a='a0', b='b0', c='c0'),
                      Namespace(a='a1', b='b1', c='c1'),
                      Namespace(a='a2', b='b2', c='c2')]
    # ANCHOR_END: abc012

    # ANCHOR: get_as_star
    assert sym_add(2,3) == '(2 + 3)'

    assert pipe(get.a.b * sym_add)(abc012) == ['(a0 + b0)', '(a1 + b1)', '(a2 + b2)']
    # ANCHOR_END: get_as_star

    # ANCHOR: star
    data = [(1,2), (3,4), (9,8)]
    assert pipe(star(sym_add))(data) == ['(1 + 2)', '(3 + 4)', '(9 + 8)']
    # ANCHOR_END: star

    # ANCHOR: put
    data = pipe(name.a.b)([(1,2), (3,4), (9,8)])

    result = pipe(get.a.b * mul >> put.ab)(data)

    assert pipe(get.a )(result) == [1  , 3  , 9  ]
    assert pipe(get.b )(result) == [  2,   4,   8]
    assert pipe(get.ab)(result) == [1*2, 3*4, 9*8]
    # ANCHOR_END: put

    # ANCHOR: multiple_put
    data = pipe(name.a.b)([(1,2), (3,4), (9,8)])

    def hilo(a,b):
        return max(a,b), min(a,b)

    result = pipe(get.a.b * hilo >> put.hi.lo)(data)

    assert pipe(get.a )(result) == [1  , 3  , 9  ]
    assert pipe(get.b )(result) == [  2,   4,   8]

    assert pipe(get.hi)(result) == [  2,   4, 9  ]
    assert pipe(get.lo)(result) == [1  , 3  ,   8]
    # ANCHOR_END: multiple_put

    # ANCHOR: nested_pipes
    inner = pipe(   f, g    )
    outer = pipe(a, inner, b)
    assert outer(range(3)) == pipe(a, f, g, b)(range(3))
    # ANCHOR_END: nested_pipes
