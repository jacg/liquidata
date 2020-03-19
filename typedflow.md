# Thoughts on design and implementation in terms of types and operators

+ Introduce 4 primary types: `source`, `pipe`, `sink` and `ready`.

+ Think of `-` as a line connecting two elements in a network: forget all
  arithmetic connotations.

  Use `-` as the basic plumbing operator for connecting

  * `source - pipe  ->  source`
  * `pipe   - pipe  ->  pipe`
  * `pipe   - sink  ->  sink`
  * `source - sink  ->  ready`

  Additionally, if `-` receives a callable as its right operand, it uses it to
  make a pipe that maps the callable over the stream, and connects it to its
  left operand. This makes `-` work in a few more situations:

  * `source - func  ->  source`
  * `pipe   - func  ->  pipe`
  * `func   - pipe  ->  pipe`
  * `func   - sink  ->  sink`

  where the last two are situations where it can sensibly work with the callable
  as the left operand.

+ Think of `+` as `-` with a barrier across it. At the barrier there is a guard
  (predicate) who decides which elements can get through: forget all arithmetic
  connotations.

  Use `+` to lift functions into the pipeline as filters (in contrast to `-`
  which can lift functions into the) pipeline as maps.

  * `source + func  ->  source`
  * `pipe   + func  ->  pipe`
  * `func   + pipe  ->  pipe`
  * `func   + sink  ->  sink`

+ We have map, we have filter, where is reduce? Let's spell it `>>`. Use it to
  lift functions in to the network as sinks:

  * `source >> func  ->  ready`
  * `pipe   >> func  ->  sink`

  As reduce turns functions into sinks, it makes no sense for it to work with
  the function on the upstream side, unlike in the case of `-` and `+`.

  It would be harmless, but not necessary, to also allow

  * `source >> sink  ->  ready`
  * `pipe   >> sink  ->  sink`

+ It's not obvious how to feed an initial value into reduce implemented as `>>`.
  Some ideas are discussed below.

+ Think of `/` as a `-` which points in a different direction. It sends the
  stream off to the side: it's a branch. Here are some examples:

  ```
  src - pipeA - pipeB / sinkX - pipeC - sinkY
  ```

  where `/ sinkX` is essentially a spy, so no separate spy utility is really
  needed.

  ```
  src - pipeA / (pipeM - pipeN - sinkX) - pipeB - sinkY
  ```

  where `/ (pipeM - pipeN - sinkX)` is a longer branch. However, if such a
  branch has functions in its first two positions, then we don't get access to
  our overloaded `-`, so our type would need to be injected somehow. So far, I
  haven't found anything cleaner than:

  ```
  src - pipeA / (pipe(fnM) - fnN - sinkX) - pipeB - sinkY
  ```

+ We could implement the old fork with `|` (or `&`, `^`; the precedence rules
  essentially limit us to these options), and it would look like this:

  ```
  src - pipe_A - pipe_B ( pipe_C1 - sink_C2
                        | sink_D1
                        | pipe_E1 - pipe_E2 - sink_E3 )
  ```

  but is there any point? given that the equivalent graph can be made with
  branch like this:


  ```
  src - pipe_A - pipe_B / (pipe_C1 - sink_C2)
                        /  sink_D1
                        - (pipe_E1 - pipe_E2 - sink_E3)
  ```

+ It is important not to reject arbitrary callables in the overload resolution
  of `-`, `+` and `>>` (and whatever other operators we might use). If an
  operand is in a position where a callable might be found, and its type is not
  one of the types playing some specific role (`source`, `pipe`, `sink` ...
  selectors?) it should probably be treated as a callable. But this will delay
  typechecking, and early type checking is a design goal of this version.

+ `ready` is a callable

   ```
   graph = source(data) - map_fn + predicate_fn - sink
   graph() # pushes the data through the pipeline
   ```

+ One of the big problems of the original framework is that its networks aren't
  very reusable, because most information is injected into the network by
  grabbing it from the enclosing scope. This can be mitigated by wrapping the
  network in a function and passing the various bits as arguments to the
  function. But this is not obvious (perhaps solvable with documentation) and it
  is too much work for the user.

  To make networks (`ready` instances) reusable, I propose a value store (or
  network namespace), which would be used something like this:

  ```
  # functions to be used in the network
  def gtN(N): return lambda x: x > N
  def inc(N): return lambda x: x + N

  # `get` and `set` manipulate the value store / internal namespace
  from typedflow import get, set, source

  graph = source(get.data) + get.cut(3) - get.lift - set.collect(future_sink)

  result = graph.return_(get.collect)(data=range(10), cut=gtN, lift=inc(6))
  ```

  What does this mean?

  Create a graph which retrieves `data` from the value store and feeds it into a
  filter made from {whatever is in the value store under the name `cut`, applied
  to 3}; then feed the stream through a map made out of {whatever function is in
  the value store under the name `lift`}; then feed the stream into `future_sink.sink`
  having stored `future_sink` in the value store under the name `collect`.

  These gets and sets happen at the time that the graph is run.

  How do `data`, `cut` and `lift` get into the value store? They are passed in
  as keyword args when the graph was called. (This leads to type checking and
  dispatch problems: disucced later.)

  `ready.return_` accepts a specification of what should be returned when the
  graph is executed, and returns a specialization of the graph on which it was
  called. This means that the original graph can be reused to create callables
  with different return values.

  In addition to `return_`, `ready` should support `store`, which returns a
  specialization of the graph with some values stored in the value store. (This
  is essentially equivalent to using `functools.partial`) This enables another
  form of reuse:

  ```
  my_graph = graph.return_(get.collect).store(cut=gtN, lift=inc(6))
  a = my_graph(data=range(10))
  b = my_graph(data=whatever)

  ```


+ The `get` timing problem.

  On the one hand, we need information about the type of the operands of `-`
  &co, at the time the network is constructed, in order to be able to type check
  and dispatch. On the other, most of the values retrieved by `get` won't be
  available until the network is executed.

  The only solution I can see so far, is to endow `get` with some mechanism for
  specifying type (or role) expectations. The operators would access this
  information for dispatch at network construction time, and the network would
  use it to type check when the values are set.

  TODO: need to think more about alternative syntaxes.


+ As suggested above, if reduce is implemented with `>>` then it's not obvious
  how to pass it an initial value. Possible solutions:

  1. Introduce `fold` for this purpose. (`fold` is the name for `reduce` in some
     other languages, it's shorter than `reduce`, and will cause less confusion
     and name clashes with `functools.reduce`).

     ```
     src - pipe - fold(fn, initial)
     ```

  2. Try to construct `fold` with an operator, such as `<<`

     ```
     src - pipe << initial >> fn
     ```

  (Visually this might be interpreted an pushing the initial value upstream,
  guaranteeing that `fn` always gets it as its first value.)

  There is also the issue of distinguishing between plain sinks and future
  sinks. The old `reduce` always created future sinks. If `>>` is to do double
  duty and create both, there needs to be a scheme to distinguish the two
  situations.

  Maybe `>>` creates plain sinks, and `<< initial_value >>` creates
  future-sinks. If we want to remove the restriction that future-sinks must
  always provide an initial value, then we could provide a symbol than can be
  used as the initial value, whose meaning is 'take it from the stream'.

  TODO: all this needs more careful thought

## Vague ideas

+ Can we put square brackets (`__getitem__`) to some use? How about .
  (`__getattr__`)? And even `__call__`. All three have very high precedence.
  Oooh, this could turn out to be very interesting. Except that, once again, we
  run into the problem that it won't work with plain functions, and we'll be
  wanting to use those as much as possible in the pipelines.

  Still, think about uses for stuff like

    ```
    pipeA - pipeB.option   - pipeC
    pipeA - pipeB(a, b, c) - pipeC
    pipeA - pipeB[a, b, c] - pipeC
    pipeA - pipeB[x:y, p:] - pipeC
    ```
  which would need to look a bit uglier if we need to apply it to plan
  functions:

  ```
   pipeA - pipe(fnB).option   - pipeC
   pipeA - pipe(fnB)(a, b, c) - pipeC
   pipeA - pipe(fnB)[a, b, c] - pipeC
   pipeA - pipe(fnB)[x:y, p:] - pipeC
   ```
  BTW, the .options could be chained:

    ```
    ... - pipeX.optionA.optionB - ...
    ```
+ Can `[]` or `()` operators be useful to make branches?
