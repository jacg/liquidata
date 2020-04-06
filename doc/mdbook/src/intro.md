{{#include ../../../README.md:what_is_this}}


# Why would I want this?

If you think that the signal is drowned out by the noise in code written like
this

```python
{{#include ../../../tutorial_test.py:pure_python_full}}
```
while the intent is clearer when it is presented like this

```python
{{#include ../../../tutorial_test.py:liquidata_abstracted_full}}
```

then you might find `liquidata` interesting. Furthermore, if you think that
abstraction should be as easy as getting the previous version by extracting
subsequences from this prototype

```python
{{#include ../../../tutorial_test.py:liquidata_full}}
```

then you might enjoy the [tutorial](https://jacg.github.io/liquidata/Tutorial.html).

## Running these samples

If you want to run the first (plain Python) version, you will need these
imports:

```python
{{#include ../../../tutorial_test.py:common_imports}}
```

To run the latter two versions you will additionally need to [get
`liquidata`](./installation.md), and import thus:


```python
{{#include ../../../tutorial_test.py:liquidata_imports}}
```

(The liquidata components were uppercased in order to highlight them in the
example.)
