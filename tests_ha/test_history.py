"""Charts read the history from the recorder (bridge.get_history, called from a panel worker thread)."""
from __future__ import annotations

from datetime import timedelta

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.nspanel_lovelace_ui.backend.libs import home_assistant as bridge


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_db_url, enable_custom_integrations):
    """The recorder database has to exist before hass (overrides the conftest fixture)."""


async def test_history_from_the_recorder(recorder_mock, hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.t", "1")
    await async_wait_recording_done(hass)
    hass.states.async_set("sensor.t", "2")
    await async_wait_recording_done(hass)
    bridge.hass = hass
    try:
        start, end = dt_util.utcnow() - timedelta(hours=1), dt_util.utcnow() + timedelta(seconds=1)
        result = await hass.async_add_executor_job(bridge.get_history, "sensor.t", start, end)
    finally:
        bridge.hass = None
    assert [state for _, state in result] == ["1", "2"]
