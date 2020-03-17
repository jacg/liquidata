# Introduction

For now, I'll just write everything here, then, as it takes shape, we can decide
what good chapter names will be and how to divide it all up.

## What is this?

`dataflow` encourages functional compositional style.

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

# Manual

## Fundamental concepts

`dataflow` is an Embedded Domain Specific Language (EDSL) for expressing
computations on streams of data, built out of three fundamental kinds of
component

+ sources
+ pipes
+ sinks

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

## The simplest graph: `push` and `sink`

Throughout the examples that follow, it is assumed that `dataflow` has been
imported thus (TODO: when implement executable examples, these imports might
have to be made explicit in each example)

```python
import dataflow as df
```

The `push` function is used to connect sources of data to pipes which can
accept, process and consume the data. In its simplest form it looks like this:

```python
df.push(source=the_source, pipe=the_pipe)
```

+ The source can be any Python iterable.
+ Pipes can be made using utilities provided by `dataflow`. [Pipes are
  implemented as coroutines, but most users can safely ignore this detail.]

[Aside: In real life we would usually choose to push lazy sources into the
pipeline, but in the examples that follow we avoid lazy sources so that we can
verify the results more easily.]

The simplest possible pipeline has the source directly connected to a single
sink. This is not particularly useful: it merely serves the purpose of showing
how the basic components fit together.

```python
{{#include ../../../dataflow_test.py:simplest}}
```

Points to note:

+ In this example, the source is connected directly to the sink.

  - There are no pipeline elements between the source and sink. This is unusual,
    but perfectly ok, because ...

  - **Sinks have exactly the same interface as pipes at the upstream end**.

+ `sink` turns a plain Python function into a sink. The function should accept
  one argument, and not return anything.

  - TODO: What happens if it *does* return something?

  - The most obvious sinks perform some side-effect using the data they receive,
    such as writing it out to persistent storage, or, as in the example above,
    collecting them into a list that was created earlier.

  - Rather than producing side-effects, sinks can produce return values for
    `push`. TODO: refer to `push(result = )` and future-sinks later on in the
    manual.

+ This is a trivial example which does nothing beyond showing how the
  fundamental components fit together.

It is worth repeating that **sinks have exactly the same interface as pipes at
the upstream end**.

+ Sinks consume data: no data flow out of the downstream end of a sink.

+ Pipes transform (or filter) data: data do flow out of the downstream end of a
  pipe.

+ The data sent downstream out of a pipe have to end up somewhere: they have to
  be collected by a sink!

+ Consequently, an *uncapped* pipe (one not connected to a sink) cannot have any
  data `push`ed into it.

## Creating and connecting pipeline components: `map` and `pipe`

The most convenient way to create pipeline components, is to use utilities
provided by `dataflow`. `df.map` is probably the most obvious one of these. Just
like `df.sink` makes sinks out of plain functions, so `df.map` makes pipeline
components out of plain functions.

`df.pipe` is used to chain together a number of pipeline components.

```python
{{#include ../../../dataflow_test.py:map}}
```

Using `df.pipe` explicitly is usually not necessary, as most utilities which
accept pipes, know how to create them implicitly out of a tuple of pipe
components. TODO: once mmkekic's implicit-pipe-in-push PR has been merged,
demonstrate this with an example right here.

TODO: refer to the `args` etc. features of map which should be discussed later on.

## `filter`

`df.filter` is the `dataflow` equivalent of Python's built-in `filter`, used to
discard data according to some criterion.

```python
{{#include ../../../dataflow_test.py:filter}}
```

## Sinks without side-effects: `push(result = ...)`

The sinks we have seen so far, have all worked by side-effect: before pushing
some data through a pipeline, we created a list along with a sink which pushes
data into that list. In some situations, particularly when the sink writes data
to a file, side-effects are fine. But eschewing side-effects TODO bla bla wax
lyrical.

Consider that

1. The sink must be placed at the end of a pipe.

2. `df.push` must be used to push data through the pipe.

3. `df.push` must stop pushing any more data through the pipe.

4. Only *then* will the sink have enough information to produce the final
   result.

How can you retrieve the value returned by the sink, if the sink is wrapped
inside a pipe inside a call to `df.push`? The solution is to create, alongside
the sink itself, another object which will allow you to access the final result,
once it becomes available.

For this purpose `dataflow` uses the `Future` found in Python's standard
`asyncio` module, but this is an implementation detail which most users can
forget, because `dataflow` provides a higher-level interface for retrieving sink
results via the value returned by `df.push`.

```python
{{#include ../../../dataflow_test.py:push-result-single}}
```

### Returning more than one value using `push(result = ...)`

Later we will see that a single network may contain multiple sinks, at which
point it becomes interesting to instruct `pipe` to return the values
created by an arbitrary subset of these sinks.

Consequently, `push(result = ...)` can accept

+ a single future
+ a tuple of futures
+ a dictionary of futures

In each case, `push` will return a similarly shaped object containing the
values extracted from the futures:

```python
push(..., result =        a.future             ) # ->        <value a>
push(..., result =     (  a.future,   b.future)) # ->     (  <value a>,     <value b>)
push(..., result = dict(a=a.future, b=b.future)) # -> dict(a=<value a>, b = <value b>)
```

## DIY side-effect-free sinks: `reduce`

`map`, `filter` and `reduce` (sometimes known under different names, such as
`transform`, `accumulate` and `fold`) are three of the most common higher-order
loop-abstraction functions, ubiquitous in functional programming, and finding
their way into most programming languages these days.

They fall into two distinct categories. All three consume iterables, but

+ `map` and `filter` return iterables
+ `reduce` returns a single[*] value

<!-- [Aside: This is not strictly true. `reduce` is the most fundamental -->
<!-- loop-abstraction function, in the sense that, in theory, **any** loop (including -->
<!-- those which produce non-scalar results) can be expressed in terms of `reduce`; -->
<!-- in practice it is often more trouble than it is worth!] -->

This dichotomy hints at the different roles their equivalents play in `dataflow`:

+ `df.map` and `df.filter` make pipe components
+ `df.reduce` makes sinks.

 `df.reduce` provides a high-level means of creating future-sinks such as
 `df.count` (which we saw earlier) or `df.sum` (which sums all the values
 receives). Here is how you would use `df.reduce` to make the latter

 TODO: `df.sum` is not implemented yet, is it?

```python
{{#include ../../../dataflow_test.py:reduce}}
```

## `spy`: side-effects in the middle of a pipe

`spy` is used to create pipe components which do not modify the data flowing
through the pipe in any way: inserting a spy into a pipe should not affect what
flows downstream. Instead, they can perform arbitrary side-effects on the data.
An obvious use would be to insert `spy(print)` into a pipe in order to observe
what is flowing through the pipe at that point.

```python
{{#include ../../../dataflow_test.py:spy}}
```

If the data flowing through the pipe are mutable, the spy could mutate them, and
thus modify what gets sent downstream, but this is *not* the intended use of
spies: don't do that!

## Splitting streams: `fork` and `branch`

`dataflow` provides two utilities for bifurcating a data stream: that is to say,
sending the same data into more than one pipeline: `fork` and `branch`.

They are equivalent in power but some ideas may be more naturally expressed in
terms of one or the other.

```python
{{#include ../../../dataflow_test.py:fork_and_branch}}
```
Visually, the `fork` version suggests a layout like this
```
              B -> C
             /
the_data -> A
             \
              D -> E
```
while the `branch` version looks more like this
```
                   B -> C
                  /
the_data -> A -> o -> D -> E
```
but their topologies, and hence their behaviours, are identical.

The main differences are:

+ `branch` accepts exactly one pipe; `fork` accepts an arbitrary number

+ `branch` creates components which can be inserted in the middle of a pipeline;
  `fork` creates components which can only be placed at the end of a pipeline
  ...
+ ... in other words, `branch` creates uncapped pipes; `fork` creates capped
  pipes.
## TODO Tests not used here so far

+ `test_fork`
