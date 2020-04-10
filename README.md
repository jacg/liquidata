[![Build Status](https://travis-ci.org/jacg/liquidata.svg?branch=master)](https://travis-ci.org/jacg/liquidata)

<!-- ANCHOR: what_is_this -->

# What is this?

`liquidata` is a Python Embedded Domain Specific Language (EDSL) which aims to encourage and facilitate

+ increasing the signal-to-noise ratio in source code

+ avoiding using strings to represent symbols in the API

+ code reuse through composition of reusable and orthogonal components

+ dataflow programming

+ function composition

+ lazy processing.

<!-- ANCHOR_END: what_is_this -->

# Why would I want this?

<!-- ANCHOR: network -->

## Dataflow networks

It can be helpful to think of your computations as flows through a network or
graph of components. For example

```
candidates
    |
quick_screen
    |
expensive_screen -------.
    |                    \
can dance ?           can sing ?
    |                     |
hop test              pitch test
    |                     |
skip test             rhythm test
    |                     |
jump test                 |
    |                     |
sum scores            sum scores
    |                     |
score above 210 ?     score above 140 ?
    |                     |
output dancers        output singers
```

The aim of `liquidata` is to allow you to express the idea laid out in the graph
above, in code that reflects the structure of the graph. A `liquidata`
implementation of the graph might look something like this:

```python
select_candidates = pipe(
    { quick_screening },
    { expensive_screening },
    [ { can_sing },
      test_pitch,
      test_rhythm,
      sum_scores.pitch.rhythm,
      { score_above(140) },
      out.singers
    ],
    { can_dance },
    test_hop,
    test_skip,
    test_jump,
    sum_scores.hop.skip.jump,
    { score_above(210) },
    out.dancers)

selected = select_candidates(candidates)

# Do something with the results
send_to_singer_committee(selected.singers)
send_to_dancer_committee(selected.dancers)
```

<!-- ANCHOR: composition_prelude -->

## Function composition

If you feel that the signal is drowned out by the noise in code written like
this

```python
for name in filenames:
    file_ = open(name):
        for line in file_:
            for word in line.split():
                print(word)
```
and that the intent is clearer in code presented like this

```python
pipe(source << filenames, open, join, str.split, join, sink(print))
```
then you might find `liquidata` interesting.

## Still with me?

That was a trivial example. Let's have a look at something a little more
involved.

If you are perfectly happy reading and writing code like this

<!-- ANCHOR_END: composition_prelude -->

```python
def keyword_frequency_loop(directories):
    counter = Counter()
    for directory in directories:
        for (path, dirs, files) in os.walk(directory):
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                for line in open(os.path.join(path, filename)):
                    for name in line.split('#', maxsplit=1)[0].split():
                        if iskeyword(name):
                            counter[name] += 1
    return counter
```

then `liquidata` is probably not for you.

But if the last example leaves you wanting to extract the core meaning from the
noise, and you feel that this

```python
all_files         = os.walk, JOIN, NAME.path.dirs.files
pick_python_files = GET.files * (JOIN, { use(str.endswith, '.py') }) >> PUT.filename
file_contents     = GET.path.filename * os.path.join, open, JOIN
ignore_comments   = use(str.split, '#', maxsplit=1), GET[0]
find_keywords     = str.split, JOIN, { iskeyword }

keyword_frequency_pipe = pipe(
    all_files,
    pick_python_files,
    file_contents,
    ignore_comments,
    find_keywords,
    OUT(INTO(Counter)))
```
is a step in the right direction, and if you feel that abstraction should be as
easy as getting the above version by extracting subsequences from this prototype

```python
keyword_frequency_pipe = pipe(
    os.walk, JOIN,
    NAME.path.dirs.files,
    GET.files * (JOIN, { use(str.endswith, '.py') }) >> PUT.filename,
    GET.path.filename * os.path.join,
    open, JOIN,
    use(str.split, '#', maxsplit=1),
    GET[0],
    str.split, JOIN,
    { iskeyword },
    OUT(INTO(Counter)))
```

then you might want to peruse the [documentation](https://jacg.github.io/liquidata).

# Installation

<!-- ANCHOR: installation -->

Currently there are two options:

1. Pip: `pip install liquidata`.

2. Just grab the source. For now, the implementation lives in a single,
   dependency-free
   [file](https://github.com/jacg/liquidata/raw/master/liquidata.py).

<!-- ANCHOR_END: installation -->
