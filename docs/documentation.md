# Documentation

`python-lazyimports` is a small, dependency-free backport of
Python 3.15's `lazy import` statement for older Python versions.
This document is the **detailed reference** — for a quick overview,
see [`README.md`](../README.md); for contribution rules, see
[`CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## Table of contents

1. [Motivation](#motivation)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [API reference](#api-reference)
5. [How it works](#how-it-works)
6. [Native `lazy import` in Python 3.15+](#native-lazy-import-in-python-315)
7. [Advanced patterns](#advanced-patterns)
8. [Limitations and gotchas](#limitations-and-gotchas)
9. [Performance notes](#performance-notes)
10. [Compatibility](#compatibility)
11. [Stability](#stability)

---

## Motivation

Heavy imports (NumPy, TensorFlow, pandas, large SDKs, …) are a
common source of slow application startup. Many modules declare a
top-level `import numpy as np` even though the symbols are only used
in a handful of code paths.

Python 3.15 introduces a `lazy import` statement so that the import
is deferred until first use. This package provides an equivalent
behaviour for every supported Python version (3.6 through 3.15)
through a tiny, focused API.

The goals of the design are:

- **Zero runtime dependencies.** Only the standard library is used,
  so installing `python-lazyimports` does not pull anything else in.
- **Drop-in for `import` statements.** Use `lazy_import("foo")` in
  place of `import foo` and the rest of the code is unchanged.
- **Transparent forwarding.** Once a module is loaded, attribute
  access, `setattr`, `delattr`, `dir()`, `repr()`, `isinstance`
  checks, `hash()`, and `bool()` all behave like the real module.
- **No magic.** No `sys.meta_path` hooks, no AST rewriting, no
  bytecode patching — just a single `types.ModuleType` subclass.

---

## Installation

```bash
pip install python-lazyimports
```

Or, for local development:

```bash
git clone https://github.com/aiwonderland/python-lazyimports
cd python-lazyimports
python -m pip install -e .
```

There are no required or optional runtime dependencies.

---

## Quick start

```python
from lazyimports import lazy_import, lazy_from, is_lazy, force_load

# Deferred `import numpy as np`:
np = lazy_import("numpy")
print(is_lazy(np))          # True
print(repr(np))             # <lazy module 'numpy' [not loaded]>

# Access triggers the real import:
arr = np.array([1, 2, 3])   # numpy is imported here

# Deferred `from os.path import join, basename`:
join, basename = lazy_from("os.path", "join", "basename")
join("a", "b")              # os.path is imported here

# Force resolution without using an attribute:
real_numpy = force_load(np) # returns the real `numpy` module
```

---

## API reference

The package is small on purpose. Every public symbol is listed below.

### `lazy_import(name, package=None)`

Return a `LazyModule` proxy for the dotted module name `name`. The
real import is deferred until any attribute of the proxy is accessed.

| Parameter | Type | Description |
| --- | --- | --- |
| `name` | `str` | Dotted module name, e.g. `"os.path"`. For relative imports, use a leading dot (e.g. `".utils"`) together with `package`. |
| `package` | `str \| None` | Anchor package used to resolve relative imports. Defaults to `None` (absolute import). |

**Returns:** `LazyModule` proxy.

**Raises:** `ImportError` (only when an attribute is accessed on the
proxy and the target module cannot be imported). Constructing the
proxy itself never raises.

**Examples**

```python
# Absolute
numpy = lazy_import("numpy")

# Relative: equivalent to ``from .utils import utils`` inside a
# package whose name is `my_pkg`.
utils = lazy_import(".utils", package="my_pkg")
```

### `lazy_from(module, *names)`

Lazily import specific names from a module. The underlying module
is loaded only when one of the returned wrappers is **called** or
**used in any way** (attribute access, repr, etc.).

| Parameter | Type | Description |
| --- | --- | --- |
| `module` | `str \| LazyModule` | Module name or an existing proxy. |
| `*names` | `str` | Zero or more attribute names to import. |

**Returns:**

- `LazyModule` if `names` is empty (the proxy is returned as-is).
- A `tuple[_LazyAttr, ...]` otherwise. Each element behaves like
  the imported object but defers resolution until use.

**Examples**

```python
join, basename = lazy_from("os.path", "join", "basename")
join("a", "b")                          # os.path is imported here

getcwd = lazy_from("os", "getcwd")[0]
print(getcwd.__name__)                  # 'getcwd', no os import yet
print(getcwd())                          # os is imported here
```

### `is_lazy(obj)`

Return `True` if `obj` is a `LazyModule` proxy, `False` otherwise.
This is the canonical way to ask "is this a lazy import?".

### `force_load(obj)`

Resolve `obj` if it is a `LazyModule` and return the real module.
If `obj` is not a `LazyModule`, it is returned unchanged. Useful
when a downstream API requires the real module object.

### `lazy()`

A no-op `contextlib.contextmanager` that yields `None`. It exists
purely for visual grouping:

```python
with lazy():
    np = lazy_import("numpy")
    pd = lazy_import("pandas")
# Both modules are still unimported.
```

The manager has no side effects; `lazy_import()` works identically
inside or outside the block.

### `LazyModule`

A `types.ModuleType` subclass returned by `lazy_import()`. Instances
support all of the standard module dunders; everything not handled
by `ModuleType` itself is forwarded to the real module on demand.

| Attribute / method | Behaviour |
| --- | --- |
| `__getattr__` | Imports the real module on first call, then forwards. Internal `_lazy_*` names always raise `AttributeError` to avoid recursion. |
| `__setattr__` | Internal `_lazy_*` writes use `object.__setattr__`; everything else is forwarded to the real module. |
| `__delattr__` | Same dispatch as `__setattr__`. |
| `__dir__` | Returns `dir(real_module)` after load; before load, returns a sorted list of `__slots__` plus the standard module attributes. |
| `__repr__` | `"<lazy module 'name' [not loaded]>"` before load; `repr(real_module)` after. |
| `__bool__` | Always `True`. Modules are not used for truthiness, and a proxy should never be `False` before loading. |
| `__hash__` | `hash(target_name)` — proxies for the same module hash equally and can be used as dict keys. |
| `_target()` | Return the fully-qualified module name. |
| `_resolve()` | Return the real module, importing it on first call. |

You should rarely need to instantiate `LazyModule` directly — use
`lazy_import()` instead.

### Constants

| Name | Type | Value |
| --- | --- | --- |
| `__version__` | `str` | Package version. |
| `NATIVE_LAZY_IMPORT` | `bool` | `True` if the interpreter provides the native `lazy import` syntax (Python 3.15+). |
| `SUPPORT_LAZY_IMPORT` | `bool` | Always `True` — this package provides its own implementation. |

---

## How it works

`LazyModule` is a `types.ModuleType` subclass that stores two extra
attributes in `__slots__`:

- `_lazy_target` — the fully-qualified module name to import.
- `_lazy_real` — `None` before the first attribute access; the real
  module afterwards.

`__getattr__` is the heart of the proxy. It is only called for
attributes Python cannot find on the instance or its class, so
existing module attributes (`__name__`, `__doc__`, etc.) keep
working. For everything else, `__getattr__` calls `_resolve()`:

```python
def _resolve(self):
    real = object.__getattribute__(self, "_lazy_real")
    if real is None:
        real = importlib.import_module(self._target())
        object.__setattr__(self, "_lazy_real", real)
    return real
```

`__setattr__`, `__delattr__`, `__dir__`, and `__repr__` use the same
two-state pattern: before load, they either fail closed (`__setattr__`
loads first), or return a synthetic answer (`__dir__`, `__repr__`);
after load, they forward to the real module.

Because Python's import system caches modules in `sys.modules`, two
proxies for the same name always resolve to the same real module
object — there is no duplication of state.

---

## Native `lazy import` in Python 3.15+

Python 3.15 introduces the native syntax:

```python
lazy import numpy
lazy from os.path import join
```

This package's API is a fully compatible fallback for older Python
versions and is **not** a wrapper around the native statement. You
can mix and match:

- Use `lazy import` directly on Python 3.15+.
- Use `lazy_import("foo")` everywhere — it works on 3.6 through
  3.15 with identical semantics.
- Detect the native availability at runtime via
  `NATIVE_LAZY_IMPORT`.

The two are observationally equivalent for the cases this package
supports. The native statement may gain additional optimisations
(e.g. lazy loading of submodules) in future Python releases; if
that happens, those optimisations will not be available through this
package, but the public behaviour is unchanged.

---

## Advanced patterns

### Deferring heavy imports in a CLI

```python
from lazyimports import lazy_import

def main(argv):
    if "--report" in argv:
        # Only loaded when the flag is actually used.
        pandas = lazy_import("pandas")
        df = pandas.read_csv("data.csv")
        print(df.describe())
```

### Wrapping optional dependencies

```python
from lazyimports import lazy_import, force_load

try:
    yaml = force_load(lazy_import("yaml"))
except ImportError:
    yaml = None

def load_config(path):
    if yaml is None:
        return json.loads(path.read_text())
    return yaml.safe_load(path.read_text())
```

### Grouping related imports

```python
from lazyimports import lazy, lazy_import

with lazy():
    np = lazy_import("numpy")
    pd = lazy_import("pandas")
    tf = lazy_import("tensorflow")
# All three modules are still unloaded.
```

### Equality and hashing

`LazyModule.__hash__` is based on the target name, so:

```python
a = lazy_import("os")
b = lazy_import("os")
assert hash(a) == hash(b)         # same target -> same hash
d = {a: "first", b: "second"}
assert d[a] == "first"            # equivalent keys share entries
```

Equality (`==`) is the default object identity — two proxies for
the same module are still distinct objects. This is intentional and
matches the behaviour of `types.ModuleType`.

---

## Limitations and gotchas

- **Static analysis.** Tools like `pyflakes`, `mypy --strict`, or
  IDE auto-import cannot see that `lazy_import("foo").bar` will
  eventually expose `bar`. This is an inherent limitation of
  dynamic attribute access and applies equally to `importlib`.
- **`pickle`.** Pickling a proxy requires the real module to be
  loaded first (call `force_load()` on it). The proxy itself is
  not picklable.
- **`isinstance` against `ModuleType`.** A proxy *is* a
  `types.ModuleType` subclass and will pass
  `isinstance(proxy, types.ModuleType)`, but it is not the *real*
  module until resolved. Code that performs `isinstance(x, real)`
  against an externally obtained `real` module may need
  `force_load()` first.
- **`sys.modules` does not contain the proxy.** The proxy is a
  local name only; the real module lives under its canonical key
  in `sys.modules` once loaded. Code that introspects `sys.modules`
  will not see the proxy.
- **Wildcard imports.** `from lazyproxy import *` works because
  `__getattr__` resolves the real module on demand, but only after
  the proxy has been loaded. Until then, `from lazyproxy import *`
  raises `ImportError: cannot import name`.
- **Thread safety.** Two threads racing on first attribute access
  may both call `importlib.import_module`; the second call returns
  the cached module from `sys.modules`. The proxy state is set
  twice but ends up pointing at the same module.

---

## Performance notes

- **Proxy construction is cheap.** Creating a `LazyModule` performs
  no I/O — it just stores the name and sets `_lazy_real = None`.
- **First access pays the import cost.** There is no saving on the
  first attribute access; the saving is that you can avoid the
  cost entirely on code paths that do not use the import.
- **Subsequent access is a dict lookup.** Once loaded, every
  attribute access is a single `getattr` on the real module — the
  proxy adds one extra Python-level method call but no measurable
  overhead.
- **Memory.** Each proxy is a tiny `ModuleType` with two extra
  slots; the cost is negligible compared to the modules themselves.

---

## Compatibility

- **Python:** 3.6 through 3.15. The package uses only
  `contextlib`, `importlib`, `sys`, and `types` — all stable since
  Python 3.0.
- **Dependencies:** none at runtime.
- **Optional:** `pytest` is convenient for running tests but not
  required; the standard library `unittest` is fully sufficient.

---

## Stability

The following are part of the **public API** and will not change
without a deprecation cycle:

- `lazy_import`, `lazy_from`, `is_lazy`, `force_load`, `lazy`,
  `LazyModule`, `__version__`, `NATIVE_LAZY_IMPORT`,
  `SUPPORT_LAZY_IMPORT`.

Anything prefixed with `_` (e.g. `_LazyAttr`, `_target`,
`_resolve`) is internal and may change in any release.

Happy lazy importing! b（￣▽￣）d
