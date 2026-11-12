"""Actions sleep_screen / wake_screen and the Screen switch (automations, e.g. alarm armed -> screen off)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.nspanel_lovelace_ui.const import DOMAIN

from .conftest import published, wait_for
from .test_entities import _entity, _recv, _setup, _unload

# Fixture panel: sleepBrightness 10, screenBrightness 100 -> "dimmode~10~100~…"


def _dimmodes(mqtt_mock, start: int = 0) -> list[str]:
    return [p for p in published(mqtt_mock)[start:] if p.startswith("dimmode~")]


async def test_sleep_screen_and_touch(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    entry = await _setup(hass, mqtt_mock)
    switch = _entity(hass, "switch")
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")  # a card is shown
    await wait_for(hass, lambda: hass.states.get(switch).state == "on")

    count = len(published(mqtt_mock))
    await hass.services.async_call(DOMAIN, "sleep_screen", {}, blocking=True)
    # Brightness first (the screensaver applies it when it opens), then the screensaver.
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock)[count:])
    sent = published(mqtt_mock)[count:]
    assert _dimmodes(mqtt_mock, count)[0].startswith("dimmode~0~100~")
    assert sent.index(_dimmodes(mqtt_mock, count)[0]) < sent.index("pageType~screensaver")
    await wait_for(hass, lambda: hass.states.get(switch).state == "off")

    # The panel keeps the forced brightness (e.g. on the minute tick) until it is woken.
    count = len(published(mqtt_mock))
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")  # a touch
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[count:]
                   and any(d.startswith("dimmode~10~100~") for d in _dimmodes(mqtt_mock, count)))
    await wait_for(hass, lambda: hass.states.get(switch).state == "on")
    await _unload(hass, entry)


async def test_wake_screen_action_and_switch(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    config["nspanels"]["living_room"]["screensaver"]["doubleTapToUnlock"] = True  # wake still works
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    entry = await _setup(hass, mqtt_mock)
    switch = _entity(hass, "switch")
    await wait_for(hass, lambda: hass.states.get(switch).state == "off")  # screensaver after startup

    count = len(published(mqtt_mock))
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await wait_for(hass, lambda: any(d.startswith("dimmode~0~") for d in _dimmodes(mqtt_mock, count)))
    assert "pageType~screensaver" not in published(mqtt_mock)[count:]  # already on the screensaver

    count = len(published(mqtt_mock))
    await hass.services.async_call(DOMAIN, "wake_screen", {"panel": "living_room"}, blocking=True)
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[count:]
                   and any(d.startswith("dimmode~10~100~") for d in _dimmodes(mqtt_mock, count)))
    await wait_for(hass, lambda: hass.states.get(switch).state == "on")

    count = len(published(mqtt_mock))
    await hass.services.async_call(DOMAIN, "sleep_screen", {"brightness": 30}, blocking=True)
    await wait_for(hass, lambda: "pageType~screensaver" in published(mqtt_mock)[count:])
    assert _dimmodes(mqtt_mock, count)[0].startswith("dimmode~30~100~")
    count = len(published(mqtt_mock))
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    await wait_for(hass, lambda: "pageType~cardEntities" in published(mqtt_mock)[count:])

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "wake_screen", {"panel": "nope"}, blocking=True)
    with pytest.raises(Exception):  # noqa: B017 - voluptuous range error
        await hass.services.async_call(DOMAIN, "sleep_screen", {"brightness": 150}, blocking=True)
    await _unload(hass, entry)
