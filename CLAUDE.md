# CLAUDE.md

Guidance for AI coding agents (Claude Code, GitHub Copilot) working in this repository.

## Communication style

This user prefers caveman mode: terse, no filler, fragments OK, short synonyms. Drop articles/hedging/pleasantries. Technical terms exact. Code unchanged. Pattern: `[thing] [action] [reason]. [next step].`

## Git commits

Never add a `Co-Authored-By: Claude ...` trailer to commit messages.

## Commands

```bash
scripts/setup       # Install dependencies and pre-commit hooks
scripts/test        # Run pytest with coverage (extra args are forwarded)
scripts/lint        # Run pre-commit + vulture dead-code check
scripts/develop     # Start local Home Assistant instance with the integration loaded
```

Run a single test:
```bash
scripts/test tests/test_sensor.py -k test_name
```

Tooling notes:
- Pre-commit config lives at `.github/pre-commit-config.yaml`, **not** the repo root — bare `pre-commit run` will not find it. Use `scripts/lint`.
- `scripts/lint` re-runs pre-commit up to 3x (hooks rewrite files), then runs `vulture . --min-confidence 75 --ignore-names policy`. New intentionally-unused code needs a vulture-visible reference or a whitelist entry.
- Ruff: line length 100, `E501` ignored, target py314. pytest: `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed.
- CI ([.github/workflows](.github/workflows)) runs pre-commit + pytest, plus hassfest and HACS validation.

## Versioning

This is a personal fork. Branching, merge-strategy, sync and upstream-PR rules come from the **fork-maintenance** skill — this file only records what is specific to this repo.

```yaml
fork-profile:
  upstream: cyberjunky/home-assistant-garmin_connect
  upstream-default-branch: main
  fork-owner: Zensqrl
  deploy-target: HACS custom repository (GitHub release on the fork)
  version-scheme: <upstream base>.<fork counter> — e.g. 3.0.16.1
  overlay:
    - custom_components/garmin_connect/manifest.json   # the `requirements` line only
    - requirements.txt                                 # the `ha-garmin` line only
    - .github/skills/                                  # all agent customization is fork-only
    - .github/prompts/
    - .github/agents/
    - .github/workflows/upstream-sync.yml
    - CLAUDE.md                                        # the fork sections only
  verify:
    - scripts/test
    - scripts/lint
  release: garmin-release skill
```

The `ha-garmin` dependency is **not** taken from PyPI — it is a PEP 508 direct reference to a wheel attached to a GitHub release on the `Zensqrl/ha-garmin` fork:

```
ha-garmin @ https://github.com/Zensqrl/ha-garmin/releases/download/v<x.y.z>/ha_garmin-<x.y.z>-py3-none-any.whl
```

Home Assistant pip-installs that URL at setup time, so the release asset must already exist before the pin is written — a dangling URL fails integration setup. Bumping means editing **both** [requirements.txt](requirements.txt) and `requirements` in [manifest.json](custom_components/garmin_connect/manifest.json).

`is_installed()` in `homeassistant/util/package.py` returns `False` for any requirement carrying a URL, so HA re-runs pip on **every** setup. Consequences: a changed URL always takes effect, even without a version bump; and HA reaches GitHub on every restart, so an unreachable asset fails setup. Pin the exact tag anyway, for reproducibility.

HACS installs only copy `custom_components/garmin_connect/` — it does not manage Python dependencies, and manifest requirements are resolved before any config entry is read, so the source cannot be made configurable per install.

The **hassfest** job fails on this pin — its requirements check rejects any requirement containing a space, which a PEP 508 direct reference (`name @ url`) always does. That is the accepted cost of the fork — do not "fix" it by reverting to PyPI. It passing on an upstream PR branch is the proof the pin was left behind.

**HACS validation** must stay green, and needs two settings GitHub does not carry over when forking: the Issues tab enabled, and repository topics set (`garmin-connect`, `home-assistant`, `home-assistant-component`). Both are one-time.

The integration `version` in manifest.json is its own release number, independent of the library version, and is what HACS uses to offer an update.

It carries a **fourth component** identifying the fork build on top of an upstream release: upstream `3.0.16` → `3.0.16.1`, `3.0.16.2`, … When upstream publishes a new version, take it as the new base and restart the counter at `.0` — `3.0.17.0`, `3.0.17.1`, …

Do **not** use a PEP 440 local version here, as the library does. HACS compares with `awesomeversion`, which classifies `3.0.16+zs1` as SemVer and ignores build metadata for precedence, so `3.0.16+zs1 > 3.0.16` is **false** — the update would never be offered, silently. A SemVer prerelease (`3.0.16-zs1`) is worse, sorting below the base. The four-part form parses as SIMPLEVER and orders correctly, including across a base change (`3.0.17.0 > 3.0.16.3`).

Don't do any of this by hand: the `garmin-release` skill ([.github/skills/garmin-release/SKILL.md](.github/skills/garmin-release/SKILL.md)) runs the whole pipeline — bump, commit, tag the library so Actions builds the wheel, repoint the pin, bump and tag the integration.

## Contributing upstream

Branch model, scrub rules and the two-PR ordering live in the **fork-maintenance** skill. The `garmin-upstream-pr` skill ([.github/skills/garmin-upstream-pr/SKILL.md](.github/skills/garmin-upstream-pr/SKILL.md)) applies them to this pair of repos.

[upstream-sync.yml](.github/workflows/upstream-sync.yml) opens a weekly PR when `cyberjunky/home-assistant-garmin_connect` moves ahead. **Merge those with a merge commit only** — squashing breaks the ancestry check the workflow relies on.

## Architecture

This is a Home Assistant custom integration that polls the Garmin Connect cloud API via the [`ha-garmin`](https://github.com/cyberjunky/ha-garmin) library. The library is the only Garmin API dependency — all data fetching happens there, so a missing field is usually fixed in `ha-garmin` (available as a sibling folder in this workspace, see its `AGENTS.md`), not here.

User-facing docs: [README.md](README.md) (install, sensors, card setup) and [docs/garmin_connect.markdown](docs/garmin_connect.markdown). Update them when adding sensors or services.

### Data flow

Each data domain has its own `DataUpdateCoordinator` subclass in [coordinator.py](custom_components/garmin_connect/coordinator.py). All coordinators share the same `GarminClient` and `GarminAuth` instances, and each calls one `client.fetch_*_data()` method per poll:

| Coordinator | Data |
|---|---|
| `CoreCoordinator` | Daily summary, steps, sleep, HR, stress, SpO2, body battery (~50 sensors) |
| `ActivityCoordinator` | Last activity, last 10 activities, polyline, workouts (~5 sensors) |
| `TrainingCoordinator` | Readiness, VO2max, HRV, training status, scores (~11 sensors) |
| `BodyCoordinator` | Weight, BMI, hydration, fitness age, body composition (~17 sensors) |
| `GoalsCoordinator` | Badges, points, active goals (~6 sensors) |
| `GearCoordinator` | Gear stats (dynamic sensors per item), alarms |
| `BloodPressureCoordinator` | Latest BP reading (~3 sensors) |
| `MenstrualCoordinator` | Menstrual data (~9 sensors, disabled by default) |
| `NutritionCoordinator` | Consumed macros, goals, per-meal breakdown (~11 sensors, disabled by default, Connect+) |

All coordinators subclass `BaseGarminCoordinator`, which maps `GarminAuthError` → `ConfigEntryAuthFailed` (triggers reauth) and any other `GarminConnectError`/`ClientError` → `UpdateFailed`. It also persists refreshed tokens back to the config entry after each fetch — keep that call when adding a coordinator. Only `CoreCoordinator` uses `async_config_entry_first_refresh()`; the rest refresh in parallel so a premium-only endpoint failure never blocks setup.

### Sensor definitions

All sensors are declared as `GarminConnectSensorEntityDescription` tuples in [sensor.py](custom_components/garmin_connect/sensor.py), grouped by coordinator. Each description has:
- `coordinator_type` — which coordinator feeds it
- `value_fn` — lambda to extract the state value from coordinator data (falls back to `key` lookup if omitted)
- `attributes_fn` — lambda to extract extra state attributes
- `preserve_value=True` — retains last non-`None` value (used for weight, sleep, HRV which go `None` mid-day)
- `entity_registry_enabled_default=False` — used for premium/Connect+ groups (menstrual, nutrition)

Adding a sensor: description tuple in its coordinator group → group listed in `_COORDINATOR_SENSOR_MAP` → `translation_key` entry in [strings.json](custom_components/garmin_connect/strings.json) **and** [translations/en.json](custom_components/garmin_connect/translations/en.json) → icon in [icons.json](custom_components/garmin_connect/icons.json) → sample value in the matching `mock_*_data()` in [tests/conftest.py](tests/conftest.py).

Gear and power-to-weight sensors are created dynamically from list data rather than static descriptions, and are added on coordinator updates.

### Large attributes and Recorder

Home Assistant's recorder drops **all** attributes for a state whose attribute blob exceeds 16 KiB, so any sensor exposing a big array must keep it out of the database. `GarminConnectSensor` declares a class-level `_unrecorded_attributes = frozenset({"polyline"})` for exactly this reason — it must be a class attribute, not set per instance or per entity description. New bulk attributes (timelines, coordinate lists, per-sample arrays) belong in that frozenset, and a sibling sensor sharing the same payload should strip the array from its own `attributes_fn` (see how `lastActivity` excludes `polyline`). Unrecorded attributes still live in the state machine and are sent to the frontend, so keep them compact anyway. The `test_route_*` tests in [tests/test_sensor.py](tests/test_sensor.py) are the template for proving both the exclusion and the 16 KiB ceiling.

### Services

Adding a service touches five files: `vol.Schema` + handler registration in [services.py](custom_components/garmin_connect/services.py), field metadata in [services.yaml](custom_components/garmin_connect/services.yaml), descriptions under `services` in [strings.json](custom_components/garmin_connect/strings.json), an icon in [icons.json](custom_components/garmin_connect/icons.json), and a test in [tests/test_services.py](tests/test_services.py). User-facing failures must raise translated `HomeAssistantError` subclasses (Silver `action-exceptions` rule).

### Config flow

[config_flow.py](custom_components/garmin_connect/config_flow.py) handles user, MFA (`GarminMFARequired` → `step_mfa`), reauth, reconfigure (region toggle), and an options flow for `CONF_SCAN_INTERVAL`. Unique ID is the Garmin profile ID. Auth is synchronous, so every `login()`/`complete_mfa()` call must go through an executor job.

### Quality scale

The integration targets **gold** ([quality_scale.yaml](custom_components/garmin_connect/quality_scale.yaml)). Bronze/Silver/Gold rules are done or exempt; `async-dependency` and `inject-websession` remain the open Platinum items. Update quality_scale.yaml when a change affects a rule.

### Tests

[tests/conftest.py](tests/conftest.py) provides `mock_config_entry`, `mock_auth`, and `mock_client` (every `fetch_*_data()` stubbed with realistic dicts from `mock_*_data()` helpers). Tests use `pytest-homeassistant-custom-component`; there is no snapshot testing. Sensor tests assert invariants — unique keys, present translation keys, correct coordinator types — so a new sensor missing a translation key fails the suite.

### Key data facts from `ha-garmin`

- `startTimeLocal` is **dropped** by the library; use `startTime` (UTC datetime) instead. In templates: `(a.startTime | as_datetime | as_local).strftime('%Y-%m-%d')`
- `activityType` is simplified to a plain string (`"running"`, `"cycling"`, etc.)
- `polyline` (GPS coordinates as `[{lat, lon}]`) lives on `lastActivityRoute` sensor, **not** `lastActivity`

### Custom Lovelace card

`www/garmin-polyline-card.js` renders activity routes using Leaflet. Users must copy **all three files** from `www/` to `<config>/www/`: the card JS plus `leaflet.js` and `leaflet.css`.

### Entity unique IDs

Format: `{entry_id}_{sensor_key}`. The v1→v2 migration in [\_\_init\_\_.py](custom_components/garmin_connect/__init__.py) rewrites unique IDs from the old `{email}_{key}` format and triggers reauth (tokens are incompatible between versions).
