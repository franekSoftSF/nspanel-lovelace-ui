"""Unit tests for the in-process Home Assistant bridge."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.nspanel_lovelace_ui.backend.libs import home_assistant as bridge

from .conftest import wait_for


async def test_state_dict_matches_websocket_shape(hass: HomeAssistant) -> None:
    when = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    hass.states.async_set("sensor.x", "21.5", {"unit_of_measurement": "°C", "at": when, "list": (1, 2)})
    data = bridge.state_to_dict(hass.states.get("sensor.x"))
    assert data["state"] == "21.5"
    assert data["attributes"]["at"] == when.isoformat()
    assert data["attributes"]["list"] == [1, 2]
    data["attributes"]["mutable"] = True  # the backend may modify its copy
    assert isinstance(data["last_changed"], str)


async def test_bridge_lifecycle_and_updates(hass: HomeAssistant) -> None:
    updates: list[str] = []
    bridge.async_init(hass, updates.append)
    try:
        assert bridge.get_entity_data("light.none") is None
        hass.states.async_set("light.a", "on")
        await hass.async_block_till_done()
        assert "light.a" in updates
        assert bridge.is_existent("light.a")
        assert len(bridge.home_assistant_entity_state_cache) >= 1

        # Display precision follows the entity registry option.
        registry = er.async_get(hass)
        entry = registry.async_get_or_create("sensor", "test", "t1", suggested_object_id="temp")
        registry.async_update_entity_options(entry.entity_id, "sensor", {"display_precision": 1})
        await hass.async_block_till_done()
        assert bridge.sensor_display_precision[entry.entity_id] == 1
        assert entry.entity_id in updates

        # Template: rendered by HA (synchronously when called on the loop, else asynchronously)
        # and every change is pushed to the displaying entity.
        bridge.get_template("ha:{{ states('light.a') }}", "light.target")
        await wait_for(hass, lambda: bridge.get_template("{{ states('light.a') }}") == "on")
        assert "light.target" in updates
        updates.clear()
        hass.states.async_set("light.a", "off")
        await wait_for(hass, lambda: bridge.get_template("{{ states('light.a') }}") == "off")
        assert "light.target" in updates
        assert "light.a" in bridge.get_template_listener_entities("{{ states('light.a') }}")
    finally:
        bridge.async_shutdown()
    assert bridge.hass is None
    assert bridge.get_entity_data("light.a") is None


async def test_call_service_unknown_action(hass: HomeAssistant) -> None:
    bridge.async_init(hass, lambda _: None)
    try:
        assert bridge.call_service("light.a", "light", "does_not_exist", {}) is False
    finally:
        bridge.async_shutdown()
