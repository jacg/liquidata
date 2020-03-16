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

Throughout the following examples it is assumed that `dataflow` has been imported thus

```python
import dataflow as df

```

A pipe needs a source of data at one end, and a sink at the other. These three
fundamental components are combined with `push`

```python
{{#include ../../../dataflow_test.py:simplest}}

```
