---
name: garmin-upstream-pr
description: 'Open a pull request against the upstream Garmin projects (cyberjunky/ha-garmin, cyberjunky/home-assistant-garmin_connect) from the Zensqrl forks. Use when contributing a tested fix or feature back upstream. Triggers: "contribute upstream", "open a PR to cyberjunky", "upstream this change", "send this fix to the original repo".'
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

## Repo-specific checks

Beyond the generic overlay-and-version verification:

```bash
git diff upstream/main -- requirements.txt custom_components/garmin_connect/manifest.json
```

Must print nothing, unless the feature legitimately adds a dependency. Anything there means the fork's wheel pin leaked in.

**No agent customization goes upstream.** Everything under `.github/skills/`, `.github/prompts/` and `.github/agents/` is fork-only in both repos, by standing decision — never include it in a PR, in either direction. Root-level `CLAUDE.md` and `AGENTS.md` improvements *are* welcome upstream, minus the fork sections; note that upstream's `CLAUDE.md` is shorter than the fork's, so hunks often need re-anchoring rather than a clean apply.

**Upstream hassfest passing is the proof the pin was scrubbed** — it is the one check the fork permanently fails. If it fails on the PR branch, the pin is still present.

Integration PRs must include the matching `strings.json`, `translations/en.json`, `icons.json` and docs entries; review bounces a sensor with no translation key. Run `scripts/test && scripts/lint`, or `make lint && make test` for the library.

## Open the PR

```bash
git push -u origin "feat/<slug>"
gh pr create --repo cyberjunky/<repo> --base main --head "Zensqrl:feat/<slug>" \
  --title "<title>" --body "<body>"
```

Approve title and body with the user first. Never add a `Co-Authored-By: Claude` trailer.

For the paired case, do not bump the `ha-garmin` pin to an unreleased version in the integration PR — leave it, state the dependency on the library PR in the body, and let the maintainer bump it after release. The integration's tests mock the library, so CI passes without it.

## After it merges

Sync `main` from upstream per the fork-maintenance procedure. Conflicts land on exactly the overlay lines; keep the fork's direct-reference URL, never upstream's PyPI pin. Then run `garmin-release` if the user wants the merged work in their own Home Assistant.
