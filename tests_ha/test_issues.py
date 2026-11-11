"""Regression tests for upstream issues fixed in the integration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.nspanel_lovelace_ui.backend.libs import home_assistant as bridge
from custom_components.nspanel_lovelace_ui.config import load_config
from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN
from custom_components.nspanel_lovelace_ui.runtime import referenced_entities

from .conftest import RECV, published, wait_for


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


# --- #1480: duplicate YAML keys ---------------------------------------------------------

def test_duplicate_keys_warn_instead_of_failing(tmp_path: Path) -> None:
    path = tmp_path / "panels.yaml"
    path.write_text(
        "nspanels:\n"
        "  p1:\n"
        "    panelRecvTopic: a/RESULT\n"
        "    panelSendTopic: a/CustomSend\n"
        "    locale: en_US\n"
        "    timeFormat: '%H:%M'\n"
        "    dateFormat: full\n"
        "    screensaver: {}\n"
        "    cards:\n"
        "      - type: cardEntities\n"
        "        title: First\n"
        "        title: Second\n"
        "        entities: []\n",
        encoding="utf-8",
    )
    config, warnings = load_config(path)
    assert config["nspanels"]["p1"]["cards"][0]["title"] == "Second"  # PyYAML: last wins
    assert warnings == ["line 12: duplicate key 'title' (the last one is used)"]


async def test_duplicate_keys_create_repair_issue(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    panels_file.write_text(panels_file.read_text(encoding="utf-8").replace(
        "        title: Salon\n", "        title: Salon\n        title: Salon\n"), encoding="utf-8")
    entry = await _setup(hass)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "config_warnings")
    assert issue is not None
    assert "duplicate key 'title'" in issue.translation_placeholders["warnings"]
    await hass.config_entries.async_unload(entry.entry_id)


# --- #1465: only configured entities wake the panels ------------------------------------

def test_referenced_entities() -> None:
    settings = yaml.safe_load("""
    nspanels:
      p:
        sleepTracking: person.anna
        sleepTrackingZones: [not_home, "off"]
        screensaver:
          entities: [{entity: weather.home}]
          statusIcon1: {entity: switch.x}
        cards:
          - type: cardGrid
            navItem1: {entity: navigate.home}
            entities:
              - entity: light.a
                status: binary_sensor.door
              - entity: service.fan.set_direction
                data: {entity_id: fan.ceiling}
              - entity: iText.hello
              - entity: sensor.t
                name: "ha:{{ states('sensor.other') }}"
    """)
    assert referenced_entities(settings) == {
        "person.anna", "weather.home", "switch.x", "light.a", "binary_sensor.door", "fan.ceiling",
        "sensor.t", "sun.sun"}


async def test_unrelated_state_changes_are_not_forwarded(hass: HomeAssistant) -> None:
    updates: list[str] = []
    bridge.async_init(hass, updates.append, frozenset({"light.a"}))
    try:
        hass.states.async_set("sensor.power_meter", "1")
        hass.states.async_set("light.a", "on")
        await hass.async_block_till_done()
        assert updates == ["light.a"]
        # Template results are still forwarded to their targets.
        bridge.get_template("ha:{{ states('sensor.power_meter') }}", "light.a")
        updates.clear()
        hass.states.async_set("sensor.power_meter", "2")
        await wait_for(hass, lambda: "light.a" in updates)
    finally:
        bridge.async_shutdown()


# --- #1470: navItem1 override on hidden cards -------------------------------------------

async def test_nav_item1_override_on_hidden_card(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    panel = config["nspanels"]["living_room"]
    panel["cards"][0]["key"] = "home"
    panel["cards"][0]["entities"].append({"entity": "navigate.daily"})
    panel["hiddenCards"] = [
        {"type": "cardEntities", "title": "Daily", "key": "daily",
         "navItem1": {"entity": "navigate.home", "icon": "mdi:home", "color": [255, 255, 255]},
         "navItem2": {"entity": "light.bed_light"},
         "entities": [{"entity": "switch.decorative_lights"}]},
    ]
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    calls = []
    hass.services.async_register("light", "toggle", lambda call: calls.append(call))
    entry = await _setup(hass)
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))
    _recv(hass, "event,startup,54,eu")
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")
    _recv(hass, "event,buttonPress2,navigate.daily,button")
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[-3:])
    _recv(hass, "event,renderCurrentPage")  # the firmware asks for content after a page switch
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Daily") for p in published(mqtt_mock)))
    page = [p for p in published(mqtt_mock) if p.startswith("entityUpd~Daily")][-1].split("~")
    # Left button: the configured navigate.home (not navigate.UP); right button: the light.
    assert page[2:4] == ["button", "navigate.home"]  # page[0:2] = entityUpd, title
    assert "navigate.UP" not in page
    assert page[8] == "light" and page[9].startswith("iid.")

    # The override navigates to its target card.
    count = len(published(mqtt_mock))
    _recv(hass, "event,buttonPress2,navigate.home,button")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Salon") for p in published(mqtt_mock)[count:]))
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(("option", "value"), [
    ("weatherIcons", "colour"), ("weatherPictureBase", "26"), ("weatherPictureBase", -1),
    ("timeTemplate", ""), ("largeIconFontId", 10),
])
def test_invalid_firmware_55_options(tmp_path: Path, option, value) -> None:
    from custom_components.nspanel_lovelace_ui.config import ConfigError

    config = yaml.safe_load((Path(__file__).parent / "fixtures" / "panels.yaml").read_text(encoding="utf-8"))
    config["nspanels"]["living_room"][option] = value
    path = tmp_path / "panels.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ConfigError, match=option):
        load_config(path)
