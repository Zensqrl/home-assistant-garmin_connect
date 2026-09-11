---
name: "Bump ha-garmin"
description: "Bump the ha-garmin library version and update the exact pin in the Home Assistant integration's requirements.txt and manifest.json, then run both test suites."
argument-hint: "Target version or bump type, e.g. '0.1.38' or 'patch'"
agent: agent
---

Bump the `ha-garmin` library version and propagate the exact pin to the `garmin_connect` integration. Both repos are folders in this workspace.

The target is given in the user's request — either an explicit version (`0.1.38`) or a bump type (`patch` / `minor` / `major`). If nothing is given, default to a patch bump of the current version.

## 1. Read the current state

Read `version` in the library's `pyproject.toml`, then compute the new version. Confirm the value with the user before editing if the request was a bump type rather than an explicit version.

## 2. Bump the library

In the `ha-garmin` folder:
- `pyproject.toml` → `version = "<new>"`
- `src/ha_garmin/__init__.py` → `__version__ = "<new>"`

`__version__` has drifted from `pyproject.toml` historically; set both to the new version so they match.

## 3. Update the pin in the integration

Both of these must change together — a half-bumped state installs one version and declares another:
- `requirements.txt` → `ha-garmin==<new>`
- `custom_components/garmin_connect/manifest.json` → `"requirements": ["ha-garmin==<new>"]`

Do **not** touch the `version` field in manifest.json — that is the integration's own release number, bumped separately.

Then grep the whole workspace for the old version string and confirm exactly those files changed (three edits in the library + integration, plus `__init__.py`). If another file references the pin, update it and report it.

## 4. Verify

Library:
```bash
make lint
make test
```

Integration:
```bash
scripts/test
scripts/lint
```

The integration's tests mock the library, so they pass against the new pin even before it exists on PyPI. If a real install is needed, `pip install -e ../ha-garmin` into the integration's `.venv`.

## 5. Do not publish

Never run `make publish`, `twine upload`, `git commit`, `git tag`, or `git push` as part of this task. Publishing to PyPI is manual and irreversible — leave it to the user.

## 6. Report

Report the old → new version, the files changed, both suites' results, and the remaining manual steps: publish the library to PyPI, then bump the integration's own `version` in manifest.json if this ships as an integration release.
