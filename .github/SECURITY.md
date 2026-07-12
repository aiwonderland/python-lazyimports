# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

## Scope

`python-lazyimports` has zero runtime dependencies — it uses only the
Python standard library — so the attack surface is limited to the
package itself. Reports on `LazyModule`, `lazy_import`, `lazy_from`,
`force_load`, `is_lazy`, and `lazy` are all in scope.

## Disclosure

We follow **coordinated disclosure**. Please give us a reasonable
window (typically 90 days) to investigate and release a fix before
publicly disclosing the issue.

## Recognition

Researchers who follow this policy and whose report leads to a code
change will be credited in the release notes (unless they prefer to
remain anonymous).
