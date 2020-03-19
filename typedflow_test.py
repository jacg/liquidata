from operator import sub, rshift, add
import typedflow as tf

from pytest import mark, raises
parametrize = mark.parametrize

func = type(lambda: 1)
X = TypeError

# Using the symbols rather than the functions directly makes the table and the
# test-suite reports easier to read.
ops = {'-': sub, '+': add, '>>': rshift}

RHS =                         (tf.source, tf.pipe  , tf.sink  ,   func   )

table = {'-'  : { tf.source : (    X    , tf.source, tf.ready , tf.source),
                  tf.pipe   : (    X    , tf.pipe  , tf.sink  , tf.pipe  ),
                  tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                  func      : (    X    , tf.pipe  , tf.sink  ,     X    )},

         '+'  : { tf.source : (    X    ,     X    ,     X    , tf.source),
                  tf.pipe   : (    X    ,     X    ,     X    , tf.pipe  ),
                  tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                  func      : (    X    , tf.pipe  , tf.sink  ,     X    )},

         '>>' : { tf.source : (    X    ,     X    , tf.ready , tf.ready ),
                  tf.pipe   : (    X    ,     X    ,     X    , tf.sink  ),
                  tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                  func      : (    X    ,     X    , tf.sink  ,     X    )},

        }

@parametrize('LHS_type, op_symbol, RHS_type, result',
             [ (lhs, op_symbol, rhs, result)
               for (op_symbol, sub_table) in table.items()
               for (lhs, results)  in sub_table.items()
               for (rhs, result)   in zip(RHS, results) ])
def test_operator_type_matrices(LHS_type, op_symbol, RHS_type, result):
    sample_instance = { tf.source : tf.source(1),
                        tf.pipe   : tf.pipe()  ,
                        tf.sink   : tf.sink(1)  ,
                        func      : lambda: 1  }

    lhs = sample_instance[LHS_type]
    rhs = sample_instance[RHS_type]
    op  = ops[op_symbol]

    if result is TypeError:

        with raises(TypeError):
            op(lhs, rhs)

    else:
        assert isinstance(op(lhs, rhs), result)


def test_source_to_sink_side_effect():
    the_data = list(range(10))
    result = []
    (tf.source(the_data) >> result.append)()
    assert result == the_data


def test_source_map_sink_side_effect():

    def square(n):
        return n*n

    the_data = list(range(10))
    result = []
    (tf.source(the_data) - square >> result.append)()
    assert result == list(map(square, the_data))


def test_source_filter_sink_side_effect():

    def odd(n):
        return n % 2 != 0

    the_data = list(range(10))
    result = []
    (tf.source(the_data) + odd >> result.append)()
    assert result == list(filter(odd, the_data))


# TODO:
#
# Check that source construction argument is iterable
