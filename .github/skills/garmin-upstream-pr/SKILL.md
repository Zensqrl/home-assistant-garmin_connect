---
name: garmin-upstream-pr
description: 'Prepare, audit and open a pull request against the upstream Garmin projects (cyberjunky/ha-garmin, cyberjunky/home-assistant-garmin_connect) from the Zensqrl forks. Use when contributing a tested fix or feature back upstream, or asked "is this branch ready for upstream?", "prepare this feature branch for PR", "clean this branch for cyberjunky". Triggers: "contribute upstream", "open a PR to cyberjunky", "upstream this change", "send this fix to the original repo".'
---

# Garmin upstream contribution

| Fork | Upstream |
|---|---|
| `Zensqrl/ha-garmin` | `cyberjunky/ha-garmin` |
| `Zensqrl/home-assistant-garmin_connect` | `cyberjunky/home-assistant-garmin_connect` |

Both upstream defaults are `main`.

The branch model, the clean-branch and port-from-polluted-branch procedures, and the no-bumps rule come from the **fork-maintenance** skill. Load it, plus the fork profiles in [CLAUDE.md](../../../CLAUDE.md) and the library's `AGENTS.md` for the overlay lists. This skill adds only what is specific to these two repos.

This is **not** the release flow. `garmin-release` deliberately carries fork-only changes; an upstream PR must carry none. Never run both on the same branch.

## Scope

A change to `src/ha_garmin/` plus the sensor that consumes it needs **two PRs, library first**. Everything else is a single PR.

Two phases below: **audit** the branch first (safe to run any time, even if not opening a PR yet — e.g. "is this branch ready for upstream?"), then **open** the PR only once the audit is clean and the user has approved.

## Phase 1: audit the branch

### Preflight commands

Run from the repo being audited:

```bash
git fetch upstream origin
git status --short --branch
git branch --show-current
git log --oneline --decorate --max-count=20
git rev-list --left-right --count upstream/main...HEAD
git diff --stat upstream/main...HEAD
git diff --name-status upstream/main...HEAD
git diff --check upstream/main...HEAD
```

Interpretation:

- Current branch must be `feat/<slug>` or another explicit PR branch, never `main`.
- The left/right count is relative to `upstream/main`, not fork `main`. Being behind fork `main` is expected and not a problem.
- If the branch is behind `upstream/main`, rebase onto `upstream/main`; do not merge.
- If the branch contains fork `main` overlay commits, create a clean branch from `upstream/main` and cherry-pick or copy only portable changes.

### Overlay scrub

Beyond the generic overlay-and-version verification, check the fork-profile overlay in `CLAUDE.md` / `AGENTS.md`, then verify no fork-only paths leaked into the upstream diff:

```bash
git diff upstream/main...HEAD -- \
  requirements.txt \
  custom_components/garmin_connect/manifest.json \
  .github/skills \
  .github/prompts \
  .github/agents \
  .github/workflows/upstream-sync.yml
```

Must print nothing, unless the feature legitimately adds a dependency. Anything there means the fork's wheel pin leaked in — the `ha-garmin @ https://github.com/Zensqrl/...` wheel pin is overlay and must never appear in an upstream PR.

**No agent customization goes upstream.** Everything under `.github/skills/`, `.github/prompts/` and `.github/agents/` is fork-only in both repos, by standing decision — never include it in a PR, in either direction. Root-level `CLAUDE.md` and `AGENTS.md` improvements *are* welcome upstream, minus the fork sections; note that upstream's `CLAUDE.md` is shorter than the fork's, so hunks often need re-anchoring rather than a clean apply.

For `ha-garmin`, apply the same rule from its `AGENTS.md`: no fork release versioning or fork-only agent customization in the PR diff.

**Upstream hassfest passing is the proof the pin was scrubbed** — it is the one check the fork permanently fails. If it fails on the PR branch, the pin is still present.

### Feature completeness checks

Use the repo conventions, not memory.

Integration sensor changes should include:

- `custom_components/garmin_connect/sensor.py`
- `custom_components/garmin_connect/strings.json`
- `custom_components/garmin_connect/translations/en.json`
- `custom_components/garmin_connect/icons.json`
- `tests/conftest.py`
- `tests/test_sensor.py`
- `README.md` and `docs/garmin_connect.markdown` when user-visible

Integration service changes should include:

- `custom_components/garmin_connect/services.py`
- `custom_components/garmin_connect/services.yaml`
- service descriptions in `strings.json`
- service icon in `icons.json`
- `tests/test_services.py`

Library endpoint changes should include:

- client implementation in `src/ha_garmin/`
- realistic mock payloads or fixture data
- tests for normalization, missing data, malformed data, and API call shape
- README contract updates when returned keys or methods are user-facing

Review bounces a sensor with no translation key.

### Validation

Run the smallest commands that cover the changed behavior, then the repo's full pre-PR checks when feasible.

```bash
scripts/test <targeted tests>
scripts/test && scripts/lint
```

or for the library:

```bash
make test
make lint
```

If tooling is missing, run the repo setup first (`scripts/setup` for the integration). If setup cannot run because the machine lacks the required Python version, report that as a blocker; do not claim the branch is ready.

Check GitHub runs too:

```bash
gh run list --repo Zensqrl/<repo> --branch "$(git branch --show-current)" \
  --limit 10 --json databaseId,displayTitle,status,conclusion,headSha,url
```

### Audit verdict

Finish the audit with one of these labels, plus the evidence behind it (base/branch SHAs, changed files, overlay diff result, test/lint/CI results):

- `Ready for upstream PR` — clean diff, current base, tests/lint pass, no overlay leaks.
- `Needs branch cleanup` — overlay/version/fork `main` commits leaked; say whether to rebase, cherry-pick, or rebuild from `upstream/main`.
- `Needs implementation work` — missing tests/docs/metadata or likely bug.
- `Needs validation` — implementation looks complete, but local or CI checks did not run/pass.
- `Blocked by dependency` — paired PR order, unreleased library change, or external requirement prevents opening/merging.

Do not proceed to Phase 2 unless the verdict is `Ready for upstream PR`.

## Phase 2: open the PR

Only after the audit is clean. Before running `gh pr create`, always show the user a summary and get explicit approval:

- target repo and branch (`cyberjunky/<repo>` base `main` ← `Zensqrl:feat/<slug>`)
- proposed title and body
- whether this is part of a paired PR (library/integration) and the ordering
- the audit verdict and evidence

Wait for the user's explicit go-ahead before pushing or opening the PR. Never open it on an unapproved title/body, and never add a `Co-Authored-By: Claude` trailer.

```bash
git push -u origin "feat/<slug>"
gh pr create --repo cyberjunky/<repo> --base main --head "Zensqrl:feat/<slug>" \
  --title "<title>" --body "<body>"
```

For the paired case, do not bump the `ha-garmin` pin to an unreleased version in the integration PR — leave it, state the dependency on the library PR in the body, and let the maintainer bump it after release. The integration's tests mock the library, so CI passes without it.

## After it merges

Sync `main` from upstream per the fork-maintenance procedure. Conflicts land on exactly the overlay lines; keep the fork's direct-reference URL, never upstream's PyPI pin. Then run `garmin-release` if the user wants the merged work in their own Home Assistant.

## Examples

### Correct: feature branch behind fork main

`git rev-list --left-right --count main...HEAD` shows many commits behind, but `git diff upstream/main...HEAD` contains only `sensor.py`, translations, docs, and tests. This is fine. Fork `main` contains overlay and release commits that do not belong on the feature branch.

### Wrong: fork wheel pin in feature branch

`git diff upstream/main...HEAD -- requirements.txt manifest.json` shows:

```diff
-ha-garmin==0.1.47
+ha-garmin @ https://github.com/Zensqrl/ha-garmin/releases/download/...
```

This branch is polluted. Remove that hunk or rebuild a clean branch from `upstream/main`; do not send it upstream.

### Wrong: fixing staleness by merging fork main

Do not run:

```bash
git merge main
```

Run:

```bash
git fetch upstream
git rebase upstream/main
```

If the branch already contains `main`, rebuild a clean branch and move only the portable commits.

### Wrong: opening the PR without a confirmation step

Even when the audit verdict is `Ready for upstream PR`, do not run `gh pr create` immediately. Show the summary (repo, branch, title, body, pairing/order) and wait for the user's approval first.
