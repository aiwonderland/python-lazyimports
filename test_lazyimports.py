# Author: Evan Yang (aiwonderland) 2026
# License: MIT
# Copyright (c) 2026–2032 Evan Yang (aiwonderland)

"""Unit tests for the ``lazyimports`` package.

Run with::

    python -m unittest test_lazyimports -v

or directly::

    python test_lazyimports.py
"""

import math
import os
import sys
import types
import unittest

import lazyimports
from lazyimports import core
from lazyimports.core import (
    NATIVE_LAZY_IMPORT,
    SUPPORT_LAZY_IMPORT,
    LazyModule,
    force_load,
    is_lazy,
    lazy,
    lazy_from,
    lazy_import,
)


class TestVersionInfo(unittest.TestCase):
    """Tests for module-level version metadata."""

    def test_version_is_string(self):
        self.assertIsInstance(lazyimports.__version__, str)

    def test_status_format(self):
        # ``__status__`` must follow the documented
        # ``"<development>;<maintenance>;<eol-iso-date>"`` format so
        # tooling can parse it reliably.
        self.assertIsInstance(lazyimports.__status__, str)
        parts = lazyimports.__status__.split(";")
        self.assertEqual(
            len(parts), 3,
            "__status__ must have exactly three ;-separated parts, got {!r}".format(
                lazyimports.__status__
            ),
        )
        development, maintenance, eol = parts
        self.assertIn(
            development,
            {"alpha", "beta", "stable", "mature", "inactive"},
        )
        self.assertIn(
            maintenance,
            {"active", "maintenance", "security-only", "retired"},
        )
        # ISO-8601 date: YYYY-MM-DD.
        self.assertRegex(eol, r"^\d{4}-\d{2}-\d{2}$")
        # The EOL date must be after today — the project is still alive.
        import datetime
        eol_date = datetime.date.fromisoformat(eol)
        self.assertGreater(eol_date, datetime.date.today())

    def test_native_lazy_import_flag(self):
        # Must be a boolean derived from the interpreter version.
        self.assertIsInstance(NATIVE_LAZY_IMPORT, bool)
        self.assertEqual(
            NATIVE_LAZY_IMPORT, sys.version_info >= (3, 15)
        )

    def test_support_lazy_import_flag(self):
        # The backport is always available, so this must always be True.
        self.assertIs(SUPPORT_LAZY_IMPORT, True)

    def test_all_exports_resolve(self):
        for name in lazyimports.__all__:
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(lazyimports, name),
                    "lazyimports is missing {!r}".format(name),
                )


class TestLazyImport(unittest.TestCase):
    """Tests for ``lazy_import``."""

    def test_returns_lazy_module(self):
        proxy = lazy_import("os")
        self.assertIsInstance(proxy, LazyModule)
        self.assertTrue(is_lazy(proxy))

    def test_target_name(self):
        proxy = lazy_import("os.path")
        self.assertEqual(proxy._target(), "os.path")
        # ``__name__`` comes from ModuleType and is set from the
        # constructor argument.
        self.assertEqual(proxy.__name__, "os.path")

    def test_does_not_import_on_creation(self):
        # Use a module guaranteed not to be imported yet.
        sentinel = "_lazyimports_test_sentinel_does_not_exist_xyz"
        proxy = lazy_import(sentinel)
        # The proxy was created without raising even though the module
        # does not exist; the import only happens on attribute access.
        self.assertIsNone(proxy._lazy_real)
        self.assertEqual(proxy._target(), sentinel)

    def test_attribute_access_imports(self):
        proxy = lazy_import("json")
        self.assertIsNone(proxy._lazy_real)
        # Triggering attribute access should populate ``_lazy_real``.
        _ = proxy.dumps
        self.assertIsNotNone(proxy._lazy_real)
        self.assertEqual(proxy._lazy_real.__name__, "json")

    def test_caches_real_module(self):
        proxy = lazy_import("sys")
        first = proxy.version
        cached = proxy._lazy_real
        # Accessing another attribute must reuse the same real module.
        self.assertIs(proxy._lazy_real, cached)
        second = proxy.platform
        self.assertIs(proxy._lazy_real, cached)
        self.assertEqual(first, sys.version)

    def test_unknown_module_raises_on_access(self):
        proxy = lazy_import("_lazyimports_definitely_missing_module_xyz")
        with self.assertRaises(ImportError):
            proxy.any_attr  # noqa: B018

    def test_relative_import_with_package(self):
        # ``.core`` resolved against ``lazyimports`` should yield the
        # same module name as ``lazyimports.core``.
        proxy = lazy_import(".core", package="lazyimports")
        self.assertEqual(proxy._target(), "lazyimports.core")
        # Trigger the load and verify we got the same module object.
        real = force_load(proxy)
        self.assertIs(real, core)


class TestLazyFrom(unittest.TestCase):
    """Tests for ``lazy_from``."""

    def test_no_names_returns_proxy(self):
        proxy = lazy_from("os")
        self.assertIsInstance(proxy, LazyModule)
        self.assertEqual(proxy._target(), "os")

    def test_returns_tuple_when_names_given(self):
        result = lazy_from("os.path", "join", "basename")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        join, basename = result
        # The lazy attr wrappers must not yet have triggered the load.
        self.assertIsNone(join._module._lazy_real)

    def test_call_triggers_import(self):
        join, _ = lazy_from("os.path", "join", "basename")
        # Accessing via __call__ resolves and invokes the underlying
        # attribute.
        result = join("a", "b")
        expected = os.path.join("a", "b")
        self.assertEqual(result, expected)

    def test_attribute_access_triggers_import(self):
        # The wrapper supports attribute forwarding, too.
        (attr,) = lazy_from("json", "dumps")
        # ``dumps.__name__`` should be accessible without errors.
        self.assertEqual(attr.__name__, "dumps")

    def test_with_existing_proxy(self):
        proxy = lazy_import("os.path")
        result = lazy_from(proxy, "join")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]("x", "y"), os.path.join("x", "y"))


class TestIsLazy(unittest.TestCase):
    """Tests for ``is_lazy``."""

    def test_true_for_proxy(self):
        self.assertTrue(is_lazy(lazy_import("os")))

    def test_false_for_real_module(self):
        self.assertFalse(is_lazy(os))

    def test_false_for_non_module(self):
        for value in (None, 0, 1, "string", [1, 2], {"a": 1}, object()):
            with self.subTest(value=value):
                self.assertFalse(is_lazy(value))


class TestForceLoad(unittest.TestCase):
    """Tests for ``force_load``."""

    def test_returns_real_module(self):
        proxy = lazy_import("math")
        real = force_load(proxy)
        self.assertIsInstance(real, types.ModuleType)
        self.assertEqual(real.__name__, "math")

    def test_populates_real_cache(self):
        proxy = lazy_import("math")
        self.assertIsNone(proxy._lazy_real)
        real = force_load(proxy)
        self.assertIs(proxy._lazy_real, real)

    def test_non_lazy_passed_through(self):
        sentinel = object()
        self.assertIs(force_load(sentinel), sentinel)
        self.assertEqual(force_load(42), 42)
        self.assertIsNone(force_load(None))

    def test_idempotent(self):
        proxy = lazy_import("sys")
        first = force_load(proxy)
        second = force_load(proxy)
        self.assertIs(first, second)


class TestLazyContextManager(unittest.TestCase):
    """Tests for the ``lazy()`` context manager."""

    def test_basic_context(self):
        with lazy():
            proxy = lazy_import("ast")
        # ``lazy()`` is a no-op grouping marker; proxies created
        # inside it are still lazy.
        self.assertTrue(is_lazy(proxy))
        self.assertIsNone(proxy._lazy_real)

    def test_yields_none(self):
        with lazy() as value:
            self.assertIsNone(value)

    def test_exception_propagation(self):
        class Boom(Exception):
            pass

        with self.assertRaises(Boom):
            with lazy():
                raise Boom


class TestLazyModuleDunderMethods(unittest.TestCase):
    """Tests for dunder methods on ``LazyModule``."""

    def test_repr_before_load(self):
        proxy = lazy_import("os")
        self.assertEqual(repr(proxy), "<lazy module 'os' [not loaded]>")

    def test_repr_after_load(self):
        proxy = lazy_import("os")
        _ = proxy.sep  # force load
        # Once loaded, repr falls through to the real module's repr.
        self.assertEqual(repr(proxy), repr(os))

    def test_bool_is_true(self):
        self.assertTrue(bool(lazy_import("os")))
        # Even before any attribute access.
        self.assertTrue(bool(LazyModule("os")))

    def test_hash_equal_for_same_target(self):
        a = lazy_import("os")
        b = lazy_import("os")
        self.assertEqual(hash(a), hash(b))

    def test_setattr_forwards_to_real_module(self):
        proxy = lazy_import("math")
        proxy.LAZY_TEST_ATTR = 12345
        try:
            # Attribute set on the proxy must be visible on the real
            # module object.
            self.assertEqual(math.LAZY_TEST_ATTR, 12345)
            self.assertEqual(proxy.LAZY_TEST_ATTR, 12345)
        finally:
            del math.LAZY_TEST_ATTR

    def test_delattr_forwards_to_real_module(self):
        import math

        math.TEMP_ATTR = "present"
        proxy = lazy_import("math")
        del proxy.TEMP_ATTR
        self.assertFalse(hasattr(math, "TEMP_ATTR"))
        with self.assertRaises(AttributeError):
            proxy.TEMP_ATTR  # noqa: B018

    def test_dir_before_load(self):
        proxy = lazy_import("os")
        names = dir(proxy)
        # Even before loading, dir() should succeed.
        self.assertIsInstance(names, list)
        self.assertIn("__class__", names)

    def test_dir_after_load_includes_module_attrs(self):
        proxy = lazy_import("os")
        _ = proxy.sep  # force load
        names = dir(proxy)
        self.assertIn("sep", names)
        self.assertIn("path", names)


class TestLazyModuleRejectsInternalAttrs(unittest.TestCase):
    """``_lazy_*`` attributes must never recurse via ``__getattr__``."""

    def test_internal_attrs_raise(self):
        proxy = lazy_import("os")
        with self.assertRaises(AttributeError):
            _ = proxy._lazy_does_not_exist


class TestIntegration(unittest.TestCase):
    """End-to-end style tests combining several APIs."""

    def test_proxy_used_in_isinstance_with_real_class(self):
        collections_proxy = lazy_import("collections")
        OrderedDict = collections_proxy.OrderedDict
        instance = OrderedDict()
        self.assertIsInstance(instance, OrderedDict)

    def test_proxy_used_with_import_statement_pattern(self):
        # Mimic ``from os import getcwd`` style: the lazy proxy should
        # expose attributes the same way the real module does.
        getcwd = lazy_from("os", "getcwd")[0]
        self.assertEqual(getcwd(), os.getcwd())

    def test_multiple_proxies_for_same_module(self):
        # Creating multiple proxies for the same target must work
        # independently and cache independently.
        a = lazy_import("os")
        b = lazy_import("os")
        self.assertIsNot(a, b)
        _ = a.sep
        self.assertIsNone(b._lazy_real)
        _ = b.curdir
        self.assertIsNotNone(a._lazy_real)
        self.assertIsNotNone(b._lazy_real)


if __name__ == "__main__":
    unittest.main(verbosity=2)
