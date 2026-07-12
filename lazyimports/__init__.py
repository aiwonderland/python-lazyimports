# Author: Evan Yang (aiwonderland) 2026
# License: MIT
# Copyright (c) 2026–2032 Evan Yang (aiwonderland)

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

Or more information, see <https://github.com/aiwonderland/python-lazyimports/blob/main/docs/documentation.md>
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


__version__ = "0.1.3"

# Lifecycle status marker for this package.
#
# Rationale for using a plain string: it offers maximum portability with zero extra dependencies,
# allowing users and automation tooling to inspect the project lifecycle state at runtime
# without relying on importlib.metadata, network requests, or platform-specific logic.
# While a structured dictionary would support richer metadata, it would lock the project into
# a rigid schema that becomes difficult to extend and revise later.
#
# String format: ``"<development-phase>;<maintenance-tier>;<eol-iso-date>"``
#   - ``development-phase`` follows PyPI's standard Development Status classifiers
#     (examples: "beta", "stable", "inactive"). Aligning with this shared vocabulary
#     ensures the value remains parsable by automated tooling.
#   - ``maintenance-tier`` accepts exactly four fixed values: "active", "maintenance",
#     "security-only", "retired". Scripts and tools may use this field for direct conditional logic.
#   - ``eol-iso-date`` denotes the scheduled end-of-life date in ISO‑8601 (YYYY‑MM‑DD).
#     This timeline is derived from the official EOL schedule of Python 3.15 (October 2031).
#     It is subject to revision if the upstream Python release timeline shifts.
__status__ = "beta;active;2031-10-31"


__all__ = [
    "__version__",
    "__status__",
    "NATIVE_LAZY_IMPORT",
    "SUPPORT_LAZY_IMPORT",
    "LazyModule",
    "lazy_import",
    "lazy_from",
    "is_lazy",
    "force_load",
    "lazy",
]
