[![Build Status](https://travis-ci.org/jacg/liquidata.svg?branch=master)](https://travis-ci.org/jacg/liquidata)


# Why would I want this?

If you think that the signal is drowned out by the noise in code written like
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
while the intent is clearer when it is presented like this

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
abstraction should be as easy as getting the previous version by extracting
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

then you might enjoy the tutorial.
