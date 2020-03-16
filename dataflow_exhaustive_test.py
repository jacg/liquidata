from pytest import mark
parametrize = mark.parametrize

import dataflow as df


@parametrize("component",
             (df.map   (lambda x: x)    ,
              df.filter(lambda x: x > 0),
              df.sink  (print)          ,
              df.branch(df.sink(print)) ,
              df.pipe  (df.map(abs))    ))
def test_string_to_pick_ignores_components(component):
    assert component is df._string_to_pick(component)


def test_string_to_pick():

    # string_to_pick creates a pipe component that picks
    # an item from the namespace and pushes it through the pipe

    the_source_elements = list(range(10))
    the_source          = (dict(x=i**2, y=i) for i in the_source_elements)

    result = []; the_sink = df.sink(result.append)
    df.push(source = the_source,
            pipe   = df.pipe(df._string_to_pick("y"), the_sink))

    assert result == the_source_elements
