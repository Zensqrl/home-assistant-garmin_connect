---
name: "Add Garmin service"
description: "Add a new Home Assistant action (service) to the Garmin Connect integration end-to-end: schema, handler, registration, YAML metadata, translations, icon, docs, and tests."
argument-hint: "Service to add, e.g. 'add_weigh_in' or 'delete an activity by id'"
agent: agent
---

Add a new service (Home Assistant "action") to the `garmin_connect` custom integration, wiring up **every** file the checklist below requires. The service is described in the user's request; if it is missing or ambiguous, ask what the action should do and which Garmin write endpoint backs it before writing code.

## 1. Confirm the client method exists

Every service is a thin wrapper over one write method on the `ha-garmin` client (`set_*` / `add_*` / `upload_*`). Search `src/ha_garmin/client.py` in the sibling workspace folder for it.

If it does not exist, add it there first (see that repo's `AGENTS.md`): endpoint URL in `const.py` → write method in `client.py` (path params must go through `_assert_safe_url()` / `_validate_positive_int()` / `_validate_uuid()`) → test in `tests/test_client.py` → `make lint && make test` → bump `version` in its `pyproject.toml`, then pin that version in **both** `requirements.txt` and `requirements` in `custom_components/garmin_connect/manifest.json`. Tell the user the action cannot work until that version is published to PyPI.

## 2. `services.py`

Four additions, each next to its existing peers:

1. Constant: `SERVICE_ADD_WEIGH_IN = "add_weigh_in"`.
2. Schema, using `vol.Coerce` + `vol.Range` for numbers and `cv.*` helpers elsewhere. Always accept an optional `entity_id` so multi-account setups can target an account:

   ```python
   ADD_WEIGH_IN_SCHEMA = vol.Schema(
       {
           vol.Optional("entity_id"): cv.entity_id,
           vol.Required("weight"): vol.All(vol.Coerce(float), vol.Range(min=20, max=300)),
           vol.Optional("timestamp"): cv.string,
       }
   )
   ```

3. Handler nested inside `async_setup_services()`, resolving the client via `_get_client(hass, entity_id=call.data.get("entity_id"))` and wrapping the call:

   ```python
   async def handle_add_weigh_in(call: ServiceCall) -> None:
       """Handle add_weigh_in service call."""
       client = _get_client(hass, entity_id=call.data.get("entity_id"))
       try:
           await client.add_weigh_in(
               weight=call.data["weight"],
               timestamp=call.data.get("timestamp"),
           )
       except (GarminConnectError, ClientError) as err:
           raise HomeAssistantError(
               translation_domain=DOMAIN,
               translation_key="add_weigh_in_failed",
               translation_placeholders={"error": str(err)},
           ) from err
   ```

4. `hass.services.async_register(...)` at the bottom of `async_setup_services()` **and** a matching `hass.services.async_remove(...)` in `async_unload_services()` — forgetting the second leaves a stale action after unload.

Rules:
- Never let a raw `GarminConnectError`/`ClientError` escape. User-facing failures must be `HomeAssistantError` with `translation_domain=DOMAIN` and a `translation_key` (Silver `action-exceptions` rule) — this module uses `HomeAssistantError` for both API failures and invalid input; stay consistent.
- If the action returns data to the caller, register it with `supports_response=SupportsResponse.OPTIONAL` and have the handler return a `dict` (see `download_activity`).
- Services are registered once per HA instance, guarded in `__init__.py` by `hass.services.has_service(DOMAIN, "set_active_gear")` — do not add a second guard.

## 3. `services.yaml`

Add a block matching the existing style: `name`, `description`, and `fields` with `name`, `description`, `required: true` where applicable, an `example`, and a `selector` (`number` with min/max, `text`, `select` with `options`, or `entity` with `integration: garmin_connect`).

## 4. Translations and icon

- `custom_components/garmin_connect/strings.json` → a block under `services.<service_name>` with `name`, `description`, and a `fields.<field>.{name,description}` entry for every field in the schema.
- Same block in `custom_components/garmin_connect/translations/en.json` (it is not generated).
- `custom_components/garmin_connect/strings.json` → an entry under `exceptions` for every `translation_key` the handler raises, e.g. `"add_weigh_in_failed": { "message": "Failed to add weigh-in: {error}" }`, plus the same in en.json.
- `custom_components/garmin_connect/icons.json` → `services.<service_name>: { "service": "mdi:..." }`.

Leave `pl.json` / `zh-Hans.json` alone unless asked; they fall back to English.

## 5. Docs

`README.md` → a `### garmin_connect.<service_name>` section under Services: one-line description, a parameter table (`| Parameter | Required | Description |`), and a YAML example using `action: garmin_connect.<service_name>`.

`docs/garmin_connect.markdown` currently documents sensors only — leave it alone unless the user asks for a services section there.

## 6. Tests

In `tests/test_services.py`:
- Extend the expected set in `test_setup_registers_all_services` and the count in its docstring — it asserts an **exact** set, so it fails otherwise.
- Add a happy-path test: grab the handler with `_get_handler(mock_hass, "<service_name>")`, call it with a `ServiceCall`-like mock, and assert the client method was awaited with the right kwargs.
- Add a failure test: make the client method raise `GarminConnectError` and assert `HomeAssistantError` is raised.

## 7. Verify

```bash
scripts/test tests/test_services.py
scripts/lint
```

`scripts/lint` runs ruff, mypy, JSON/YAML syntax checks and vulture. hassfest and HACS validation only run in CI, so double-check by eye that every `services.yaml` field has a matching `strings.json` entry.

## 8. Report

Summarize as a table of touched files, show the final YAML example for the action, and call out any pending `ha-garmin` PyPI release.
