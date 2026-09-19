"""Freshness remains attached to the value, even across empty polls."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorStateClass

from custom_components.garmin_connect.coordinator import CoreCoordinator, TrainingCoordinator
from custom_components.garmin_connect.sensor import (
    TRAINING_SENSORS,
    GarminConnectSensor,
    GarminConnectSensorEntityDescription,
    _source_status,
)


def test_retained_value_keeps_original_date_and_attributes():
    coordinator = MagicMock()
    coordinator.last_update_success = True
    metadata = {
        "source_date": "2026-09-17",
        "fetched_at": "2026-09-18T04:00:00+00:00",
        "outcome": "ok",
    }
    coordinator.data = {"hrvLastNightAvg": 50, "baseline": 40, "_sources": {"hrv": metadata}}
    description = GarminConnectSensorEntityDescription(
        key="hrvLastNightAvg",
        preserve_value=True,
        attributes_fn=lambda data: {"baseline": data.get("baseline")},
    )
    sensor = GarminConnectSensor(coordinator, description, "existing-entry")
    # Attribute-first access must cache the same observation as native_value.
    assert sensor.extra_state_attributes["data_provenance"]["source_date"] == "2026-09-17"
    assert sensor.native_value == 50
    coordinator.data = {
        "baseline": 99,
        "_sources": {
            "hrv": {
                "source_date": None,
                "fetched_at": "2026-09-19T04:00:00+00:00",
                "outcome": "error",
            }
        },
    }
    attrs = sensor.extra_state_attributes
    assert sensor.native_value == 50
    assert sensor.unique_id == "existing-entry_hrvLastNightAvg"
    assert attrs["baseline"] == 40
    assert attrs["data_provenance"]["source_date"] == "2026-09-17"
    assert attrs["data_provenance"]["fetched_at"] == metadata["fetched_at"]
    assert attrs["data_provenance"]["latest_outcome"] == "error"
    assert attrs["data_provenance"]["retained"] is True
    coordinator.last_update_success = False
    assert sensor.extra_state_attributes["data_provenance"]["coordinator_available"] is False


def test_missing_metadata_does_not_invent_freshness():
    coordinator = MagicMock()
    coordinator.data = {"totalSteps": 10}
    sensor = GarminConnectSensor(
        coordinator, GarminConnectSensorEntityDescription(key="totalSteps"), "entry"
    )
    assert sensor.native_value == 10
    assert sensor.extra_state_attributes == {}


def test_load_statistics_and_missing_values():
    coordinator = MagicMock()
    coordinator.data = {"acuteTrainingLoad": 0}
    descriptions = {d.key: d for d in TRAINING_SENSORS}
    for key in (
        "acuteTrainingLoad",
        "chronicTrainingLoad",
        "trainingLoadRatio",
        "hrvBaselineBalancedLow",
        "hrvBaselineBalancedUpper",
    ):
        assert descriptions[key].state_class == SensorStateClass.MEASUREMENT
    assert descriptions["trainingLoadRatioStatus"].state_class is None
    sensor = GarminConnectSensor(coordinator, descriptions["acuteTrainingLoad"], "entry")
    assert sensor.native_value == 0
    coordinator.data = {}
    assert sensor.native_value is None


@pytest.mark.parametrize(
    "coordinator_type, method",
    [(CoreCoordinator, "fetch_core_data"), (TrainingCoordinator, "fetch_training_data")],
)
async def test_ha_local_date_and_last_success(coordinator_type, method):
    hass, entry, auth = MagicMock(), MagicMock(), MagicMock()
    entry.options = {}
    client = MagicMock()
    fetch = AsyncMock(
        return_value={
            "_sources": {"summary": {"outcome": "ok", "fetched_at": "2026-09-18T03:30:00+00:00"}}
        }
    )
    setattr(client, method, fetch)
    coordinator = coordinator_type(hass, entry, client, auth)
    coordinator._update_tokens_if_changed = AsyncMock()
    # UTC date is Sep 18; configured local date still Sep 17.
    from zoneinfo import ZoneInfo

    local = datetime(2026, 9, 18, 3, 30, tzinfo=UTC).astimezone(ZoneInfo("America/New_York"))
    with patch("custom_components.garmin_connect.coordinator.dt_util.now", return_value=local):
        data = await coordinator._async_update_data()
        fetch.assert_awaited_once_with(target_date=date(2026, 9, 17))
        coordinator.data = data
        fetch.return_value = {"_sources": {"summary": {"outcome": "error", "fetched_at": "later"}}}
        failed = await coordinator._async_update_data()
    assert failed["_sources"]["summary"]["last_successful_fetch"] == "2026-09-18T03:30:00+00:00"
    assert _source_status(failed) == "partial"
    assert _source_status({}) is None
