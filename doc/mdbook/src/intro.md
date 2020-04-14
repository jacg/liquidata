{{#include ../../../README.md:what_is_this}}


# Why would I want this?

{{#include ../../../README.md:network}}

{{#include ../../../README.md:composition_prelude}}

```python
{{#include ../../../tutorial_test.py:pure_python_full}}
```
then `liquidata` is probably not for you.

But if the last example leaves you wanting to extract the core meaning from the
noise, and you feel that this

```python
{{#include ../../../tutorial_test.py:liquidata_abstracted_full}}
```

is a step in the right direction, and if you feel that abstraction should be as
easy as getting the above version by extracting subsequences from this prototype

```python
{{#include ../../../tutorial_test.py:liquidata_full}}
```

then you might want to read on.

## Running these samples

+ `select_candidates` is an outline of the solution, which omits details. As
  such, it is not executable.

+ `keyword_frequency_loop` and both versions of `keyword_frequency_pipe` are
  both complete executable examples.

To run `keyword_frequency_loop`, you will need these imports:

```python
{{#include ../../../tutorial_test.py:common_imports}}
```

To run (either version of) `keyword_frequency_pipe` you will additionally need
to [get `liquidata`](./installation.md), and import thus:


```python
{{#include ../../../tutorial_test.py:liquidata_imports}}
```

(The liquidata components were uppercased in order to highlight them in the
example.)
