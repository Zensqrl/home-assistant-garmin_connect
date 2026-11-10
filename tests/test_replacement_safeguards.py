"""Regression coverage specific to the separately reviewed replacement candidate."""
import datetime
from unittest.mock import MagicMock

import pytest

from custom_components.garmin_connect.sensor import (
    SLEEP_SENSORS,
    SYNC_SENSORS,
    GarminConnectSensor,
)


@pytest.mark.parametrize('key', [
    'avgSleepStress', 'awakeCount', 'restlessMomentsCount',
    'avgSleepHeartRate', 'sleepBodyBatteryChange',
])
def test_new_sleep_metrics_keep_provenance_when_retained(key):
    description = next(d for d in SLEEP_SENSORS if d.key == key)
    coordinator = MagicMock()
    coordinator.last_update_success = True
    provenance = {'source_date': '2026-11-08', 'outcome': 'ok'}
    coordinator.data = {key: 0, '_sources': {'sleep': provenance}}
    sensor = GarminConnectSensor(coordinator, description, 'existing-entry')
    assert sensor.native_value == 0
    assert sensor.unique_id == f'existing-entry_{key}'
    coordinator.data = {'_sources': {'sleep': {'outcome': 'error'}}}
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes['data_provenance']['source_date'] == '2026-11-08'
    assert sensor.extra_state_attributes['data_provenance']['retained'] is True


@pytest.mark.parametrize('value', [None, True, 123, 'not-a-date', {},
                                      datetime.datetime(2026, 11, 10)])
def test_invalid_device_sync_time_is_unknown(value):
    description = next(d for d in SYNC_SENSORS if d.key == 'lastSyncTimestamp')
    assert description.value_fn({'lastSyncTimestamp': value}) is None


def test_aware_device_sync_time_is_unchanged():
    description = next(d for d in SYNC_SENSORS if d.key == 'lastSyncTimestamp')
    value = datetime.datetime(2026, 11, 10, tzinfo=datetime.UTC)
    assert description.value_fn({'lastSyncTimestamp': value}) is value


def test_bulk_attributes_are_unrecorded():
    assert {'polyline', 'body_battery', 'stress', 'sleep_stress', 'workoutSteps'} <= (
        GarminConnectSensor._unrecorded_attributes
    )
