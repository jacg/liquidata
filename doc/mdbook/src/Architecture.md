# Why do we have the current architecture?

The current implementation uses coroutines to push data through the pipeline.

This was motivated by the context in which the ancestor of `liquidata` was written, where a single input stream was required be split into multiple independent output streams fed into separate sinks.

Let's take a step back and ask some questions about this choice: Do we need to push? Do we need coroutines? Why? When? What are the consequences? What alternatives are there?

# Function composition

Let's consider a very simple pipeline, consisting of a linear sequence of maps:

```python
pipe(f, g, h)
```
This could be implemented using any of

+ coroutines
+ generators
+ asyncio
+ function composition

Function composition is the simplest, so why bother with the others?

# Changing stream length

Let's throw in a filter or a join:

```python
pipe(f, { p }, g, h)
pipe(f, join, g, h)
```
Function composition no longer cuts the mustard, because there is no longer a 1-to-1 correspendence between items in the input and output streams: something is needed to shrink or expand the stream.

# Stream bifurcation

A different complication, branches:

```python
pipe(f, [x, y], g, h)
```
It's difficult to see how function composition and generators could deal with this.

# Joining streams

That last pipe describes a graph that looks something like this:
```
             x -- y
           /
source -- f
           \
             g -- h
```

How about

```
sourceA -- a
            \
             g --- h
            /
sourceB -- b
```
Generators can deal with this easily:

```python
map(h, map(g, map(a, sourceA)
              map(b, sourceB)))
```
but it's not obvious how this would work for function composition or coroutines.

## `liquidata` syntax for multiple sources

What would the `liquidata` syntax for this look like?

Ideally we'd have another kind of bracket (we've exhausted the possibilities
that Python offers: `()`, `[]`, `{}`). Let's imagine that `<>` are valid
syntactic brackets, then we could have:

```
pipe(b, <sourceA, a>, g, h)  # join two sources
pipe(b, [a, out.A],   g, h)  # branch out into two sinks
```

Working with syntax available in Python, how about:

```python
pipe(b, source(sourceA, a), g, h)
```

Recall that the following are already synonymous in `liquidata`

```python
pipe(f)(data)
pipe(source << data, f)
pipe(data >> source, f)
pipe(source(data), f)
```
so the following could work

```python
pipe(source << sourceB, b, (source << sourceA , a), g, h)
```

`liquidata` used to have a input-variable syntax (called slots) in its earlier
prototype. If something like it were resurrected, we could write something along
the lines of

```python
fn = pipe(source << slot.B, b, (source << slot.A, a), g, h)
fn(A=sourceA, B=sourceB)
```

## Synchronization

In `liquidata` `[]`-branches are called *independent*, because there is
absolutely no synchronization between them (in contrast with named branches
which are based on namespaces flowing through the pipe and managed with `name`,
`get` and `put`). Once the stream has split, the branches can change the length
of the stream without the others knowing or caring about it.

We would need to think about the synchronization consequences for multiple
independent input streams. I guess that the answer is: it's up to the user to
make sure something sensible happens. Essentially, the user has the same
freedoms and responsibilities as when joining multiple sources in
classically-written generator networks:

```python
map(h, map(g, map(<filter or join>, sourceA)
              map(b,                sourceB)))
```


# `close_all`

Consider the following in current `liquidata`
```python
pipe(source << itertools.count(), take(3))
pipe(source << itertools.count(), take(3, close_all=True))
```

Because of the pull-architecture, the first never returns. In a pull
architecture the issue doesn't arise.

# So what?

I would like to remove the universal reliance on coroutines, with two main goals

+ Enabling things that were impossible before.

+ Simplifying portions of the code which don't need coroutines.
