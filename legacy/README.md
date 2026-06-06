# `legacy/` — graveyard and migration notes

This directory holds artefacts that are no longer active development
targets but are preserved for reference, migration support, or
reproducibility of historical results.

## What belongs here

- Deprecated modules scheduled for removal in a future major version.
- Historical packaging artefacts (old installer scripts, one-shot
  migration utilities).
- Snapshots referenced by a published paper so that an archived DOI
  stays reachable from source control.

## What does **not** belong here

- Active code — put it in `packages/<name>/`.
- Confidential or private material — keep it out of the public
  monorepo entirely.
- Build artefacts or test output — those belong in `.gitignore`.

## Retention policy

Each file or sub-directory in `legacy/` must carry a short top-of-file
note stating:

1. What it is.
2. Why it is archived (deprecated / superseded / reference-only).
3. When it may be deleted (a version tag or a date).

Anything older than two major versions with no "keep" note is eligible
for removal in the next cleanup pass.
