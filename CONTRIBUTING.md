# Contributing

Thanks for your interest in `python-lazyimports`! This document is
intentionally short — it covers only what every contributor needs to
know to get a change merged quickly.

## Reporting issues

- **Bug reports** — include a minimal reproducible example, the
  Python version (`python -V`), and the full traceback.
- **Feature requests** — describe the use case, not just the desired
  API. A short code snippet showing how you would *like* to write the
  code is the best starting point.
- **Security issues** — please do **not** open a public issue; email
  the maintainers directly instead.

## Development setup

```bash
git clone https://github.com/aiwonderland/python-lazyimports
cd python-lazyimports
python -m venv .venv
. .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e .
```

The package has **zero runtime dependencies** (only the standard
library) so the editable install is sufficient for development and
testing.

## Running the tests

The test suite uses the standard library's `unittest`:

```bash
python -m unittest test_lazyimports -v
```

A clean run — all tests passing — is required before any pull request
can be merged.

## Coding guidelines

- **Standard library only.** Do not add runtime dependencies; this is
  a hard requirement that keeps the package trivially installable.
- **Python 3.6 compatibility.** Avoid syntax introduced after 3.6
  (e.g. walrus operator, f-strings with `=` for self-doc, `match`
  statements). The code is exercised on 3.6 through 3.15.
- **Match the existing style.** The codebase uses 4-space indentation,
  `snake_case` for functions/modules and `CapWords` for classes. No
  external formatter is enforced; please read a few files in
  `lazyimports/` and follow the same conventions.
- **Keep the public API small.** Internal helpers should be prefixed
  with `_`. Anything exported from `lazyimports/__init__.py` is part
  of the API contract and must remain backward-compatible or go
  through the deprecation process below.
- **Document non-obvious decisions** in a short comment. The code
  should explain *why*, not *what*.

## Adding or changing the public API

1. Add the symbol to `lazyimports/core.py`.
2. Re-export it from `lazyimports/__init__.py` (and update `__all__`).
3. Add tests in `test_lazyimports.py` covering the new behaviour and
   the existing one.
4. Update `README.md` (the API table) and bump `__version__` in
   `lazyimports/__init__.py`.

For **breaking changes**, first deprecate the old symbol for at least
one minor release: emit a `DeprecationWarning`, document the migration
path in the README, and only remove the symbol in a subsequent
release.

## Pull request process

1. Fork the repository and create a topic branch.
2. Make focused commits with imperative-mood messages
   (`Add lazy_import support for relative packages`, not `Added …`).
3. Ensure `python -m unittest test_lazyimports -v` passes locally.
4. Push the branch and open a pull request against `main`.
5. Describe **what** changed and **why** in the PR description.
   Reference the relevant issue if one exists.
6. Be prepared to iterate on review feedback — small, focused PRs are
   reviewed fastest.

## Code of conduct

Be respectful and constructive. Disagree with ideas, not with people.
Harassment of any kind is not tolerated.

## License

By contributing, you agree that your contributions will be licensed
under the [MIT License](LICENSE).
