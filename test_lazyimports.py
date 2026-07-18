"""Unit tests for the ``lazyimports`` package.

Run with::

    python -m unittest test_lazyimports -v

or directly::

    python test_lazyimports.py
"""

# A feature again :)
__lazy_modules__ = [
    "types",
]

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
    SETATTR_TARGET,
    LazyModule,
    _check_SETATTR_TARGET_value,
    force_load,
    is_lazy,
    lazy,
    lazy_from,
    lazy_import,
)


#License MIT <aiwonderland> in <2026>
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


# GNUv3 License, add in <2018>, by <Evan Yang>
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


# GNUv3 License, add in <2021>, by <Evan Yang>
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


# GNUv3 License, add in <2018>, by <Evan Yang>
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


# GNUv3 License, add in <2022>, by <Evan Yang>
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


#License MIT <aiwonderland> in <2026>
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


# GNUv3 License, add in <2018>, by <Evan Yang>
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



# GNUv3 License, add in <2018>, by <Evan Yang>
class TestLazyModuleRejectsInternalAttrs(unittest.TestCase):
    """``_lazy_*`` attributes must never recurse via ``__getattr__``."""

    def test_internal_attrs_raise(self):
        proxy = lazy_import("os")
        with self.assertRaises(AttributeError):
            _ = proxy._lazy_does_not_exist



# GNUv3 License, add in <2018>, by <Evan Yang>
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


# License MIT <aiwonderland> in <2026>
class TestSetattrTarget(unittest.TestCase):
    """Tests for the ``SETATTR_TARGET`` mode switch.

    ``SETATTR_TARGET`` controls whether ``LazyModule.__setattr__``
    forwards attribute writes to the underlying module (``"module"``,
    the default) or mounts them on the proxy shell only
    (``"proxy"``).
    """

    # Helper used by the mode tests. Save and restore the global so
    # a failure in one test cannot leak into another.
    def setUp(self):
        self._previous_mode = SETATTR_TARGET

    def tearDown(self):
        # Reset to the default for every test that runs afterwards.
        lazyimports.core.SETATTR_TARGET = self._previous_mode
        # In case the default ever changes, fall back to "module".
        if lazyimports.core.SETATTR_TARGET not in ("module", "proxy"):
            lazyimports.core.SETATTR_TARGET = "module"

    def test_default_is_module(self):
        # The package default must be the backward-compatible mode.
        self.assertEqual(SETATTR_TARGET, "module")

    def test_module_mode_forwards_to_underlying_module(self):
        lazyimports.core.SETATTR_TARGET = "module"
        proxy = lazy_import("math")
        sentinel_name = "_setattr_target_module_test_attr"
        try:
            proxy.SCRATCH_ATTR = "via-proxy"
            # The attribute must be visible on the real module too
            # (because the write was forwarded).
            self.assertEqual(math.SCRATCH_ATTR, "via-proxy")
        finally:
            if hasattr(math, sentinel_name):
                delattr(math, sentinel_name)

    def test_proxy_mode_does_not_load_module(self):
        lazyimports.core.SETATTR_TARGET = "proxy"
        # Use a sentinel module name guaranteed not to exist; the
        # ``"proxy"`` mode must not even attempt to import it.
        sentinel = "_lazyimports_setattr_proxy_sentinel_xyz"
        proxy = lazy_import(sentinel)
        # No exception yet because we have not touched the module.
        proxy.SCRATCH_ATTR = "scratch"
        # The proxy shell must carry the value.
        self.assertEqual(proxy.SCRATCH_ATTR, "scratch")
        # And the underlying import must NOT have been triggered.
        self.assertIsNone(proxy._lazy_real)
        self.assertIsNone(proxy._lazy_error)
        # Sanity: touching a real attribute now should still raise.
        with self.assertRaises(ImportError):
            _ = proxy.any_real_attribute  # noqa: B018

    def test_proxy_mode_is_per_instance(self):
        # Two proxies in proxy mode must not see each other's state
        # because the writes are local to the shell.
        lazyimports.core.SETATTR_TARGET = "proxy"
        sentinel = "_lazyimports_setattr_proxy_isolation_xyz"
        a = lazy_import(sentinel)
        b = lazy_import(sentinel)
        a.ONLY_ON_A = 1
        # Check ``b``'s instance dict directly so we don't trigger
        # ``__getattr__`` (which would try to import the missing
        # module). The whole point of proxy mode is to keep state
        # local, so verifying the dicts are isolated is enough.
        self.assertNotIn("ONLY_ON_A", b.__dict__)
        self.assertIn("ONLY_ON_A", a.__dict__)
        # ``a`` still has its value.
        self.assertEqual(a.ONLY_ON_A, 1)

    def test_internal_lazy_slots_unaffected_by_mode(self):
        # The ``_lazy_*`` slot writes always go through
        # ``object.__setattr__`` regardless of the mode flag.
        for mode in ("module", "proxy"):
            with self.subTest(mode=mode):
                lazyimports.core.SETATTR_TARGET = mode
                proxy = lazy_import("os")
                # Touching internal slots must work in both modes.
                self.assertEqual(proxy._target(), "os")
                self.assertIsNone(proxy._lazy_real)
                self.assertIsNone(proxy._lazy_error)


# License MIT <aiwonderland> in <2026>
class TestImportErrorCaching(unittest.TestCase):
    """``ImportError`` on first resolve must be cached.

    Missing optional dependencies should not be retried on every
    attribute access — that would defeat the whole purpose of the
    backport for conditional dependencies.
    """

    def test_missing_module_caches_error(self):
        sentinel = "_lazyimports_cache_err_does_not_exist_xyz"
        proxy = lazy_import(sentinel)
        # First access fails and caches the exception.
        with self.assertRaises(ImportError):
            proxy.any_attr  # noqa: B018
        cached = proxy._lazy_error
        self.assertIsNotNone(cached)
        self.assertIsInstance(cached, ImportError)
        # The real module must still be unset.
        self.assertIsNone(proxy._lazy_real)
        # Subsequent accesses re-raise the SAME cached exception
        # object (proves we did not retry the import).
        with self.assertRaises(ImportError) as ctx:
            proxy.other_attr  # noqa: B018
        self.assertIs(ctx.exception, cached)

    def test_force_load_after_failure_still_raises(self):
        # ``force_load`` must not magically succeed when the module
        # really does not exist; it just re-raises the cached error.
        sentinel = "_lazyimports_force_load_after_err_xyz"
        proxy = lazy_import(sentinel)
        with self.assertRaises(ImportError):
            _ = proxy.any_attr  # noqa: B018
        with self.assertRaises(ImportError):
            force_load(proxy)

    def test_repr_after_failure_includes_error(self):
        sentinel = "_lazyimports_repr_after_err_xyz"
        proxy = lazy_import(sentinel)
        with self.assertRaises(ImportError):
            proxy.any_attr  # noqa: B018
        text = repr(proxy)
        # The failure must be visible in the repr so debugging is easy.
        self.assertIn("[failed", text)
        self.assertIn(sentinel, text)


# License MIT <aiwonderland> in <2026>
class TestMagicMethodsNoLoad(unittest.TestCase):
    """Operator dunders must not trigger a lazy import.

    Python looks up operator dunders (``__eq__``, ``__hash__``, ...)
    on the *type*, not on the instance, so they never reach
    ``__getattr__`` and never trigger an import. These tests pin
    that contract down.
    """

    def test_eq_uses_target_name(self):
        a = lazy_import("os")
        b = lazy_import("os")
        c = lazy_import("sys")
        # Equality must be true even before any module is loaded.
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        # And no import should have been triggered by the comparison.
        self.assertIsNone(a._lazy_real)
        self.assertIsNone(b._lazy_real)
        self.assertIsNone(c._lazy_real)

    def test_ne_uses_target_name(self):
        a = lazy_import("os")
        b = lazy_import("sys")
        self.assertTrue(a != b)
        # ``a != b`` short-circuits on equality, so still no import.
        self.assertIsNone(a._lazy_real)
        self.assertIsNone(b._lazy_real)

    def test_eq_with_non_lazy_returns_not_equal(self):
        # A proxy is never equal to an arbitrary non-proxy object.
        proxy = lazy_import("os")
        self.assertNotEqual(proxy, 42)
        self.assertNotEqual(proxy, "os")
        self.assertNotEqual(proxy, None)
        self.assertIsNone(proxy._lazy_real)

    def test_hash_consistent_with_eq(self):
        # ``hash(a) == hash(b)`` whenever ``a == b``. This is the
        # invariant Python requires of any object that defines
        # ``__eq__``.
        a = lazy_import("os.path")
        b = lazy_import("os.path")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_bool_is_true_without_loading(self):
        proxy = lazy_import("os")
        self.assertIs(bool(proxy), True)
        self.assertIsNone(proxy._lazy_real)


# License MIT <aiwonderland> in <2026>
class TestEnhancedDir(unittest.TestCase):
    """``__dir__`` should surface ``__all__`` when the target is
    already in ``sys.modules``."""

    def test_dir_merges_all_when_already_loaded(self):
        # ``os`` is imported very early by Python itself, so it is
        # almost always in ``sys.modules``. The proxy's dir() should
        # merge those exported names.
        proxy = lazy_import("os")
        names = dir(proxy)
        self.assertIn("sep", names)
        self.assertIn("path", names)
        self.assertIn("__class__", names)

    def test_dir_static_fallback_when_not_loaded(self):
        # Use a sentinel that is definitely not in sys.modules.
        sentinel = "_lazyimports_dir_sentinel_xyz"
        # Make absolutely sure it is not loaded.
        sys.modules.pop(sentinel, None)
        proxy = lazy_import(sentinel)
        names = dir(proxy)
        # Static baseline still contains the slot names.
        self.assertIsInstance(names, list)
        self.assertIn("__class__", names)
        # And must not have triggered an import.
        self.assertIsNone(proxy._lazy_real)
        self.assertIsNone(proxy._lazy_error)


# License MIT <aiwonderland> in <2026>
class TestSetattrTargetExported(unittest.TestCase):
    """The ``SETATTR_TARGET`` constant must be reachable from the
    package top level so users can read it.

    Note on configuration
    ---------------------
    Python's import semantics mean that ``lazyimports.SETATTR_TARGET``
    is a **re-exported binding**: it captures the string value at
    package import time. To change the mode at runtime, write to
    ``lazyimports.core.SETATTR_TARGET`` (the canonical location);
    the ``LazyModule.__setattr__`` implementation reads from there
    every time it is invoked.
    """

    def test_exported_in_package_all(self):
        self.assertIn("SETATTR_TARGET", lazyimports.__all__)

    def test_exported_attribute_matches_core(self):
        # The re-exported value equals the live core value at import
        # time. (Strings are immutable, so identity equality is fine.)
        self.assertEqual(lazyimports.SETATTR_TARGET, core.SETATTR_TARGET)

    def test_configuration_via_core_round_trips(self):
        # Writing through ``lazyimports.core.SETATTR_TARGET`` is the
        # supported configuration path and must take effect
        # immediately for any new ``__setattr__`` call.
        original = core.SETATTR_TARGET
        try:
            core.SETATTR_TARGET = "proxy"
            proxy = lazy_import("os")
            # The proxy's ``__setattr__`` must observe the new mode.
            # We probe by setting an internal-only attribute via the
            # default code path: in proxy mode the underlying module
            # is NOT loaded as a side effect.
            proxy.SCRATCH = 1
            # The write went to the shell, not to ``os`` itself, so
            # ``os`` must not have been touched (and therefore not
            # loaded by us through the test scenario).
            self.assertNotIn("SCRATCH", os.__dict__)
            core.SETATTR_TARGET = "module"
        finally:
            core.SETATTR_TARGET = original
        # Sanity: default mode behaviour is restored.
        proxy2 = lazy_import("math")
        try:
            proxy2.SCRATCH2 = 2
            self.assertTrue(hasattr(math, "SCRATCH2"))
        finally:
            if hasattr(math, "SCRATCH2"):
                delattr(math, "SCRATCH2")


# License MIT <aiwonderland> in <2026>
class TestCheckSetattrTargetValue(unittest.TestCase):
    """Tests for ``_check_SETATTR_TARGET_value``.

    The validator is the single source of truth for what counts as a
    legal ``SETATTR_TARGET`` value. It must:

      * return the validated value (acting as a normaliser);
      * accept both ``"module"`` and ``"proxy"``;
      * reject unknown strings with ``ValueError``;
      * reject non-string arguments with ``TypeError``;
      * treat ``value=None`` as a request to re-check the current
        module-level ``SETATTR_TARGET``.
    """

    def setUp(self):
        # Save and restore the global so an exception-raising test
        # does not leave the package in a broken state for the
        # tests that follow.
        self._previous_mode = core.SETATTR_TARGET

    def tearDown(self):
        core.SETATTR_TARGET = self._previous_mode
        if core.SETATTR_TARGET not in ("module", "proxy"):
            core.SETATTR_TARGET = "module"

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------
    def test_default_module_value_passes(self):
        # The shipped default must validate without raising. We
        # call without an argument so the function checks the
        # current ``SETATTR_TARGET``.
        result = _check_SETATTR_TARGET_value()
        self.assertEqual(result, SETATTR_TARGET)
        self.assertEqual(result, "module")

    def test_explicit_module_string(self):
        result = _check_SETATTR_TARGET_value("module")
        self.assertEqual(result, "module")

    def test_explicit_proxy_string(self):
        result = _check_SETATTR_TARGET_value("proxy")
        self.assertEqual(result, "proxy")

    def test_none_argument_validates_current_value(self):
        # ``None`` is documented as ``"check the current value"``,
        # not as "missing argument". This is a behaviour the tests
        # lock down so a future refactor cannot quietly change it.
        core.SETATTR_TARGET = "proxy"
        result = _check_SETATTR_TARGET_value(None)
        self.assertEqual(result, "proxy")
        core.SETATTR_TARGET = "module"
        result = _check_SETATTR_TARGET_value(None)
        self.assertEqual(result, "module")

    def test_returns_valid_value_for_use_as_normaliser(self):
        # The return value must equal the input when it is valid,
        # which lets callers use the function as a one-stop
        # ``str -> Literal[...]`` converter.
        self.assertEqual(_check_SETATTR_TARGET_value("module"), "module")
        self.assertEqual(_check_SETATTR_TARGET_value("proxy"), "proxy")

    # ------------------------------------------------------------------
    # Value errors
    # ------------------------------------------------------------------
    def test_unknown_string_raises_value_error(self):
        for bad in ("MODULE", "Module", "Module ", "", "modules", "prxy"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    _check_SETATTR_TARGET_value(bad)

    def test_value_error_message_lists_accepted_values(self):
        # The message is part of the API surface: callers (and
        # automated tooling) rely on it being informative without
        # having to consult the source.
        try:
            _check_SETATTR_TARGET_value("nope")
        except ValueError as exc:
            message = str(exc)
        else:
            self.fail("ValueError not raised")
        # Both accepted values must appear in the message.
        self.assertIn("'module'", message)
        self.assertIn("'proxy'", message)
        # And the offending value must be echoed back so the
        # user can see what they sent.
        self.assertIn("'nope'", message)

    def test_value_error_with_none_checks_current(self):
        # If the *current* ``SETATTR_TARGET`` has been corrupted
        # before the test runs, the validator must still catch it.
        core.SETATTR_TARGET = "garbage"
        with self.assertRaises(ValueError):
            _check_SETATTR_TARGET_value(None)

    # ------------------------------------------------------------------
    # Type errors
    # ------------------------------------------------------------------
    def test_non_string_raises_type_error(self):
        for bad in (0, 1, 1.5, True, None, [], {}, (), b"module", object()):
            with self.subTest(value=bad, type=type(bad).__name__):
                # ``None`` is special-cased (means "check current
                # value") and should NOT raise ``TypeError``. Skip
                # it explicitly here.
                if bad is None:
                    continue
                with self.assertRaises(TypeError):
                    _check_SETATTR_TARGET_value(bad)

    def test_type_error_message_mentions_str(self):
        try:
            _check_SETATTR_TARGET_value(42)
        except TypeError as exc:
            message = str(exc)
        else:
            self.fail("TypeError not raised")
        # The error must point at ``str`` as the expected type so
        # users immediately know what to pass instead.
        self.assertIn("str", message)

    def test_subclass_of_str_is_accepted(self):
        # ``str`` subclasses are valid: this is standard Python
        # duck-typing and avoids surprising users who build their
        # own string-like types.
        class MyStr(str):
            pass
        self.assertEqual(_check_SETATTR_TARGET_value(MyStr("module")), "module")
        self.assertEqual(_check_SETATTR_TARGET_value(MyStr("proxy")), "proxy")

    # ------------------------------------------------------------------
    # Integration with the package import-time check
    # ------------------------------------------------------------------
    def test_package_loaded_successfully(self):
        # ``__init__.py`` calls ``_check_SETATTR_TARGET_value()``
        # once at import time. The mere fact that we have reached
        # this test class proves the call succeeded; if the
        # default value were invalid the import would have raised
        # before any test could run.
        #
        # We additionally assert the global is still in a valid
        # state after all the previous tests have potentially
        # poked at it.
        _check_SETATTR_TARGET_value()  # must not raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
