{{#include ../../../README.md:what_is_this}}


# Why would I want this?

If you feel that the signal is drowned out by the noise in code written like
this

```python
{{#include ../../../tutorial_test.py:pure_python_full}}
```
and that the intent is clearer in code presented like this

```python
{{#include ../../../tutorial_test.py:liquidata_abstracted_full}}
```

then you might find `liquidata` interesting. Furthermore, if you think that
abstraction should be as easy as getting the above version by extracting
subsequences from this prototype

```python
{{#include ../../../tutorial_test.py:liquidata_full}}
```

then you might want to read on.

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
