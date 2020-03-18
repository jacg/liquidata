# Thoughts on implementation in terms of types and operators

+ Introduce 3 types: source, pipe and sink.

+ use `-` as the basic combination operator implementing the following
  operation matrix (left = left operand, top = right operand, X =
  TypeError)

  |      -  |  src  |   pipe  |  sink  |  fn  |
  |---------|:-----:|:-------:|:------:|:----:|
  | src     |   X   |   src   |   [*]  |  src |
  | pipe    |   X   |   pipe  |  sink  |  pipe|
  | sink    |   X   |    X    |    X   |   X  |
  | fn      |   X   |   pipe  |  sink  |  [+] |

  Need to be careful about not rejecting arbitrary callables in places
  where functions are acceptable!

[*] The obvious choice is to make this run the pipeline. But maybe it
    should return a callable, which accepts a return-value-spec à la
    `push(result = ...)`

[+] We have no control over this: it will be a TypeError whether we like
    it or not. See discussion lower down[X]

+ When `-` receives a function, it should turn it into a map pipe
  component.

+ Filter can be implemented with `+`, which will probably have to give
  TypeError if it doesn't get a function on the RHS.

+ fork can be implemented with `|` or `&`: they have lower precedence than `-`
  and `+`, so you could write:

    ```
    src - pipe A - pipe B ( pipe C1 - sink C2
                          | sink D1
                          | pipe E1 - pipe E2 - sink E3 )
    ```

  The trouble is, that, if `pipe C1` and `sink C2` are functions, the -
  between them will give `TypeError`[X].

+ branch could be `/`. It's higher precedence than `+` and `-`, so you could
  write:

    ```
    src - pipe A - pipe B / sink X - pipe C - sink Y
    ```

  `/` should only accept sinks and functions on the RHS. If it gets a function,
  it turns it into a sink.

  If you want more than one component in your branch, bracket them
  together:

    ```
    src - pipe A - pipe B / (pipe F - sink G) - pipe C - sink Y
    ```

  but, if `pipe F` and `sink G` are just functions, then we run into the
  same problem as we did with `fork`[X].

+ Don't really need spy any more, as its now spelt `/ spy_fn`. But we have the
  `//` operator available, with the same precedence as `/`. Maybe it can be
  useful for distinguishing spies from future spies?

+ Could argue that fork is no longer necessary, because the example I
  gave above

    ```
    src - pipe A - pipe B ( pipe C1 - sink C2
                          | sink D1
                          | pipe E1 - pipe E2 - sink E3 )
    ```

  can be written with branch as

    ```
    src - pipe A - pipe B / (pipe C1 - sink C2)
                          /  sink D1
                          / (pipe E1 - pipe E2 - sink E3)
    ```
+ Consider these two examples
     ```
     pipe - fn-I-want-to-use-in-map  # should return a pipe
     pipe - fn_I-want-to-use-as-sink # should return a sink
     ```

  maybe we can use `>>` instead of `-` to indicate that we want a sink?

+ ... in which case, maybe `-` should only be used to connect pipes, while `>>`
  should be used to connect different types:

      ```
      src  >> pipe  -> src
      pipe >> sink  -> sink
      src  >> sink  -> [*] in the table right at the top
      ```
+ One thing that's annoying with the old dataflow as used in IC, is that the
  pipelines' components need to be defined in the same scope just before the
  pipeline, which can then only be used once. It would be good to find a way of
  making the pipeline more reusable by allowing the injection of such
  components.

+ What replaces pipe(result = ...) ? See [*] near the top.

+ Consider `__call__` and `__getitem__` for the last two points.

[X] How to deal with the (fn - fn) TypeError? Somehow we must dispatch
    the operator overload lookup into our type system. I haven't come up
    with anything cleaner than prepending such chains with some symbol
    of ours, eg:

    ```
    pipe - fn - fn
    ```

    where `pipe` could be our pipe type itself, with a metaclass which
    implements the operator. Or, an instance of a plain type which
    implements the operator.

    I'd like to find a syntactically cheaper solution.

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
