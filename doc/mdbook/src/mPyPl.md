# Comparison to mPyPl

[`mPyPl`](http://soshnikov.com/mPyPl/) is a project with certain similarities to
`liquidata`.

A major architectural difference is that `mPyPl` uses generators to *pull* data
through the pipeline, while `liquidata` uses coroutines to *push* the data
through the pipeline. This is because `liquidata` was designed to allow easy
bifurcation of flows into independent unsynchronized branches. (`liquidata` will
probably also support pull-pipelines in the future.) Both `mPyPl` and
`liquidata` support synchronized, named branches by sending compound objects
with named components through the flow. `mPyPl`'s and `liquidata`'s approach to
managing these names is markedly different.

Here we compare and contrast the APIs provided by the two packages.

This example appears in the [quickstart](http://soshnikov.com/mPyPl/) for `mPyPl`:

```python
import mPyPl as mp

images = (
  mp.get_files('images',ext='.jpg')
  | mp.as_field('filename')
  | mp.apply('filename','image', lambda x: imread(x))
  | mp.apply('filename','date', get_date)
  | mp.apply(['image','date'],'result',lambda x: imprint(x[0],x[1]))
  | mp.select_field('result')
  | mp.as_list)
```

Here is its translation into `liquidata`

```python
from liquidata import pipe, source, name, get, put

images = pipe(
  get_files(...) >> source,  name.filename,
  imread   * get.filename >> put.image,
  get_date * get.filename >> put.date,
  imprint  * get.image.date)
```

Observations:

+ `liquidata` highlights the high-level information about what happens in the
  pipeline: `get_files`, `imread`, `get_date`, `imprint`. In contrast, `mPyPl`
  buries it in the noise.

+ `liquidata` avoids the use of strings as symbols.

+ `mPyPl` provides a specific `get_files` utility; `liquidata` can work with any
  iterable source of files, but providing such sources is outside of the scope
  of `liquidata`'s goals.

+ `mp.as_field('filename')` is equivalent to `name.filename`

+ `mp.apply` serves three purposes:

  - mapping a function over the stream data
  - selecting arguments from the compound flow items
  - placing the result back in the compound flow items

  In contrast `liquidata` separates these concerns

   - mapping is done by default: no need to ask for it
   - `get` selects arguments
   - `put` places results

+ `mp.apply(['image', 'date'], 'result', lambda x: imprint(x[0],x[1]))`

  - creates an argument tuple containing `image` and `date`
  - uses a `lambda` to unpack the argument tuple into the call to `imprint`
  - puts the result back in the compound flow under the name `result`

  In contrast, in `imprint * get.image.date`

  - `get.image.date` creates an argument tuple
  - `*` unpacks the augment tuple into the call to `imprint`
  - The lack of `put` causes the result to continue downstream on its own: the
    other items in the compound flow are no longer needed!

+ `mp.select_field('result')` translates to `get.result` in `liquidata`. It
  extracts the interesting item from the compound flow. In the `liquidata`
  version this step is not needed, because it was done implicitly in the
  previous step: by avoiding the use of `>> put.result`, the result continued
  down the pipe on its own, rather than being placed in the compound object
  along with everything else. That is to say
  ```python
  imprint * get.image.date
  ```
  is equivalent to

  ```python
  imprint * get.image.date >> put.result,
  get.result
  ```

+ `mp.as_list` collects the results in a list. The equivalent (which would be
  written `out(into(list))`) is missing from the `liquidata` version, because
  it's the default.

+ `out(into(...))` is far more general than `mp.as_list`, as it will work with
  *any* callable that consumes iterables, such as `set`, `tuple`, `min`, `max`,
  `sum`, `sorted`, `collections.Counter`, ... including any and all that will be
  written in the future.
