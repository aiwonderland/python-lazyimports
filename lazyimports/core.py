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
from importlib import import_module
from importlib.util import resolve_name
import sys
import types


__all__ = [
    "NATIVE_LAZY_IMPORT",
    "SUPPORT_LAZY_IMPORT",
    "SETATTR_TARGET",
    "LazyModule",
    "lazy_import",
    "lazy_from",
    "is_lazy",
    "force_load",
    "lazy",
]


# License MIT <aiwonderland> in <2026>

# Native `lazy import` statement is available on Python 3.15+.
NATIVE_LAZY_IMPORT = sys.version_info >= (3, 15)

# GNUv3 License, add in <2019>, by <Evan Yang>

# This package provides its own implementation, so lazy imports are
# always supported regardless of interpreter version.
SUPPORT_LAZY_IMPORT = True

# License MIT <aiwonderland> in <2026>

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

# Controls where ``LazyModule.__setattr__`` writes non-internal
# attributes when the real module has not yet been loaded (or when
# loading has failed).
#
# Accepted values:
#   * ``"module"`` (default, backward-compatible): the attribute is
#     forwarded to the underlying module via ``setattr(real, ...)``.
#     This means a value written through the proxy becomes visible
#     globally (because Python modules are singletons in
#     ``sys.modules``). This matches the behaviour of ordinary
#     ``import foo`` followed by ``foo.bar = ...``.
#   * ``"proxy"``: the attribute is mounted on the proxy shell via
#     ``object.__setattr__(self, ...)``. The underlying module is
#     **not** loaded as a side effect, and the value is visible only
#     through this proxy instance. Use this when you want to attach
#     scratch state to a lazy module without paying for the import
#     or polluting the real module's namespace.
#
# Why a global instead of a per-instance flag? The two modes are
# not usually mixed in the same project; a single global keeps the
# API surface small. Change at your own risk and reset it before any
# code that expects the default behaviour runs.
SETATTR_TARGET = "module"

# GNUv3 License, add in <2018>, by <Evan Yang>
class LazyModule(types.ModuleType):
    """Proxy module that defers the real import until attribute access.

    Instances should be created via `lazy_import()` rather than
    instantiated directly. The proxy behaves like the underlying
    module, but the real module is not imported until an attribute is
    actually requested. Once loaded, the real module is cached.

    Failure handling
    ----------------
    If the first import attempt raises ``ImportError`` (typically
    because the module does not exist), the exception is **cached**
    on the proxy and re-raised on every subsequent attribute access
    — the import system is not asked again. This prevents a missing
    optional dependency from being retried on every attribute access
    in a hot loop. Use :func:`force_load` if you need to retry after
    installing the dependency.

    Magic methods
    -------------
    Python looks up operator dunders (``__eq__``, ``__lt__``,
    ``__hash__``, ``__bool__``, ``__repr__``, etc.) on the **type**,
    not the instance, so they never go through ``__getattr__`` and
    therefore never trigger the lazy import. The handful we define
    (``__hash__``, ``__bool__``, ``__eq__``, ``__ne__``, ``__repr__``)
    are based purely on the target module name, which is known at
    proxy-construction time. As a consequence:

      * Two proxies for the same module compare equal
        (``a == b`` when ``a._target() == b._target()``).
      * Hashing is consistent with equality.
      * A proxy is always truthy (``bool(proxy) is True``).

    Other operators (``<``, ``<=``, ``+``, …) fall back to
    ``object``'s default identity-based behaviour; if you need
    ordering, compare the target names explicitly.

    ``__dir__``
    -----------
    Before the proxy is loaded, ``dir(proxy)`` returns the slot names
    plus ``types.ModuleType``'s attributes. If the target module is
    already present in ``sys.modules`` (because something else
    imported it first), the contents of that module's ``__all__``
    are merged in so REPL / IDE completion sees the real exports.
    """

    __slots__ = ("_lazy_target", "_lazy_real", "_lazy_error")

    def __init__(self, name):
        super().__init__(name)
        # Use ``object.__setattr__`` because we override ``__setattr__``
        # to forward writes to the real module once it has been loaded.
        object.__setattr__(self, "_lazy_target", name)
        object.__setattr__(self, "_lazy_real", None)
        # Cached ``ImportError`` from a failed first-resolve attempt.
        # ``None`` means "no failure recorded yet". The presence of a
        # truthy value short-circuits future ``_resolve()`` calls and
        # prevents repeated import attempts.
        object.__setattr__(self, "_lazy_error", None)

    def _target(self):
        # Return the fully-qualified module name stored at construction.
        # Defined as a method (not a property) so it does not collide
        # with ``__getattr__``-driven attribute forwarding.
        return object.__getattribute__(self, "_lazy_target")

    def _resolve(self):
        # Two-state cache: either the real module is loaded, or we
        # have a cached exception to re-raise. Anything else means
        # this is the first call and we attempt the import.
        real = object.__getattribute__(self, "_lazy_real")
        if real is not None:
            return real
        error = object.__getattribute__(self, "_lazy_error")
        if error is not None:
            raise error
        try:
            real = import_module(self._target())
        except ImportError as exc:
            # Cache the exception so we don't retry. The original
            # traceback is preserved on the cached exception object.
            object.__setattr__(self, "_lazy_error", exc)
            raise
        object.__setattr__(self, "_lazy_real", real)
        return real

    def __getattr__(self, name):
        # ``_lazy_*`` attributes are managed via ``object.__setattr__``;
        # asking for one on a not-yet-loaded module would otherwise
        # recurse here, so guard explicitly.
        if name.startswith("_lazy_"):
            raise AttributeError(name)
        return getattr(self._resolve(), name)

    def __setattr__(self, name, value):
        # Internal ``_lazy_*`` slots always live on the proxy shell.
        if name.startswith("_lazy_"):
            object.__setattr__(self, name, value)
            return
        # Behaviour is controlled by the module-level ``SETATTR_TARGET``
        # flag. See the flag's docstring for the rationale.
        if SETATTR_TARGET == "proxy":
            object.__setattr__(self, name, value)
            return
        # Default: forward to the underlying module. This both loads
        # the module (if it has not been loaded yet) and makes the
        # attribute visible through every reference to that module.
        setattr(self._resolve(), name, value)

    def __delattr__(self, name):
        if name.startswith("_lazy_"):
            object.__delattr__(self, name)
            return
        # Deleting an attribute on a proxy implies the real module
        # is intended to be touched — we never silently unmount
        # shell-only state because there is none in the default mode.
        delattr(self._resolve(), name)

    def __dir__(self):
        if object.__getattribute__(self, "_lazy_real") is None:
            # Module hasn't been loaded yet by us. Show a static
            # baseline so introspection tools do not raise.
            attrs = set(dir(types.ModuleType))
            attrs.update(self.__slots__)
            # If the target module was already imported by some other
            # code path, surface its ``__all__`` so REPL completion
            # and IDEs see the real exports even before we touch it.
            target = self._target()
            already_loaded = sys.modules.get(target)
            if already_loaded is not None:
                all_attr = getattr(already_loaded, "__all__", None)
                if all_attr:
                    attrs.update(all_attr)
            return sorted(attrs)
        return dir(self._resolve())

    def __repr__(self):
        real = object.__getattribute__(self, "_lazy_real")
        if real is None:
            error = object.__getattribute__(self, "_lazy_error")
            if error is not None:
                return "<lazy module {!r} [failed: {}]>".format(
                    self._target(), error
                )
            return "<lazy module {!r} [not loaded]>".format(self._target())
        return repr(real)

    def __bool__(self):
        # A lazy proxy is always truthy, even before its target loads.
        # Modules are typically used for their side effects / attributes,
        # so truthiness should not depend on the load state.
        return True

    def __hash__(self):
        # Hash by target name so equal proxies hash equally and can
        # be used interchangeably as dict keys. Defined as a dunder
        # (rather than via ``__getattr__``) so it works before the
        # underlying module is loaded.
        return hash(self._target())

    def __eq__(self, other):
        # Two proxies are equal when their targets match. Defined as
        # a dunder so it does not trigger a lazy import — useful in
        # tests and debugging where you want to compare proxy
        # identity without paying the import cost.
        if isinstance(other, LazyModule):
            return self._target() == other._target()
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


# GNUv3 License, add in <2018>, by <Evan Yang>
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
        # real_name = importlib.import_module(name, package).__name__

        # Old code imports module eagerly and defeats lazy loading.
        # Switch to resolve_name to resolve name without importing.
        real_name = resolve_name(name, package)
    else:
        real_name = name
    return LazyModule(real_name)


# GNUv3 License, add in <2021>, by <Evan Yang>
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
        returns a tuple of `_LazyAttr` wrappers; each wrapper triggers
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


# GNUv3 License, add in <2018>, by <Evan Yang>
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


# GNUv3 License, add in <2018>, by <Evan Yang>
def is_lazy(obj):
    """Return True if `obj` is a lazy module proxy."""
    return isinstance(obj, LazyModule)


# GNUv3 License, add in <2022>, by <Evan Yang>
def force_load(obj):
    """Force loading of a lazy module and return the real module.

    If `obj` is not a `LazyModule`, it is returned unchanged.
    """
    if isinstance(obj, LazyModule):
        return obj._resolve()
    return obj


#License MIT <aiwonderland> in <2026>
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
