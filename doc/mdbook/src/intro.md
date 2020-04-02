# Quickstart

## Guinea pig functions

In the examples that follow, we will use some small pre-defined functions, such
as:

```python
{{#include ../../../quickstart_test.py:guinea_pigs}}
```

## Function composition and iteration

Use `pipe` to create data flows. In its most basic usage

```python
{{#include ../../../quickstart_test.py:function_composition}}
```

+ `pipe` composes functions.
+ `pipe` returns a callable.
+ That callable accepts an iterable argument
+ It feeds the contents of its argument through the sequence of functions in the
  pipe.
+ It returns a list of the values that reach the end of the pipe

## Equivalence to `map`

So far, it just a concise way of mapping multiple functions over a stream of
data:

```python
{{#include ../../../quickstart_test.py:equivalence_to_multiple_maps}}
```

Note the reversal of the order in which the functions are specified (`f`-`g`-`h`
vs `h`-`g`-`f`).

## Filtering

To use a function as a filtering predicate, rather than a mapping, wrap it in braces (`{  }`):

```python
{{#include ../../../quickstart_test.py:filter}}
```

## Concatenation: `join` and `flat`

`join` is a component which accepts iterable values from downstream, and sends
the items they contain, downstream, one by one:

```python
{{#include ../../../quickstart_test.py:join}}
```

`flat(...)` is a utility for creating mapping components with an internal
`join`.

# Folds

By default, data reaching the end of the pipe is collected into a list, which is
returned once the input is exhausted. You can override this default collection
behaviour by providing a binary function to be used to fold the data together,
before returning. To indicate that the function is to be used to fold together
the data for output, wrap it in `out(...)`.

This is equivalent to `functools.reduce`:

```python
{{#include ../../../quickstart_test.py:fold}}
```

A default or initial value can be provided, just like with `functools.reduce`:

```python
{{#include ../../../quickstart_test.py:fold_with_initial}}
```

# Side-effects

Instead of returning the data reaching the end of the pipe, it is possible to
use it to perform side-effects. This is done by providing a unary side-effecting
function and wrapping it in `sink(...)`:

```python
{{#include ../../../quickstart_test.py:side_effects}}
```

In this case we're just appending the values to a list. In real life you might
print them out, write them to files, send them across a network ...

# Branches

It is possible to bifurcate the flow. Grouping some components together in
square brackets (`[...]`) creates a branch containing those components:

```python
{{#include ../../../quickstart_test.py:branch}}
```

# Named outputs

In the last example, data reaching the end of the main pipe was returned, while
the side-branch sent the data down a side-effecting sink.

It is possible to have the network return multiple values from various
end-points in the graph. In order to make it clear which output corresponds to
which branch, it's a good idea to name the outputs. This is done with
`out.<name>`:

```python
{{#include ../../../quickstart_test.py:named_outs}}
```

As soon as multiple outputs are present in a network, the function created by
`pipe` returns a namespace containing all the return values, rather than a
single return value.

In this example the two named outs (`out.side` and `out.main`) caused `pipe` to
return a namespace containing the names `side` and `main`.

# Spies

TODO

```python
{{#include ../../../quickstart_test.py:spy}}
```

# Compound flows

So far, we have been sending streams of single values down the pipes. We also
used branches (`[...]`) to bifurcate the flow.

An alternative approach to bifurcation is to send namespaces, rather than single
values, through the pipes. Each name in the namespace can be thought of as a
separate pipe.

The important contrast between these two approaches to branching is that:

- synchronization:

  + `[]`-branches are independent: filters (`{}`), `join` (and `flat`) will cause
    different numbers of items to reach the end of each branch.

  + the branches represented by namespaces are synchronized: the same number of
    items reach their ends, even if they contain filters or `join`s.

- merging:

  + namespace branches can easily be made to feed items into a single component.
    This is not really feasible with `[]`-branches.

`liquidata` provides a number of utilities for working with namespaces in the
flow: `name`, `get` and `put`.

# name

`name` can be used to create namespaces out of single values, or sequences of values:

```python
{{#include ../../../quickstart_test.py:name_single}}
```

# get

`get` plays two roles:

+ a more concise version of `operator.attrgetter`
+ a pipeline version of Python's stardard argument expansion syntax:
  `fn(*args)`.

Here it is as a drop-in replacement for `attrgetter`:

```python
{{#include ../../../quickstart_test.py:get_as_attrgetter}}
```

where `abc012` is the following sequence of namespaces

```python
{{#include ../../../quickstart_test.py:abc012}}
```

which will be used in many of the subsequent examples.

Here is `get` combined with the `*` operator, acting like Python's
argument-expanding `*`:

```python
{{#include ../../../quickstart_test.py:get_as_star}}
```

`get` picked two values out of the namespace, and `*` passed them as *separate*
arguments to `sym_add`.

It is worth emphasizing the important difference between

```python
get.a.b , f   # f((a,b))
get.a.b * f   # f( a,b )
```

# `star`

The `*` in the above example is an operator defined on `get`. When you need to
expand a tuple of arguments flowing through the pipe into a component, without
the use of `get`, you can use `star`:

```python
{{#include ../../../quickstart_test.py:star}}
```

# `put`

`put` is used to place the outputs of a component into the namespace which came
from upstream, under specified names.

```python
{{#include ../../../quickstart_test.py:put}}
```

The incoming namespaces contained the names `a` and `b` only. `put.ab` *added*
the name `ab` to the namespace, binding it to the result of `mul` being applied
to the `a` and `b` already present in the namespace.

+ `a` and `b` are 2 synchronized branches.

+ `get.a.b * mul` joins these two branches together.

+ `mul >> put.ab` creates a new synchronized branch named `ab`.

`put` can create more than one name at a time. This is appropriate when the
component returns more than one value:

```python
{{#include ../../../quickstart_test.py:multiple_put}}
```

`hilo` returns two values, `hilo >> put.hi.lo` binds them to two separate names
in the namespace.

# `on`

TODO

# Nested pipes

Pipes can be used as components inside other pipes:

```python
{{#include ../../../quickstart_test.py:nested_pipes}}
```

# Use as function



# Introduction

For now, I'll just write everything here, then, as it takes shape, we can decide
what good chapter names will be and how to divide it all up.

## What is this?

`liquidata` encourages functional compositional style.

Embedded Domain Specific Language (EDSL) for Keywords: testable, composable,
orthogonal, reusable, legible ...

inspired by the belief that it is preferable to write code like this

TODO: example of a nontrivial graph

as opposed to the equivalent

TODO: the same thing written as a physicist-style loop with no abstraction

TODO: prove, by testing, that the two are equivalent

TODO: wax lyrical about how much more legible, testable, maintainable,
debuggable etc. the dataflow version is.

## Background: Where did this come from?

Next.

HEP analysis code tends to process a bazillion events in the same way. This
tends to be written with *event loops*, which tend to be copy-pasted leading to
an accumulation of crap into an incomprehensible mess. Try to say this politely.

To stop physicists from writing pointless classes containing 2000 line methods containing some nested loops

## Design choices

+ Push rather than pull, because of divergence of streams
+ Namespace in a single stream to simulate parallel, synchronized, joinable streams.

## Concurrency

Obvious potential extension. Not needed by IC yet, so not worked on it yet. Should do.

Pitfalls:
  * Order of arrival in sinks
  * How to combine sinks found in the middle of streams if those streams are split across multiple processors

# User guide

## Fundamental concepts

`liquidata` is an Embedded Domain Specific Language (EDSL) for expressing
computations on streams of data. TODO composition of functions


Conceptually these may be connected like this

TODO: decide on a pretty graphical way of presenting these network diagrams

```
source -> pipe element 1 -> pipe element 2 -> ... -> sink
```
+ sources produce data
+ pipes transform and filter data
+ sinks consume data

Pipes are *composable* and *reusable*: a pipe can be made out of smaller pipes
joined end-to-end.

More complex data flows, including bifurcations

```
source -> pipe 1 ---> pipe X -> pipe Y -> sink Z
                \
                 pipe A -> pipe B -> pipe C -> sink D

```

and even joins

```
source -> pipe 1 ---> pipe X -> pipe Y ---> sink Z
                \                      /
                 pipe A -> pipe B ____/

```

can also me made, but we will put off discussing these until later.

TODO: note that graph, network and data flow are synonyms

TODO: note that pipe and stream are almost synonymous


+ Zero or more elements which
+ Exactly one sink, which consume

## The trivial graph: `pipe` and `out`

`pipe` is used to construct data flows: sequences (more generally, graphs) of
processing components through which data are sent.

Let's start off with a trivial example.

```python
{{#include ../../../liquidata_doc_test.py:trivial}}
```

Points to note:

+ In this example, the pipeline contains a single element, `out`, which simply
  collects all items that reach it from upstream into a list, and returns the
  list as the result of the pipeline, once the data stream is exhausted.

+ `pipe` returns a function, which we bound to the name `process`

+ We called `process` with an iterable argument.

+ `process` fed each item in its argument, through the pipeline, one by one.

+ The pipeline did nothing besides collecting the items being fed into it.

+ Therefore, `process` returned a list of all the elements in its argument.

+ This is a trivial example which does nothing beyond showing how:

  - `pipe` returns a callable which consumes an iterable,

  - `out` is used to collect streamed data into a container.

[Aside: In real life we would usually choose to push lazy sources into the
pipeline, but in the examples that follow we avoid lazy sources so that we can
verify the results more easily.]

## Aside: `arg`, a lambda alternative with lighter syntax

TODO: Actually, the symbolic functions are probably a better bet, except for
filters ...

In the examples that follow, we will frequently need to put very simple
functions into the pipelines, for illustrative purposes. Python's lambda syntax
is excessively noisy for such trivial functions, so `liquidata` provides a
utility which makes it possible to create trivial functions, using a lighter
syntax.

In brief, the following two expressions are equivalent.


```python
lambda x: x + 1
        arg + 1
```
Here is a more complete example
```python
{{#include ../../../liquidata_doc_test.py:meet_arg}}
```

Note that `arg` must be imported from `liquidata`. You may choose to bind it to
any name you like, for example `from liquidata import arg as _`.


`arg` is limited in what it can do, compared to `lambda`, but for very simple
functions, it brings less syntactic overhead. Expect to see it used liberally in
the examples that follow.

# Adding functions into the pipeline: mapping

Let's take our trivial pipeline from earlier, and place a function, `f`, before
`out`:

```python
{{#include ../../../liquidata_doc_test.py:map}}
```

[We used `arg` to define `f`. `arg` was described in the previous section.]

The function transforms every item passing through the pipe. Consequently,
putting a function in a pipe is equivalent to mapping the function over the
elements flowing through the pipe at that point.

Now let's put multiple functions into the pipe:

```python
{{#include ../../../liquidata_doc_test.py:map_many}}
```

Comparing this to the standard way of chaining mappings:

+ There is far less syntactic overhead.

+ The order in which the functions appear is reversed.

# Filtering data

Let's take the earlier example where we placed a single function in the
pipeline, and modify it in two ways:

+ Replace `f` with a predicate: a function that returns a boolean

+ Wrap it in `{   }` when placing it in the pipeline

```python
{{#include ../../../liquidata_doc_test.py:filter}}
```

Observe that the braces (`{ fn }`) indicate that the function should be treated
as a filter rather than a map.

TODO: consider providing the name `keep` (or something else that doesn't clash
with `filter`) as a more verbose version of `{ }`

# Combining filters and maps

TODO: It just works

# Filtering on keys

TODO: discuss.

TODO: Is it really worth having this, once we get `pipe(..., (key_fn, {pred}),
...)` working?

For example:

```python
{{#include ../../../liquidata_doc_test.py:filter_on_key}}
```

There are strings flowing through this pipeline. The predicate, `arg < 3`,
should not be applied to the strings themselves. It should be applied to the
length of each string: this is indicated by `: len`.

# `flat`

In all the examples we have seen so far, components which appear in the pipeline
accept items from upstream, and send items downstream.

+ In the case of mapping components, exactly one item is sent downstream for
  each incoming component.

+ In the case of filtering components, each incoming item results in either one
  or zero components being sent downstream.

+ It should be possible to have an arbitrary number of separate items sent
  downstream, for each incoming item. This is the purpose of `flat`.

```python
{{#include ../../../liquidata_doc_test.py:flat}}
```

Let's break this one down:

+ `repeat` turns an integer `n` into a string containing `n` repetitions of `n`:

  - `repeat(1) == '1'`
  - `repeat(0) == ''`
  - `repeat(3) == '333'`
  - `repeat(2) == '22'`

+ `flat` takes the iterable returned by `repeat`, and sends the contained items
  downstream, one by one.

  - for `n=1` this results in the single item `1` being sent downstream.
  - for `n=0` no items emerge
  - for `n=3` there are 3 items: `3`, `3` and `3`
  - for `n=2` there are 2 items: `2`, and `2`

+ `out` collects all of them into a list: `['1', '3', '3', '3', '2', '2']`.

+ `''.join(...)` sticks them together in a visually more appealing string: `'133322'`.


# Sinks

In contrast to all the other components appearing in the pipes we have seen so
far, `out` never sends any items downstream, because the pipe stops there: there
is no downstream. `out` belongs to the category of components which terminate
pipes by collecting all the items that reach it. These are called *sinks*.

Specifically, `out` collects all the items into a list which is then returned by
the pipeline as a whole. Let's look at some other kinds of sinks.

## Side-effecting sinks.

Rather than having the items returned, we could use them to perform some side
effect, such as printing them to standard output, writing them to a file, or
sending them across a network. In order to keep the example small and
self-contained, we'll perform a simpler side-effect: append the items to a list:

```python
{{#include ../../../liquidata_doc_test.py:side_effect_sink}}
```

+ `arg * 10` and `{arg < 45}` simply map and filter the data. Nothing new here.

+ Note that the last item in the pipe is `result.apppend`. This is the bound
  `append` method of the `result` list that was created one line earlier in the
  code. It appends its argument to that specific list.

+ If the last item is not explicitly a sink, `pipe` will implicitly convert it
  into a side-effecting sink.

  - Every item reaching this point in the flow will be passed as an argument to the component.
  - Anything the component returns will be ignored: nothing will be sent
    downstream, because it's a sink.

## Fold, reduce

So far we have seen two distinct kinds of sink:

+ Perform side-effects with the data. `pipe` *implicitly* treats the last item
  as a side-effecting action.
+ Return the stream data in a list. This must be *explicitly* requested with
  `out`.

It is possible to request `out` to do something more interesting with the data,
by giving it a binary function which it can use to fold or reduce the data.

```python
{{#include ../../../liquidata_doc_test.py:fold}}
```
+ Recall that `sym_add` is a binary function which performs a symbolic addition
  of its arguments: `sym_add(1,2) == '(1+2)'`.

+ The pipe is terminated with `out(addem)`. This means that:

  - the pipeline should *return* a value

  - that value should be produced by combining all the stream data with
    `sym_add`.

Note that this is equivalent to `functools.reduce`.

## Fold with initial value

Just like `functools.reduce`, `out` accepts an initial or default value:

```python
{{#include ../../../liquidata_doc_test.py:fold_with_initial}}
```

# Branches

All the pipes we have seen so far have been linear. `liquidata` allows us to
bifurcate the flows. One mechanism for doing this is the *branch*.

```python
{{#include ../../../liquidata_doc_test.py:branch}}
```

+ The first element in the pipe is the mapping function `f`

+ The second element in the pipe is the *branch* `[g, branch.append]`

+ `branch.append` is an implicit side-effecting sink (discussed earlier), which
  appends all the items it receives, to the list `branch`.

+ After the branch, there are two further components: `h` and `main.append`, a
  mapping function and a side-effecting sink.

+ In order to reach `branch.append` data has to flow through both `f` and `g`.

+ In order to reach `main.append` data has to flow through both `f` and `h`.

Square brackets (`[ ... ]`) are the `liquidata` syntax for creating branches.

## Multiple returning sinks and named return values

In the previous example, the network contains two sinks. They are both
side-effecting sinks. But what if we wanted the stream data to be collected and
returned, rather than used in side-effects?

Earlier we used `out` for this purpose. But now that there are two sinks ... if
we used two `out`s, which one would be returned?

In order to avoid such ambiguities, `out`s can be named:

```python
{{#include ../../../liquidata_doc_test.py:named_outs}}
```

This is a variation on the previous example: The side-effecting sinks have been
replaced with *named* `out`s.

+ Named `out`s cause the network to return a namespace.

+ The namespace contains all the names specified by the named `out`s (in this
  examlpe, `branch` and `main`), bound to the values they collected.


TODO: discuss name collisions, and multiple anonymous outs.

## Named return values and folding

Just like anonymous `out`s, named `out`s accept a folding function:

```python
{{#include ../../../liquidata_doc_test.py:named_outs_fold}}
```

# Compound flow

Branches are a convenient way of splitting the flow into independent streams.
However, if you need the branches to be synchronized, or need multiple branches
to feed into a single component, then a different branching style is more
appropriate: compound flow. Rather than propagating atomic data down separate
pipes, propagate a namespace containing multiple data down a single pipe.

```python
{{#include ../../../liquidata_doc_test.py:branch_into_namespace}}
```

+ `split` takes a single input and returns a tuple with three elements.

+ `name.a.b.c` takes a 3-tuple and returns a namespace with `a`, `b` and `c`
  bound to the tuple's items.

+ Together, `split` and `name.a.b.c` turn a stream of atomic values into a
  stream of namespaces containing three values.

+ A stream of namespaces with N values, may be thought of as N parallel pipes.

+ Thus `... split, name.a.b.c, ...`, split a single pipe into three parallel
  branches.

`name` is used to create new namespaces. There are other utilities which make it
easier to work with existing namespaces in a stream.

# `get`

At a basic level `get` is simply a less verbose version of `operator.attgetter`:

```python
{{#include ../../../liquidata_doc_test.py:get_attrgetter_equivalence}}
```

Inside pipes, it can be used to pick a single value out of a namespace for
consumption by the next element in the stream:

```python
{{#include ../../../liquidata_doc_test.py:get_single_before_map}}
```

## `get *`

`get` can also be used to pick *multiple* values from the namespace. This would
result in the following component in the pipe receiving a tuple containing those
values, as its single argument.

However, `get` also supports argument unpacking, similar to Python's stardard
`fn(*args)` syntax. This feature uses the `*` operator:


```python
{{#include ../../../liquidata_doc_test.py:get_star}}
```
Note the crucial difference between the following two

```python
pipe(..., get.a.b , f, ...)  # f((a,b))
pipe(..., get.a.b * f, ...)  # f( a,b )
```

+ In the first case

  - there is a `,` between `get.a.b` and `f`

  - `f` receives a single argument: a tuple containing two values

+ In the second case

  - there is a `*` between `get.a.b` and `f`

  -  `f` receives two separate arguments

## `star`

`get`'s `*` operator is just syntactic sugar for `star`

```python
{{#include ../../../liquidata_doc_test.py:star}}
```

TODO: describe situations in which you would use `star` because `*` is not available.

# `put`


In the last few examples, the branches represented by the incoming namespace,
are replaced with a single, atomic result. This is rarely what we want: more
often you would want to place the result in the namespace, under some name of
your choosing.

This is the job of `put`:

```python
{{#include ../../../liquidata_doc_test.py:put}}
```

+ `f` is a binary function which returns a 2-tuple of results

+ `get.a.b * f` applies `f` to two arguments: the value of `a` and `b` in the
  namespace which is flowing though the pipe.

+ `>> put.sum.product` binds the two values returned by `f` to the namespace,
  under the names `sum` and `product`.

# `on`



# Pipes inside pipes

TODO
