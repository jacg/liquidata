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

If you feel that the signal is drowned out by the noise in code written like
this

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

and that the intent is clearer in code presented like this

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

then you might find `liquidata` interesting. Furthermore, if you think that
abstraction should be as easy as getting the above version by extracting
subsequences from this prototype

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
