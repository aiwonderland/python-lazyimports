# lazyimports

A backport of Python 3.15's `lazy import` statement for older Python versions.

On Python 3.15+, you can write:

```python
lazy import numpy
lazy from os.path import join
```

This package provides the same deferred-import behaviour on every
supported Python version (3.6 through 3.15) via a small, focused API.

## Why?

Deferring heavy imports until they are actually needed can noticeably
speed up module load times and reduce memory usage — useful for CLIs,
plugins, and any code path that imports optional dependencies.

## Installation

```bash
pip install python-lazyimports
```

## Usage

### Lazy `import`

```python
from lazyimports import lazy_import

np = lazy_import("numpy")          # not imported yet
pd = lazy_import("pandas")         # not imported yet

# ``numpy`` is loaded on first attribute access:
arr = np.array([1, 2, 3])
```

### Lazy `from X import Y`

```python
from lazyimports import lazy_from

join, basename = lazy_from("os.path", "join", "basename")
result = join("a", "b")            # os.path is imported here
```

### Grouping with `lazy()`

```python
from lazyimports import lazy, lazy_import

with lazy():
    np = lazy_import("numpy")
    pd = lazy_import("pandas")
    tf = lazy_import("tensorflow")
# None of the modules are imported until first use.
```

### Inspecting and forcing load

```python
from lazyimports import is_lazy, force_load

proxy = lazy_import("json")
assert is_lazy(proxy)
assert not is_lazy(json)           # False for already-imported modules

real = force_load(proxy)           # resolve now and return the real module
```

## API

See the [main documentation](docs/documentation.md)

## Python 3.15+ native syntax

When you are running on Python 3.15+, you may prefer the native
syntax. The package's own API still works identically, so you can use
either:

```python
# Native (Python 3.15+ only):
lazy import numpy

# Cross-version equivalent via this package:
from lazyimports import lazy_import
numpy = lazy_import("numpy")
```

## Compatibility

- Python 3.6 through 3.15
- No third-party dependencies — uses only the standard library
  (`contextlib`, `importlib`, `sys`, `types`)

## Running the tests

```bash
python -m unittest test_lazyimports -v
```

## Retired

This project will reach its end-of-life around October 1, 2031 — the official EOL date of Python 3.15 — and the exact timeline could be slightly delayed.
We plan to ship the final stable release in November 2031. After this release, all support will **cease** and the repository will be **officially archived**,
as this library is developed solely to bring lazy import compatibility to Python 3.15 and older versions.


## License

MIT
