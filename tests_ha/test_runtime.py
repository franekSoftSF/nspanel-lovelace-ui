"""End-to-end tests: MQTT in -> panel backend -> MQTT out / Home Assistant actions."""
from __future__ import annotations

import json
from pathlib import Path
import threading

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_service,
)

from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN

from .conftest import RECV, SEND, published, wait_for


def _recv(hass: HomeAssistant, message: str) -> None:
    async_fire_mqtt_message(hass, RECV, json.dumps({"CustomRecv": message}))


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    hass.states.async_set("light.bed_light", "off", {"friendly_name": "Lampka"})
    hass.states.async_set("switch.decorative_lights", "on", {"friendly_name": "Dekor"})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not [t for t in threading.enumerate() if t.name.startswith("nspanel-")]


async def test_startup_handshake(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass)
    # The panel object announces itself so the firmware reports "startup".
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))

    _recv(hass, "event,startup,54,eu")
    await wait_for(hass, lambda: any(p.startswith("dimmode~") for p in published(mqtt_mock)))
    out = published(mqtt_mock)
    assert any(p.startswith("date~") for p in out)
    assert any(p.startswith("time~") for p in out)
    assert "pageType~screensaver" in out
    assert "timeout~20" in out
    assert "dimmode~10~100~6371~~0" in out
    # qos/retain are always explicit (HA 2027.6 removes the None fallbacks).
    for call in mqtt_mock.async_publish.call_args_list:
        assert call.args[2] == 0 and call.args[3] is False
    await _unload(hass, entry)


async def test_navigation_render_and_state_updates(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass)
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))
    _recv(hass, "event,startup,54,eu")
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock))

    # Leaving the screensaver opens the first card.
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock))
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Salon") for p in published(mqtt_mock)))
    page = [p for p in published(mqtt_mock) if p.startswith("entityUpd~Salon")][-1]
    # Items are addressed by generated iids: "~light~iid.<id>~<icon>~<color>~<name>~<state>".
    assert "~light~iid." in page and "~Lampka~0" in page

    # A state change of a displayed entity re-renders the page.
    count = len(published(mqtt_mock))
    hass.states.async_set("light.bed_light", "on", {"friendly_name": "Lampka nocna"})
    await wait_for(hass, lambda: any("Lampka nocna" in p for p in published(mqtt_mock)[count:]))

    # Templates (ha: prefix) are rendered by Home Assistant and pushed on change.
    await wait_for(hass, lambda: any("Dekor on" in p for p in published(mqtt_mock)))
    hass.states.async_set("switch.decorative_lights", "off", {"friendly_name": "Dekor"})
    await wait_for(hass, lambda: any("Dekor off" in p for p in published(mqtt_mock)))
    await _unload(hass, entry)


async def test_button_calls_home_assistant_action(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    calls = async_mock_service(hass, "light", "turn_on")
    entry = await _setup(hass)
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))
    _recv(hass, "event,startup,54,eu")
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock))

    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Salon") for p in published(mqtt_mock)))
    page = [p for p in published(mqtt_mock) if p.startswith("entityUpd~Salon")][-1].split("~")
    light_iid = page[page.index("light") + 1]
    assert light_iid.startswith("iid.")

    # The panel sends the iid; the backend maps it back to the entity.
    _recv(hass, f"event,buttonPress2,{light_iid},OnOff,1")
    await wait_for(hass, lambda: len(calls) == 1)
    assert calls[0].data["entity_id"] in ("light.bed_light", ["light.bed_light"])
    await _unload(hass, entry)


async def test_ignores_foreign_and_malformed_messages(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass)
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))
    async_fire_mqtt_message(hass, RECV, "not json")
    async_fire_mqtt_message(hass, RECV, json.dumps({"POWER": "ON"}))
    async_fire_mqtt_message(hass, RECV, b"\xff\xfe")
    _recv(hass, "garbage")
    await hass.async_block_till_done()
    # The worker is still alive and answers a real message.
    _recv(hass, "event,startup,54,eu")
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock))
    await _unload(hass, entry)


async def test_invalid_config_fails_setup(hass: HomeAssistant, panels_file: Path) -> None:
    panels_file.write_text("nspanels: {broken: {}}\n", encoding="utf-8")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_reload_action(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass)
    await wait_for(hass, lambda: published(mqtt_mock).count("pageType~pageStartup") == 1)
    await hass.services.async_call(DOMAIN, "reload", blocking=True)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    await wait_for(hass, lambda: published(mqtt_mock).count("pageType~pageStartup") == 2)
    await _unload(hass, entry)


async def test_esphome_variant_uses_actions(hass: HomeAssistant, panels_file: Path) -> None:
    """use_ha_api: no MQTT; commands go to esphome.<device>_nspanelui_api_call."""
    text = panels_file.read_text(encoding="utf-8").replace(
        'panelRecvTopic: "tele/nspanel_test/RESULT"', 'panelRecvTopic: "abc123"').replace(
        'panelSendTopic: "cmnd/nspanel_test/CustomSend"', 'panelSendTopic: "nspanel_salon"')
    panels_file.write_text("use_ha_api: true\n" + text, encoding="utf-8")
    calls = async_mock_service(hass, "esphome", "nspanel_salon_nspanelui_api_call")
    entry = await _setup(hass)
    await wait_for(hass, lambda: any(c.data["data"] == "pageType~pageStartup" for c in calls))
    hass.bus.async_fire("esphome.nspanel.data", {"device_id": "abc123", "CustomRecv": "event,startup,54,eu"})
    await wait_for(hass, lambda: any(c.data["data"] == "pageType~screensaver" for c in calls))
    assert all(c.data["command"] == 2 for c in calls)
    await _unload(hass, entry)
