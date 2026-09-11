---
name: "Add Garmin sensor"
description: "Add a new sensor entity to the Garmin Connect integration end-to-end: entity description, coordinator wiring, translations, icon, mock data, and tests."
argument-hint: "Sensor to add, e.g. 'restingCalories from core' or 'weekly VO2max trend'"
agent: agent
---

Add a new sensor to the `garmin_connect` custom integration, wiring up **every** file the checklist below requires. The sensor to add is described in the user's request; if it is missing or ambiguous, ask for the Garmin data key and which coordinator provides it before writing code.

## 1. Confirm the data exists

The state value must come from a key in the dict returned by one of the `client.fetch_*_data()` methods in the sibling `ha-garmin` library.

- Search `tests/conftest.py` (`mock_core_data()`, `mock_training_data()`, …) and the library's `src/ha_garmin/client.py` for the key.
- Map the source method to the coordinator: `fetch_core_data` → `CoordinatorType.CORE`, `fetch_training_data` → `TRAINING`, and so on.

### If the key does not exist in `ha-garmin` yet

Add it in the sibling workspace folder first (see that repo's `AGENTS.md` for full conventions):

1. Endpoint URL in `src/ha_garmin/const.py` plus a `get_*()` method in `src/ha_garmin/client.py`, if a new endpoint is needed.
2. Surface the field in the relevant `fetch_*_data()` aggregate. If it originates from an activity payload, add the field name to `ACTIVITY_ESSENTIAL_KEYS` or it will be filtered out.
3. Add a test in `tests/test_client.py` (patch `_request` with `AsyncMock`), then run `make lint && make test`.
4. Bump `version` in the library's `pyproject.toml`, and pin that version **in both** `requirements.txt` and `requirements` in `custom_components/garmin_connect/manifest.json`.

Tell the user explicitly that the integration cannot see the field until that library version is published to PyPI, and that `pip install -e ../ha-garmin` into the integration's `.venv` works for local testing in the meantime.

## 2. Entity description

In `custom_components/garmin_connect/sensor.py`, add a `GarminConnectSensorEntityDescription` to the existing group tuple that best matches the domain (`HEART_RATE_SENSORS`, `TRAINING_SENSORS`, `BODY_COMPOSITION_SENSORS`, …). Match the surrounding style:

```python
GarminConnectSensorEntityDescription(
    key="totalSteps",                       # exact key from fetch_*_data()
    translation_key="total_steps",          # snake_case, must exist in strings.json
    coordinator_type=CoordinatorType.CORE,  # omit only when CORE
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement="steps",
    preserve_value=True,                    # only if the API returns None mid-day
),
```

Rules:
- Use `device_class` + a `UnitOf*` constant whenever Home Assistant has one; add `suggested_display_precision` for floats.
- Use `value_fn=lambda data: ...` only when the value is nested or derived; plain top-level keys resolve from `key` automatically.
- Use `attributes_fn` for supporting detail rather than creating extra sensors.
- Set `entity_registry_enabled_default=False` for Garmin premium / Connect+ data.
- Set `preserve_value=True` only for values that legitimately go `None` during the day (weight, sleep, HRV).
- If you create a **new** group tuple, register it in `_COORDINATOR_SENSOR_MAP`.

### Large array attributes

If `attributes_fn` returns a big array (timeline, coordinate list, per-sample data), it must be kept out of Recorder — a state whose attribute blob exceeds 16 KiB has **all** of its attributes dropped from history:

- Add the attribute name to the class-level `_unrecorded_attributes` frozenset on `GarminConnectSensor` (it already holds `polyline`). It must stay a class attribute; setting it per instance or per entity description does nothing.
- If a sibling sensor shares the same payload, strip the array from its `attributes_fn` too — see how `lastActivity` excludes `polyline` while `lastActivityRoute` exposes it.
- Prefer the existing precedent for the state value: `lastActivityRoute` uses the sample count, not a derived timestamp. Deviate only with a stated reason.
- Mirror the `test_route_*` tests in `tests/test_sensor.py`: one asserting the attribute is unrecorded, one asserting the remaining recorded attributes stay under the cap, one asserting the array is still available live.
- Unrecorded attributes are still sent to the frontend on every update, so keep the payload compact regardless.

### Dynamic sensors

If the sensor must be created **per item in a list** (one entity per gear item, per sport, …), a static description will not work. Follow `GarminConnectGearSensor` / `GarminConnectPowerToWeightSensor` in the same file instead:

- Subclass `CoordinatorEntity[<Coordinator>]` + `SensorEntity`, with its own `_attr_unique_id` of the form `{entry_id}_{discriminator}`.
- In `async_setup_entry`, seed the entities from the first coordinator payload, track already-added discriminators in a `set`, and register an `@callback` adder via `entry.async_on_unload(coordinators.<name>.async_add_listener(_async_add_new_...))` so items appearing later are picked up.
- Handle the item disappearing from the payload by returning `None` from `native_value`.
- Existing unique IDs must never change — if the discriminator format changes, add a registry migration like `_async_migrate_gear_unique_ids`.

## 3. Translations and icon

- `custom_components/garmin_connect/strings.json` → `entity.sensor.<translation_key>: { "name": "Human Name" }`
- `custom_components/garmin_connect/translations/en.json` → same entry (en.json is not generated; it must be edited too)
- `custom_components/garmin_connect/icons.json` → `entity.sensor.<translation_key>: { "default": "mdi:..." }`

These blocks are roughly alphabetical — insert the new key next to its neighbours rather than appending. Leave `pl.json` / `zh-Hans.json` alone unless the user asks; they fall back to English.

## 4. Test data and tests

- Add a realistic sample value for the new key to the matching `mock_*_data()` helper in `tests/conftest.py`.
- Add a test to `tests/test_sensor.py` asserting the native value (and attributes, if any) resolve from the mock data. Follow the existing `test_*_returns_*` style; `asyncio_mode = "auto"`, so no `@pytest.mark.asyncio`.

## 5. Docs

Both sensor lists are maintained by hand — add the new sensor's display name to the section that matches its group:

- `README.md` → the `## Sensors` tables, format `| Sensor Name | Short description |`
- `docs/garmin_connect.markdown` → the `## Sensors` bullet list, format `- **Sensor Name** - Short description`

## 6. Verify

```bash
scripts/test tests/test_sensor.py
scripts/lint
```

The suite already enforces unique keys, present translation keys, and correct coordinator types, so a missing `strings.json` entry fails the tests.

## 7. Report

Summarize as a table of touched files plus the resulting entity ID (`sensor.garmin_connect_<name>`) and unique ID (`{entry_id}_{key}`). If work in the sibling `ha-garmin` repo was needed, call out the pending PyPI release.
