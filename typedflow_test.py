from operator import sub, rshift, add
import typedflow as tf

from pytest import mark, raises
parametrize = mark.parametrize

func = type(lambda: 1)
X = TypeError

RHS =                           (tf.source, tf.pipe  , tf.sink  ,   func   )

table = {sub    : { tf.source : (    X    ,     X    ,     X    ,     X    ),
                    tf.pipe   : (    X    , tf.pipe  ,     X    , tf.pipe  ),
                    tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                    func      : (    X    , tf.pipe  ,     X    ,     X    )},

         rshift : { tf.source : (    X    , tf.source, tf.ready , tf.source),
                    tf.pipe   : (    X    ,     X    ,     X    , tf.pipe  ),
                    tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                    func      : (    X    , tf.pipe  , tf.sink  ,     X    )},

         add    : { tf.source : (    X    ,     X    ,     X    ,     X    ),
                    tf.pipe   : (    X    ,     X    ,     X    , tf.pipe  ),
                    tf.sink   : (    X    ,     X    ,     X    ,     X    ),
                    func      : (    X    ,     X    ,     X    ,     X    )}}

@parametrize('LHS_type, op, RHS_type, result',
             [ (lhs, op, rhs, result)
               for (op, sub_table) in table.items()
               for (lhs, results)  in sub_table.items()
               for (rhs, result)   in zip(RHS, results) ])
def test_operator_type_matrices(LHS_type, op, RHS_type, result):
    sample_instance = { tf.source : tf.source(),
                        tf.pipe   : tf.pipe()  ,
                        tf.sink   : tf.sink()  ,
                        func      : lambda: 1  }

    lhs = sample_instance[LHS_type]
    rhs = sample_instance[RHS_type]

    if result is TypeError:

        with raises(TypeError):
            op(lhs, rhs)

    else:
        assert isinstance(op(lhs, rhs), result)
