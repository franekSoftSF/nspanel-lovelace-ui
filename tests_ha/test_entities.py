"""Panel entities (notify, wake button, page sensor, card select), the notify action and diagnostics."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN
from custom_components.nspanel_lovelace_ui.diagnostics import async_get_config_entry_diagnostics

from .conftest import RECV, published, wait_for


def _recv(hass: HomeAssistant, message: str) -> None:
    async_fire_mqtt_message(hass, RECV, json.dumps({"CustomRecv": message}))


def _entity(hass: HomeAssistant, domain: str) -> str:
    entity_id = next(e.entity_id for e in er.async_get(hass).entities.values()
                     if e.platform == DOMAIN and e.domain == domain)
    return entity_id


async def _setup(hass: HomeAssistant, mqtt_mock) -> MockConfigEntry:
    hass.states.async_set("light.bed_light", "off", {"friendly_name": "Lampka"})
    hass.states.async_set("switch.decorative_lights", "on", {"friendly_name": "Dekor"})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    await wait_for(hass, lambda: "pageType~pageStartup" in published(mqtt_mock))
    _recv(hass, "event,startup,55,eu")
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock))
    await hass.async_block_till_done()
    return entry


async def _unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities_follow_the_page(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    sensor, select = _entity(hass, "sensor"), _entity(hass, "select")
    await wait_for(hass, lambda: hass.states.get(sensor).state == "screensaver")
    assert "Salon" in hass.states.get(select).attributes["options"]

    _recv(hass, "event,buttonPress2,screensaver,bExit,1")  # touch: first card
    await wait_for(hass, lambda: hass.states.get(sensor).state == "Salon")
    assert hass.states.get(sensor).attributes["card_type"] == "cardEntities"
    assert hass.states.get(select).state == "Salon"
    await _unload(hass, entry)


async def test_select_shows_a_card(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    select = _entity(hass, "select")
    await wait_for(hass, lambda: "Salon" in hass.states.get(select).attributes["options"])
    count = len(published(mqtt_mock))
    await hass.services.async_call("select", "select_option", {"entity_id": select, "option": "Salon"}, blocking=True)
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[count:])
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("select", "select_option", {"entity_id": select, "option": "Nope"},
                                       blocking=True)
    await _unload(hass, entry)


async def test_notify_entity_and_wake_button(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    await wait_for(hass, lambda: hass.states.get(_entity(hass, "sensor")).state == "screensaver")
    await hass.services.async_call("notify", "send_message", {
        "entity_id": _entity(hass, "notify"), "title": "Garaż", "message": "Brama~otwarta"}, blocking=True)
    await wait_for(hass, lambda: "notify~Garaż~Brama-otwarta" in published(mqtt_mock))  # '~' would split fields

    # Wake up = a touch on the screensaver: the panel switches to its card (brightness from pageType).
    count = len(published(mqtt_mock))
    await hass.services.async_call("button", "press", {"entity_id": _entity(hass, "button")}, blocking=True)
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[count:])
    sensor = _entity(hass, "sensor")
    await wait_for(hass, lambda: hass.states.get(sensor).state == "Salon")
    # On a card the screen is awake: nothing is sent.
    count = len(published(mqtt_mock))
    await hass.services.async_call("button", "press", {"entity_id": _entity(hass, "button")}, blocking=True)
    await hass.async_block_till_done()
    assert not any(p.startswith("pageType~") for p in published(mqtt_mock)[count:])
    await _unload(hass, entry)


async def test_notify_action_popup_returns_to_the_card(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    count = len(published(mqtt_mock))
    await hass.services.async_call(DOMAIN, "notify", {
        "message": "Pralka skończyła", "title": "Pranie", "mode": "popup", "timeout": 30, "buzzer": True},
        blocking=True)
    await wait_for(hass, lambda: "pageType~popupNotify" in published(mqtt_mock)[count:] and any(
        p.startswith("entityUpdateDetail~nspanelNotify") for p in published(mqtt_mock)[count:]))
    detail = next(p for p in published(mqtt_mock)[count:] if p.startswith("entityUpdateDetail~nspanelNotify"))
    assert detail.split("~")[2] == "Pranie" and detail.split("~")[8] == "Pralka skończyła"
    assert detail.endswith("~30")
    assert published(mqtt_mock, "cmnd/nspanel_test/Buzzer") == ["2,2,2"]

    count = len(published(mqtt_mock))
    _recv(hass, "event,buttonPress2,nspanelNotify,bExit")  # close: back to the page before
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock)[count:])

    await hass.services.async_call(DOMAIN, "notify", {"mode": "clear"}, blocking=True)
    await wait_for(hass, lambda: "notify~~" in published(mqtt_mock))
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "notify", {"mode": "popup"}, blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "notify", {"message": "x", "panel": "nope"}, blocking=True)
    await _unload(hass, entry)


async def test_diagnostics(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    data = await async_get_config_entry_diagnostics(hass, entry)
    panel = data["panels"]["living_room"]
    assert panel["display"] == {"version": 55, "model": "eu"}
    assert panel["worker_started"] is True and panel["cards"] >= 1
    assert data["firmware_package"] is None
    await _unload(hass, entry)
