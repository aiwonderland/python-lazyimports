"""lazyimports — A module that backports Python 3.15's lazy import.

This package provides a backport of the ``lazy import`` statement
introduced in Python 3.15, so the same deferred-import behaviour is
available on every supported Python version (3.x through 3.15).

Typical usage::

    from lazyimports import lazy_import

    np = lazy_import("numpy")   # not imported yet
    arr = np.array([1, 2, 3])   # numpy is imported here

For ``from X import Y`` style imports, use :func:`lazy_from`::

    from lazyimports import lazy_from

    join, basename = lazy_from("os.path", "join", "basename")
    join("a", "b")              # os.path is imported here

On Python 3.15+ you may also use the native syntax directly::

    lazy import numpy
    lazy from os.path import join

This package's API works identically across all supported versions.
"""

from lazyimports.core import (
    NATIVE_LAZY_IMPORT,
    SUPPORT_LAZY_IMPORT,
    LazyModule,
    lazy_import,
    lazy_from,
    is_lazy,
    force_load,
    lazy,
)


__version__ = "0.0.1"

__all__ = [
    "__version__",
    "NATIVE_LAZY_IMPORT",
    "SUPPORT_LAZY_IMPORT",
    "LazyModule",
    "lazy_import",
    "lazy_from",
    "is_lazy",
    "force_load",
    "lazy",
]
