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
```
