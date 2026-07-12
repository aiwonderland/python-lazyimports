# Author: Evan Yang (aiwonderland) 2026
# License: MIT
# Copyright (c) 2026–2032 Evan Yang (aiwonderland)

"""The core api of `lazyimports` module.

This module provides a backport of Python 3.15's `lazy import`
statement for older Python versions. On Python 3.15+, the native
syntax may be used directly; this module's API works identically on
all supported Python versions (3.x through 3.15).
"""

# Use python 3.15's new feature :)
__lazy_modules__ = [
    "sys",
    "contextlib",
]

import contextlib
import importlib
import sys
import types


__all__ = [
    "NATIVE_LAZY_IMPORT",
    "SUPPORT_LAZY_IMPORT",
    "LazyModule",
    "lazy_import",
    "lazy_from",
    "is_lazy",
    "force_load",
    "lazy",
]


# Native `lazy import` statement is available on Python 3.15+.
NATIVE_LAZY_IMPORT = sys.version_info >= (3, 15)
# This package provides its own implementation, so lazy imports are
# always supported regardless of interpreter version.
SUPPORT_LAZY_IMPORT = True


class LazyModule(types.ModuleType):
    """Proxy module that defers the real import until attribute access.

    Instances should be created via `lazy_import()` rather than
    instantiated directly. The proxy behaves like the underlying
    module, but the real module is not imported until an attribute is
    actually requested. Once loaded, the real module is cached.
    """

    __slots__ = ("_lazy_target", "_lazy_real")

    def __init__(self, name):
        super().__init__(name)
        object.__setattr__(self, "_lazy_target", name)
        object.__setattr__(self, "_lazy_real", None)

    def _target(self):
        return object.__getattribute__(self, "_lazy_target")

    def _resolve(self):
        real = object.__getattribute__(self, "_lazy_real")
        if real is None:
            real = importlib.import_module(self._target())
            object.__setattr__(self, "_lazy_real", real)
        return real

    def __getattr__(self, name):
        if name.startswith("_lazy_"):
            raise AttributeError(name)
        return getattr(self._resolve(), name)

    def __setattr__(self, name, value):
        if name.startswith("_lazy_"):
            object.__setattr__(self, name, value)
            return
        setattr(self._resolve(), name, value)

    def __delattr__(self, name):
        if name.startswith("_lazy_"):
            object.__delattr__(self, name)
            return
        delattr(self._resolve(), name)

    def __dir__(self):
        if object.__getattribute__(self, "_lazy_real") is None:
            return sorted(set(self.__slots__) | set(dir(types.ModuleType)))
        return dir(self._resolve())

    def __repr__(self):
        real = object.__getattribute__(self, "_lazy_real")
        if real is None:
            return "<lazy module {!r} [not loaded]>".format(self._target())
        return repr(real)

    def __bool__(self):
        return True

    def __hash__(self):
        return hash(self._target())


def lazy_import(name, package=None):
    """Return a lazy proxy for the module `name`.

    The actual import is deferred until the first attribute access on
    the returned proxy.

    Parameters
    ----------
    name : str
        The dotted module name. May be a relative name (starting with
        a dot) when `package` is given.
    package : str, optional
        The package to use as the anchor for relative imports.

    Returns
    -------
    LazyModule
        A proxy that loads the real module on first attribute access.

    Examples
    --------
    >>> np = lazy_import("numpy")
    >>> np  # not loaded yet
    <lazy module 'numpy' [not loaded]>
    >>> np.array([1, 2, 3])  # numpy is imported here
    array([1, 2, 3])
    """
    if package is not None:
        real_name = importlib.import_module(name, package).__name__
    else:
        real_name = name
    return LazyModule(real_name)


def lazy_from(module, *names):
    """Lazily import specific names from a module.

    Parameters
    ----------
    module : str or LazyModule
        A module name or an existing `LazyModule` proxy.
    *names : str
        Names to import. If no names are given, returns the module
        proxy itself.

    Returns
    -------
    LazyModule or tuple
        If `names` is empty, returns the module proxy. Otherwise
        returns a tuple of `LazyAttr` wrappers; each wrapper triggers
        the underlying import on first access.

    Examples
    --------
    >>> join, basename = lazy_from("os.path", "join", "basename")
    >>> join("a", "b")  # os.path is imported here
    'a/b'
    """
    if isinstance(module, str):
        module = lazy_import(module)
    if not names:
        return module
    return tuple(_LazyAttr(module, name) for name in names)


class _LazyAttr:
    """Wrapper that defers a `module.name` lookup until used.

    Used by `lazy_from` so that requesting multiple names from a
    module does not force the import until each name is consumed.
    """

    __slots__ = ("_module", "_name")

    def __init__(self, module, name):
        object.__setattr__(self, "_module", module)
        object.__setattr__(self, "_name", name)

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattr__(self, name):
        if name in ("_module", "_name"):
            raise AttributeError(name)
        return getattr(self._resolve(), name)

    def __repr__(self):
        module = object.__getattribute__(self, "_module")
        name = object.__getattribute__(self, "_name")
        if isinstance(module, LazyModule):
            target = module._target()
        else:
            target = getattr(module, "__name__", repr(module))
        return "<lazy attr {!r} of {!r}>".format(name, target)

    def _resolve(self):
        module = object.__getattribute__(self, "_module")
        name = object.__getattribute__(self, "_name")
        return getattr(module, name)


def is_lazy(obj):
    """Return True if `obj` is a lazy module proxy."""
    return isinstance(obj, LazyModule)


def force_load(obj):
    """Force loading of a lazy module and return the real module.

    If `obj` is not a `LazyModule`, it is returned unchanged.
    """
    if isinstance(obj, LazyModule):
        return obj._resolve()
    return obj


@contextlib.contextmanager
def lazy():
    """Context manager for grouping lazy imports.

    This is primarily a readability aid; `lazy_import()` works anywhere
    in your code. The context manager is useful for visually grouping
    related lazy imports together.

    Example::

        with lazy():
            np = lazy_import("numpy")
            pd = lazy_import("pandas")
        # None of the modules are imported until first use.
    """
    yield
