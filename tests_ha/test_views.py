"""Cards and popups against the display code (HMI/n2t-out/*.txt): field positions and the fixes from the
protocol check (fan speed, timer, closing popups, layouts that only grow, option lists, PIN, open sensors)."""
from __future__ import annotations

from pathlib import Path
import queue
import threading
from unittest.mock import patch

import pytest
import yaml

from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.nspanel_lovelace_ui.backend import ha_cards
from custom_components.nspanel_lovelace_ui.backend.libs import home_assistant as bridge

from .conftest import published, wait_for
from .test_entities import _recv, _setup, _unload


def _detail(detail_type: str, entity_id: str, state: str, attributes: dict, **kwargs) -> list[str]:
    """detail_open with a fake entity; returns the fields after "entityUpdateDetail" (index 1 = name)."""
    data = {"state": state, "attributes": attributes}
    with patch.object(bridge, "get_entity_data", return_value=data):
        payload = ha_cards.detail_open("en_US", detail_type, entity_id, "iid.x", queue.Queue(), **kwargs)
    return ["entityUpdateDetail", *payload.split("~")]


# --- popups (pure payloads) --------------------------------------------------------------------

@pytest.mark.parametrize(("state", "attributes", "minutes", "seconds", "editable", "actions"), [
    ("idle", {"duration": "1:30:00"}, "90", "0", "1", ["", "start", ""]),        # hours were dropped
    ("paused", {"duration": "0:10:00", "remaining": "0:04:05"}, "4", "5", "0", ["cancel", "start", "finish"]),
    ("unavailable", {}, "0", "0", "0", ["", "", ""]),                              # crashed before
    ("active", {"duration": "0:10:00"}, "0", "0", "0", ["", "", ""]),             # no finishes_at
])
def test_timer_popup(state, attributes, minutes, seconds, editable, actions) -> None:
    before = threading.active_count()
    fields = _detail("popupTimer", "timer.tea", state, attributes)
    # popupTimer.txt: 1 name, 4 name again, 5/6 min/sec (covx), 7 editable, 8-10 actions, 11-13 labels
    assert len(fields) == 14 and fields[1] == fields[4] == "iid.x"
    assert fields[5:8] == [minutes, seconds, editable] and fields[8:11] == actions
    assert threading.active_count() == before  # no refresh thread any more


def test_timer_popup_counts_down_from_finishes_at() -> None:
    from homeassistant.util import dt as dt_util
    from datetime import timedelta
    finishes = (dt_util.utcnow() + timedelta(hours=1, minutes=2, seconds=30)).isoformat()
    fields = _detail("popupTimer", "timer.tea", "active", {"finishes_at": finishes})
    assert fields[5] in ("62", "61") and fields[8:11] == ["pause", "cancel", "finish"]


def test_cover_popup() -> None:
    # popupShutter.txt: 2 position slider ("disable" hides), 5 icon, 9-11 up/stop/down, 19 tilt slider
    no_position = _detail("popupShutter", "cover.gate", "open", {"current_position": 40, "supported_features": 1 | 2 | 8})
    assert len(no_position) == 20 and no_position[2] == "disable" and no_position[9:12] == ["enable", "enable", "enable"]
    full = _detail("popupShutter", "cover.blind", "open", {"current_position": 40, "supported_features": 15 | 128,
                                                           "current_tilt_position": None})
    assert full[2] == "40" and full[19] == "disable"
    assert len(_detail("popupShutter", "cover.x", "unknown", {})) == 20  # no supported_features: no crash


def test_option_lists_survive_separators_and_size() -> None:
    options = ["Ready?", "A~B", "x" * 30] + [f"option {i}" for i in range(200)]
    fields = _detail("popupInSel", "input_select.mode", "A~B", {"options": options})
    # popupInSel.txt: 4 type, 5 current, 6 "?"-separated list (vaModeList 900, strCommand 960)
    assert fields[4] == "input_select" and fields[5] == "A-B"
    listed = fields[6].split("?")
    assert listed[:3] == ["Ready", "A-B", "x" * 30] and len(fields[6].encode()) <= 850
    assert len("~".join(fields).encode()) < 960


def test_thermo_and_fan_popups() -> None:
    attributes = {"preset_modes": ["eco", "comfort"], "preset_mode": None, "fan_modes": ["auto", "low?"],
                  "fan_mode": "auto", "swing_modes": None}
    fields = _detail("popupThermo", "climate.x", "heat", attributes)
    # popupThermo.txt: 4-7 first group (heading, type, current, list), 8-11 second group
    assert fields[5] == "preset_modes" and fields[6] == "" and fields[9] == "fan_modes" and fields[11] == "auto?low"
    fan = _detail("popupFan", "fan.x", "on", {"percentage": 66, "percentage_step": 100 / 3, "preset_mode": None})
    # popupFan.txt: 5 speed step, 6 hSpeed.maxval, 8 current preset, 9 presets
    assert fan[5:7] == ["2", "3"] and fan[8] == ""


# --- actions and pages on a running panel ------------------------------------------------------

def _write(panels_file: Path, cards: list[dict]) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    config["nspanels"]["living_room"]["cards"] = cards
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


def _calls(hass: HomeAssistant, domain: str, service: str) -> list[ServiceCall]:
    calls: list[ServiceCall] = []
    hass.services.async_register(domain, service, calls.append)
    return calls


async def _open_first_card(hass: HomeAssistant, mqtt_mock, page: str) -> None:
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")
    await wait_for(hass, lambda: f"pageType~{page}" in published(mqtt_mock))


async def test_closing_a_popup_returns_to_its_card(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardEntities", "title": "A", "entities": [{"entity": "light.bed_light"}]},
                         {"type": "cardEntities", "title": "B", "entities": [{"entity": "light.bed_light"}]}])
    entry = await _setup(hass, mqtt_mock)
    await _open_first_card(hass, mqtt_mock, "cardEntities")
    runtime = entry.runtime_data
    card_b = next(c for c in runtime.cards("living_room") if c["title"] == "B")
    runtime.async_navigate("living_room", card_b["iid"])
    await wait_for(hass, lambda: hass.states.get("sensor.nspanel_living_room_page").state == "B")
    _recv(hass, "event,pageOpenDetail,popupLight,light.bed_light")
    _recv(hass, "event,buttonPress2,popupLight,bExit")
    count = len(published(mqtt_mock))
    await wait_for(hass, lambda: any(p.startswith("entityUpd~B~") for p in published(mqtt_mock)[count:]))
    assert hass.states.get("sensor.nspanel_living_room_page").state == "B"  # it went to A before
    await _unload(hass, entry)


async def test_fan_speed_and_invalid_mode_buttons(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    hass.states.async_set("fan.ceiling", "on", {"percentage": 33, "percentage_step": 100 / 3})
    hass.states.async_set("climate.room", "heat", {"fan_modes": ["auto", "low"], "fan_mode": "auto"})
    entry = await _setup(hass, mqtt_mock)
    percentage = _calls(hass, "fan", "set_percentage")
    fan_mode = _calls(hass, "climate", "set_fan_mode")
    _recv(hass, "event,buttonPress2,fan.ceiling,number-set,2")  # popupFan speed slider: step 2 of 3
    _recv(hass, "event,buttonPress2,climate.room,mode-fan_modes,2")  # an empty third button
    _recv(hass, "event,buttonPress2,climate.room,mode-fan_modes,1")
    await wait_for(hass, lambda: percentage and fan_mode)
    assert percentage[0].data["percentage"] == 67 and [c.data["fan_mode"] for c in fan_mode] == ["low"]
    await _unload(hass, entry)


async def test_media_card(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardMedia", "title": "TV", "entity": "media_player.tv"}])
    hass.states.async_set("media_player.tv", "playing", {
        "media_title": "Part~1", "media_artist": "X", "volume_level": 0.5, "shuffle": False,
        "supported_features": 32768 | 256 | 16384})
    entry = await _setup(hass, mqtt_mock)
    shuffle = _calls(hass, "media_player", "shuffle_set")
    await _open_first_card(hass, mqtt_mock, "cardMedia")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~TV~") for p in published(mqtt_mock)))
    fields = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~TV~")).split("~")
    # cardMedia.txt: 14 entity, 15 title, 17 author, 19 volume, 21 on/off colour, 22 shuffle icon, 23.. items
    assert fields[14] == "media_player.tv" and fields[15] == "Part-1" and fields[19] == "50"
    assert fields[21] != "disable" and fields[22] != "disable"
    _recv(hass, "event,buttonPress2,media_player.tv,media-shuffle")
    await wait_for(hass, lambda: shuffle)
    assert shuffle[0].data["shuffle"] is True
    await _unload(hass, entry)


async def test_alarm_buttons_restart_the_page_and_open_sensors(hass: HomeAssistant, mqtt_mock,
                                                                    panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardAlarm", "title": "Alarm", "entity": "alarm_control_panel.home"}])
    hass.states.async_set("alarm_control_panel.home", "disarmed", {"supported_features": 1 | 2 | 4,
                                                                   "open_sensors": ["binary_sensor.window"]})
    hass.states.async_set("binary_sensor.window", "on", {"friendly_name": "Okno kuchnia"})
    entry = await _setup(hass, mqtt_mock)
    await _open_first_card(hass, mqtt_mock, "cardAlarm")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Alarm~") for p in published(mqtt_mock)))
    first = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~Alarm~")).split("~")
    # cardAlarm.txt: 15-22 four arm buttons (text, mode), 27 open sensors button icon
    assert [first[i] for i in (16, 18, 20)] == ["arm_home", "arm_away", "arm_night"] and first[27]
    count = len(published(mqtt_mock))
    hass.states.async_set("alarm_control_panel.home", "armed_away", {"supported_features": 1 | 2 | 4})
    # Fewer buttons: the display only shows them on an update, so the page opens again first.
    await wait_for(hass, lambda: "pageType~cardAlarm" in published(mqtt_mock)[count:])
    count = len(published(mqtt_mock))
    hass.states.async_set("alarm_control_panel.home", "armed_away", {"supported_features": 1 | 2 | 4, "x": 1})
    await hass.async_block_till_done()
    assert "pageType~cardAlarm" not in published(mqtt_mock)[count:]  # same layout: a plain update

    hass.states.async_set("alarm_control_panel.home", "disarmed", {"supported_features": 1 | 2 | 4,
                                                                   "open_sensors": ["binary_sensor.window"]})
    count = len(published(mqtt_mock))
    _recv(hass, "event,buttonPress2,alarm_control_panel.home,opnSensorNotify")
    await wait_for(hass, lambda: any(p.startswith("entityUpdateDetail~nspanelNotify") for p in published(mqtt_mock)[count:]))
    assert "pageType~popupNotify" in published(mqtt_mock)[count:]
    detail = next(p for p in published(mqtt_mock)[count:] if p.startswith("entityUpdateDetail~nspanelNotify"))
    assert "Okno kuchnia" in detail
    await _unload(hass, entry)


async def test_thermostat_dual_set_point_restarts_the_page(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardThermo", "title": "Grzanie", "entity": "climate.room"}])
    base = {"hvac_modes": ["heat", "heat_cool"], "min_temp": 7, "max_temp": 35, "current_temperature": None}
    hass.states.async_set("climate.room", "heat_cool", {**base, "target_temp_low": 19, "target_temp_high": 23})
    entry = await _setup(hass, mqtt_mock)
    await _open_first_card(hass, mqtt_mock, "cardThermo")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Grzanie~") for p in published(mqtt_mock)))
    fields = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~Grzanie~")).split("~")
    # cardThermo.txt: 15 current temperature, 16 set point (×10), 57 low set point ("" = single)
    assert fields[15].startswith(" ") and fields[16] == "230" and fields[57] == "190"
    count = len(published(mqtt_mock))
    hass.states.async_set("climate.room", "heat", {**base, "temperature": 21})
    await wait_for(hass, lambda: "pageType~cardThermo" in published(mqtt_mock)[count:])
    await _unload(hass, entry)


async def test_power_card_keeps_hidden_items_in_place(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardPower", "title": "Energia", "entities": [
        {"entity": "sensor.home"}, {"entity": "sensor.grid", "state": "on"}, {"entity": "sensor.solar", "speed": 5}]}])
    for entity, state in (("sensor.home", "1"), ("sensor.grid", "2"), ("sensor.solar", "3")):
        hass.states.async_set(entity, state)
    entry = await _setup(hass, mqtt_mock)
    await _open_first_card(hass, mqtt_mock, "cardPower")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Energia~") for p in published(mqtt_mock)))
    fields = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~Energia~")).split("~")
    # cardPower.txt: items of 7 fields from 14 (type, id, icon, colour, name, value, speed); the hidden
    # second item keeps its 7 fields, so the third one still starts at 28 (value 33, speed 34)
    assert fields[21] == "delete" and fields[28] == "text" and fields[33].startswith("3") and fields[34] == "5"
    await _unload(hass, entry)


async def test_unlock_pin_is_compared_as_text(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    _write(panels_file, [{"type": "cardUnlock", "title": "PIN", "pin": "0123", "destination": "navigate.secret"},
                         {"type": "cardEntities", "title": "Secret", "key": "secret",
                          "entities": [{"entity": "light.bed_light"}]}])
    entry = await _setup(hass, mqtt_mock)
    await _open_first_card(hass, mqtt_mock, "cardAlarm")  # cardUnlock uses the cardAlarm page
    secret = next(c for c in entry.runtime_data.cards("living_room") if c["title"] == "Secret")
    for wrong in ("123", ""):
        _recv(hass, f"event,buttonPress2,navigate.{secret['iid']},cardUnlock-unlock,{wrong}")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.nspanel_living_room_page").state == "PIN"
    _recv(hass, f"event,buttonPress2,navigate.{secret['iid']},cardUnlock-unlock,0123")
    await wait_for(hass, lambda: hass.states.get("sensor.nspanel_living_room_page").state == "Secret")
    await _unload(hass, entry)
