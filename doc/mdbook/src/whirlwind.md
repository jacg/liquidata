# Whirlwind tour of basic features

```python
from liquidata import pipe, sink

fn = pipe(
    [ sink(print) ],
    { str.isalpha },
    str.upper)

fn(dir())
```

+ `pipe` accepts an arbitrary number of pipe components.

+ `pipe` returns a function (callable).

+ The function created by `pipe` accepts an iterable argument, and pushes its
  elements through the pipeline.

+ Square brackets (`[ ]`) create *independent branches*: the same data are sent
  both into the branch and downstream.

+ `sink` feeds items into a (presumably) side-effectful function (`print` in
  this example), and prevents them from going any further downstream.

+ Braces (`{ }`) are filters: they should contain a predicate (a function whose
  return value is interpreted as a boolean; `str.isalpha`, in this example), and
  will prevent any items which don't satisfy the predicate, from progressing
  further down the pipe.

+ Unadorned functions are mappings: they accept incoming items, and the values
  they return are sent downstream.

+ Any items that reach the end of a pipe are, by default, collected into a list
  and returned.

Consequently, in the above example:

+ The names in the global scope (`dir()`) are fed into the pipeline, one by one.

+ Each incoming item is printed out.

+ Items containing non-alphabetic characters are filtered out.

+ All remaining items are uppercased ...

+ ... and returned in a list.

```python
from operator import add
from liquidata import source, pipe, out, arg

pipe(
    source << dir(),
    [ out.incoming ],
    { str.isalpha },
    { arg > 5 : len },
    [ str.upper, out.big ],
    [ len, [ out.ADD(add) ], out.SUM(into(sum)) ],
    str.lower,
    out.small)
```

+ Rather than using `pipe` to create a reusable function, we feed data into the
  pipeline directly, by including the source in the pipeline. The following
  three variations have the same meaning:

  - `source << dir()`
  - `dir() >> source`
  - `source(dir())`

+ Rather than using a side-effect (`print`) to inspect what is passing through
  the pipe at various points, in this example we used *named outputs*. `out` is
  a sink which collects values so that they can be returned from the pipe.

  - The presence of multiple `out`s in the graph, causes the pipeline to return
    a namespace, rather than a single result.

  - If a pipe (or branch; branches are just pipes) does not explicitly end in a
    `sink` or `out`, then it is implicitly capped with an anonymous `out`.

  - `out.incoming` will collect all items into a list, and arrange for the list
    to be bound to the name `incoming` in the namespace that is returned by the
    pipe as a whole.

  - `out.ADD(add)` uses a binary function (`add`) to fold or reduce all the
    values it receives into a single one, which will be placed in the returned
    namespace under the specified name, `ADD`.

  - `out.SUM(into(sum))` feeds the items it receives into a callable which
    consumes iterables (in this case `sum`, but keep in mind that there are very
    many ready-made options here: `set`, `min`/`max`, `collections.Counter`, `',
    '.join`, etc.). The result will bound in the returned namespace under the
    name `SUM`.

  - `arg` provides a concise syntax for very simple anonymous functions: ones
    consisting of the application of an operator and a constant to the
    function's argument. In this example, we have `arg > 5`. This is equivalent
    to `lambda arg: arg > 5`.

  - Braces containing colons are *key-filters*. In this example, `{ arg > 5 :
    len }`. The predicate appears before the colon, but, rather than being
    applied to the item in the pipe, it is applied to the result the key
    function (specified after the colon) returns when given the item.

    If the verdict is positive, the *original* item (rather than the value
    returned by the key function) progresses downstream.

    In this example, strings are coming through the pipe, and strings continue
    past the filter, but only those whose `len` is greater than `5`.

  - Branches can be nested: `[ len, [ out.ADD(add) ], out.SUM(into(sum)) ]`.

  - The list of items reaching the end of the main pipe, unlike in the first
    example, is not anonymous: it is bound to the name `small` in the returned
    namespace.

+ The result returned by the pipeline is a namespace containing 5 names.
