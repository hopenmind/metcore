# Contributing to the Hope 'n Mind Scientific Suite

Thank you for considering a contribution. This guide keeps the process simple
and the codebase coherent.

## Ground rules

1. **Open an issue first** for anything non-trivial: a new tool, an adapter, an
   API change, or a refactor that touches more than one file. Small fixes and
   typos can go straight to a pull request.
2. **Agree on the shape before the code.** A short sketch in the issue saves
   everyone from a large pull request that took the wrong turn.
3. **Target one package.** Each sub-package has its own `pyproject.toml`, its own
   tests, and its own scope. Keep a change inside the package it belongs to.

## Architecture in one line

Everything is a layer of one engine: a memory kernel C(tau) is compiled by
`memkern`, embedded by the Markov Embedding Theorem, and diagnosed by the
obliquity and CP-divisibility tools. A new domain is usually a small **adapter**
that turns a native quantity (a spectral density, a modulus, a synaptic kernel)
into C(tau). A new diagnostic is a function over the Prony modes. Prefer adding
to that structure over inventing a parallel one.

## Development setup

```bash
git clone https://github.com/hopenmind/hopenmind-suite
cd hopenmind-suite
uv sync --all-packages      # editable install of every member
uv run pytest               # run the full test suite
```

To work on a single package:

```bash
cd packages/memkern
pip install -e ".[test]"
pytest
```

## Pull request checklist

- [ ] Tests pass locally.
- [ ] New behaviour is covered by a test.
- [ ] Public API or CLI changes are reflected in `README.md` and `USAGE.md`.
- [ ] The CHANGELOG "Unreleased" section mentions the change.
- [ ] Prose, docstrings and comments use plain hyphens, never typographic dashes.
- [ ] No unrelated reformatting in the same commit.

## Style

- Keep functions small and pure where you can. The GUI follows a controller
  (Qt-free, testable) plus a thin view, so logic stays unit-testable without a
  display. Match that split for new panels.
- Docstrings explain the "why" and the units, not just the types.
- Write in plain English, with hyphens only. No em-dash, en-dash, or minus sign.

## Reporting bugs and asking for features

Use the issue templates under `.github/ISSUE_TEMPLATE`. For anything
security-sensitive, follow `SECURITY.md` and email us privately instead of
opening a public issue.

## License of contributions

By contributing, you agree that your work is licensed under the project terms:
Apache-2.0 OR LicenseRef-HopenMind-Commercial (see `LICENSE`).
