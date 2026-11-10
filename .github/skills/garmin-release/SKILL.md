---
name: garmin-release
description: 'End-to-end release for the forked Garmin stack. Use when shipping a new ha-garmin library version and/or a new garmin_connect integration release — bumps versions, tags the library so GitHub Actions builds the wheel, repoints the integration manifest at that release asset, and publishes an integration tag plus GitHub release for HACS. Triggers: "release garmin", "ship the garmin change", "cut a new ha-garmin version", "publish the fork".'
---

# Garmin fork release

Publishes the forked stack for a separately approved Home Assistant rollout. Owner **`Zensqrl`**; the library is consumed from the fork's GitHub release assets, not PyPI.

Branching, merge strategy and version-identity rules come from the **fork-maintenance** skill and the fork profiles in [CLAUDE.md](../../../CLAUDE.md) and the library's `AGENTS.md`. Load them; this skill covers only the Garmin-specific pipeline.

To send a change to `cyberjunky` instead, use `garmin-upstream-pr`. Never run the two on the same branch.

```
bump library → tag → CI builds wheel → repoint integration pin → bump integration → tag + GitHub release → HACS
```

All phases below are subordinate to the specific approved plan. Do not bypass its PR, validation, publication or separate installation/restart gates.

## Phase 0 — Scope and branch

Releases happen on **`main`** only. If HEAD is a `feat/*` branch, merge it first rather than releasing from it:

```bash
git switch main && git merge --no-ff feat/<slug>
```

Do that in whichever repos the feature touched. If `main` is behind `origin`, stop and report.

Then establish scope, unless the request already makes it obvious:

- **Library change** (anything under `ha-garmin/src/`) → every phase.
- **Integration-only change** (sensors, services, translations, docs) → skip phases 1–4; start at phase 5 and leave the pin untouched.

Versions: the library uses `<upstream base>+zs<n>`, the integration uses plain increments. Default to incrementing the fork counter. Confirm a computed version with the user; an explicit one needs no confirmation.

## Phase 1 — Bump the library

In the `ha-garmin` folder:

- `pyproject.toml` → `version = "<lib>"`
- `src/ha_garmin/__init__.py` → `__version__ = "<lib>"`

These have drifted historically; set both. The release workflow fails the build if the tag disagrees with `pyproject.toml`.

```bash
make lint && make test
```

## Phase 2 — Commit and push the library

```bash
git add pyproject.toml src/ha_garmin/__init__.py
git commit -m "Bump version to <lib>"
git push origin main
```

Commit only the version files unless the user's change is also uncommitted — then show `git status` and ask what belongs in the release commit. Never add a `Co-Authored-By: Claude` trailer.

Push before tagging: a tag push carries its objects but does not advance the branch, so tagging first leaves the release built from a commit no branch points at.

## Phase 3 — Tag the library

Preflight, read-only — stop and report rather than fixing:

```bash
git status --porcelain                  # empty
git rev-parse --abbrev-ref HEAD         # main
git log origin/main..HEAD --oneline     # empty
git ls-remote --tags origin "v<lib>"    # empty
```

Never delete or move a published tag. If `v<lib>` exists, the fix is a new version.

**Get explicit approval before pushing** — this publishes a release and is not cleanly reversible. Show the tag, `git log -1 --oneline`, and the resulting asset URL.

```bash
git tag -a "v<lib>" -m "v<lib>"
git push origin "v<lib>"
```

## Phase 4 — Wait for the wheel, then repoint the pin

Do not write the new pin until the asset exists. Home Assistant resolves this requirement with pip at setup time, and a dangling URL fails setup with no useful error.

```bash
gh run watch --repo Zensqrl/ha-garmin
gh release view "v<lib>" --repo Zensqrl/ha-garmin --json assets
```

The asset list must contain `ha_garmin-<lib>-py3-none-any.whl`. A source-only release means the build step failed. If `gh` is unavailable, `curl -sIL -o /dev/null -w '%{http_code}' <url>` must return `200`.

On the **first** release using a `+zs<n>` version, confirm GitHub did not mangle the `+` in the asset filename and that the URL downloads. If it did, fall back to `.post<n>` and record that in the library's `AGENTS.md`.

Then update both files together — a half-updated state declares one source and installs another:

- [manifest.json](../../../custom_components/garmin_connect/manifest.json) → `"requirements": ["ha-garmin@https://github.com/Zensqrl/ha-garmin/releases/download/v<lib>/ha_garmin-<lib>-py3-none-any.whl"]`
- [requirements.txt](../../../requirements.txt) → the same string on the `ha-garmin` line

Grep the workspace for the old version string and confirm only the expected files changed.

## Phase 5 — Bump the integration

`version` in [manifest.json](../../../custom_components/garmin_connect/manifest.json) is the integration's own release number, independent of the library version. Bump it for every release — HACS uses it to decide whether an update is available.

Update [README.md](../../../README.md) and [docs/garmin_connect.markdown](../../../docs/garmin_connect.markdown) if this release adds or renames a sensor or service.

```bash
scripts/test && scripts/lint
```

The suite mocks the library, so it passes without the new wheel installed locally. For a real end-to-end check, `pip install <asset-url>` into the integration's `.venv` and run `scripts/develop`.

Keep manifest requirements in no-space `name@url` form. Require HACS and hassfest green for the exact candidate before merge; investigate failures without reverting the fork pin to PyPI or granting a blanket waiver. HACS may retain only its existing `brands` exclusion. Record the run, checked source/ref and available validator image identity.

## Phase 6 — Merge and publish the integration

Follow the specifically approved publication plan. Finish planned commits before
opening the PR, and preserve upstream ancestry with merge commits, never squash
or rebase. Require the final candidate's checks and required reviews before merge.
Verify the resulting remote `main` commit and tree before releasing from it.

Same explicit approval gate as phase 3 applies before publication. Recheck the
integration tag and release do not exist; never replace or move them. Tag the
verified `main` commit, then create an explicit GitHub release for that tag.
A tag push alone is not completion: there is no integration release-building
workflow or custom ZIP asset. Verify the published release, peeled tag commit,
generated source archive contents/hash, manifest version and exact wheel pin.
Reuse the existing matching library release for integration-only changes.

Installation, backup/rollback preparation and restart are separate rollout gates;
a publication approval does not authorize them.

## Report

- Library old → new version, tag, release URL
- The requirement string now in the manifest
- Integration old → new version, tag, explicit release URL and source archive verification
- Both suites' results, and exact-candidate HACS/hassfest results
- Remaining separately approved rollout gates: backup/rollback readiness, HACS installation, restart and acceptance

## Never

- `make publish` or `twine upload` — this fork does not go to PyPI.
- Force-push, or delete/move a published tag.
- Revert the direct-reference pin to satisfy hassfest.
- Release from a `feat/*` branch.
