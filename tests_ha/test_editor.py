"""Card editor: shared schema (every card type), validation issues and the websocket API."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import re
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nspanel_lovelace_ui import editor_schema
from custom_components.nspanel_lovelace_ui.backend import config_manager, ha_cards, ha_icons
from custom_components.nspanel_lovelace_ui.backend.libs import icon_mapping
from custom_components.nspanel_lovelace_ui.backend.config_schema import (
    CARD_TYPES, CARDS, GLOBAL_FIELDS, ITEM_FIELDS, MESSAGES, PANEL_FIELDS, SCREENSAVER_FIELDS, collect_issues,
    schema_json,
)
from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN

from .conftest import FIXTURES

ROOT = Path(__file__).resolve().parents[1]


# --- schema: one source of truth --------------------------------------------------------------

def test_every_backend_card_type_has_an_editor() -> None:
    """card_factory (what the panels can show) == validator == editor forms."""
    source = inspect.getsource(ha_cards.card_factory)
    implemented = set(re.findall(r"'(card\w+)'", source))
    assert implemented == set(CARD_TYPES) == set(CARDS)
    assert config_manager.CARD_TYPES is CARD_TYPES  # the validator uses the same list
    for card_type, spec in CARDS.items():
        assert spec["fields"], card_type
        assert {"en", "pl"} <= set(spec["label"]), card_type


def test_every_label_and_message_is_translated() -> None:
    def walk(fields):
        for spec in fields:
            yield spec
    fields = [*GLOBAL_FIELDS, *PANEL_FIELDS, *SCREENSAVER_FIELDS, *ITEM_FIELDS]
    for spec in CARDS.values():
        fields += spec["fields"]
    for spec in walk(fields):
        for text in [spec["label"], spec.get("help")] + [o["label"] for o in spec.get("options", [])]:
            if text is not None:
                assert text["en"].strip() and text["pl"].strip(), spec["key"]
    for code, text in MESSAGES.items():
        assert text["en"] and text["pl"], code
        assert set(re.findall(r"{(\w+)}", text["en"])) == set(re.findall(r"{(\w+)}", text["pl"])), code
    schema = schema_json()
    assert schema["card_types"] == CARD_TYPES and set(schema["cards"]) == set(CARDS)


def _codes(config, entity_ids=None):
    return {(tuple(i.path), i.code, i.severity) for i in collect_issues(config, entity_ids)}


def _panel(**extra):
    panel = {"panelRecvTopic": "tele/p/RESULT", "panelSendTopic": "cmnd/p/CustomSend", "locale": "pl_PL",
             "timeFormat": "%H:%M", "dateFormat": "full", "screensaver": {"entities": []},
             "cards": [{"type": "cardEntities", "title": "A", "entities": [{"entity": "light.a"}]}]}
    panel.update(extra)
    return {"nspanels": {"p": panel}}


@pytest.mark.parametrize("path", [FIXTURES / "panels.yaml", ROOT / "examples" / "panels.yaml"])
def test_known_configurations_are_valid(path: Path) -> None:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert [i.text() for i in collect_issues(config) if i.severity == "error"] == []


def test_issues_point_at_the_field() -> None:
    p = ("nspanels", "p")
    config = _panel(panelRecvTopic="tele/+/RESULT", sleepBrightness=[{"time": "25:00", "value": 5}],
                    weatherIcons="colour", defaultCard="navigate.nope")
    config["nspanels"]["p"]["cards"] += [
        {"type": "cardThermo"},
        {"type": "cardGrid2"},
        {"type": "cardUnlock", "pin": 1234, "destination": "navigate.missing"},
        {"type": "cardEntities", "entities": [{"entity": "not an id"}, {"entity": "navigate.x"}, {"name": "x"}]},
    ]
    codes = _codes(config)
    assert (p + ("panelRecvTopic",), "topic_wildcard", "error") in codes
    assert (p + ("sleepBrightness",), "brightness", "error") in codes
    assert (p + ("weatherIcons",), "one_of", "error") in codes
    assert (p + ("defaultCard",), "navigate_missing", "warning") in codes
    assert (p + ("cards", 1, "entity"), "required", "error") in codes
    assert (p + ("cards", 2, "type"), "unknown_card_type", "error") in codes
    assert (p + ("cards", 3, "destination"), "navigate_missing", "warning") in codes
    assert not any(path == p + ("cards", 3, "pin") for path, _, _ in codes)  # pin: 1234 (int) is fine
    assert (p + ("cards", 4, "entities", 0, "entity"), "entity_format", "error") in codes
    assert (p + ("cards", 4, "entities", 1, "entity"), "navigate_missing", "warning") in codes
    assert (p + ("cards", 4, "entities", 2, "entity"), "required", "error") in codes


def test_missing_entities_are_warnings_only() -> None:
    config = _panel()
    config["nspanels"]["p"]["cards"].append({"type": "cardMedia", "entity": "light.a"})
    issues = collect_issues(config, entity_ids={"light.a"})
    assert all(i.severity == "warning" for i in issues)
    assert {i.code for i in issues} == {"entity_domain"}  # light.a exists but is no media_player
    issues = collect_issues(_panel(), entity_ids=set())
    assert [(i.code, i.severity) for i in issues] == [("entity_missing", "warning")]


def test_loader_uses_the_same_schema(tmp_path: Path) -> None:
    from custom_components.nspanel_lovelace_ui.config import ConfigError, load_config
    path = tmp_path / "panels.yaml"
    path.write_text(yaml.safe_dump(_panel(largeIconFontId=12)), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"p\.largeIconFontId"):
        load_config(path)


# --- websocket API ---------------------------------------------------------------------------

@pytest.fixture
async def editor(hass: HomeAssistant, mqtt_mock, panels_file: Path, hass_ws_client):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    ids = iter(range(1, 1000))

    async def call(command, **data):
        await client.send_json({"id": next(ids), "type": f"{DOMAIN}/editor/{command}", **data})
        return await client.receive_json()

    yield call
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_load_schema_icons(editor, panels_file: Path) -> None:
    loaded = (await editor("load"))["result"]
    assert loaded["exists"] and loaded["config"]["nspanels"]["living_room"]["cards"]
    assert loaded["path"] == DEFAULT_CONFIG_FILE and len(loaded["revision"]) == 64
    schema = (await editor("schema"))["result"]
    assert schema["card_types"] == CARD_TYPES
    picker = (await editor("icons"))["result"]
    names = {row[0] for row in picker["icons"]}
    assert "lightbulb" in names and len(names) > 5000 and picker["mdi"] == "7.4.47"
    lamp = next(row for row in picker["icons"] if row[0] == "lamp")
    assert "Home Automation" in [picker["tags"][index] for index in lamp[2]]


def test_icon_picker_offers_exactly_the_panel_font() -> None:
    """Picker rows = icons in the panel font (same MDI metadata as the font and the mapping)."""
    picker = editor_schema.icon_picker()
    names = [row[0] for row in picker["icons"]]
    font = [entry["name"] for entry in json.loads((ROOT / "HMI" / "code_gen" / "icons" / "icons.json").read_text())]
    assert sorted(names) == sorted(font) and len(set(names)) == len(names)
    for name, aliases, tags, *flags in picker["icons"]:
        assert name in icon_mapping.icons, name
        assert all(alias in icon_mapping.icons for alias in aliases.split()), name
        assert all(0 <= tag < len(picker["tags"]) for tag in tags) and flags in ([], [1]), name


def test_editor_translates_every_icon_category() -> None:
    source = (ROOT / "custom_components" / DOMAIN / "frontend" / "nspanel-editor.js").read_text(encoding="utf-8")
    block = source[source.index("const ICON_TAGS_PL = {"):]
    block = block[:block.index("};")]
    translated = set(re.findall(r'"([^"]+)":', block))
    assert translated == set(editor_schema.icon_picker()["tags"])


def test_unknown_icons_are_warnings() -> None:
    rows = ("nspanels", "p", "cards", 0, "entities")
    config = _panel(cards=[{"type": "cardEntities", "entities": [
        {"entity": "light.a", "icon": "mdi:lightbulb"}, {"entity": "light.b", "icon": "lamp"},
        {"entity": "light.c", "icon": "mdi:lecturn"},  # alias of lectern
        {"entity": "light.d", "icon": "mdi:google-home"},  # removed from MDI 7
        {"entity": "light.e", "icon": "ha:{{ 'x' }}"}, {"entity": "light.f", "icon": "text:A"},
        {"entity": "light.g", "icon": {"on": "mdi:lightbulb-on", "off": "mdi:nope"}}]}])
    issues = [(tuple(i.path), i.severity) for i in collect_issues(config) if i.code == "icon_unknown"]
    assert issues == [((*rows, 3, "icon"), "warning"), ((*rows, 6, "icon", "off"), "warning")]
    config_manager.validate(config)  # only warnings: the panel still loads


async def test_default_icons_follow_the_cards(hass: HomeAssistant, editor) -> None:
    hass.states.async_set("switch.mirror", "off")
    hass.states.async_set("cover.shutter", "closed", {"device_class": "shutter"})
    hass.states.async_set("binary_sensor.door", "on", {"device_class": "door"})
    hass.states.async_set("sensor.temp", "21", {"device_class": "temperature"})
    entities = ["switch.mirror", "cover.shutter", "binary_sensor.door", "sensor.temp", "light.missing",
                "navigate.lights", "iText.x", "service.light.toggle", "delete"]
    icons = (await editor("default_icons", entities=entities))["result"]["icons"]
    assert icons == {"switch.mirror": "light-switch", "cover.shutter": "window-shutter", "binary_sensor.door": "door-open",
                     "sensor.temp": "thermometer", "light.missing": None, "navigate.lights": "gesture-tap-button",
                     "iText.x": "gesture-tap-button", "service.light.toggle": "script-text", "delete": None}
    # The cards use the same rules.
    assert ha_icons.get_icon_ha("cover", "closed", "shutter") == icon_mapping.icons["window-shutter"]
    assert ha_icons.get_icon_ha("cover", "closed", "shutter", overwrite="mdi:lamp") == icon_mapping.icons["lamp"]


async def test_validate_save_backup_and_conflict(editor, panels_file: Path) -> None:
    loaded = (await editor("load"))["result"]
    config = loaded["config"]
    config["nspanels"]["living_room"]["cards"][0]["title"] = "Kuchnia"

    bad = yaml.safe_load(yaml.safe_dump(config))
    bad["nspanels"]["living_room"]["sleepTimeout"] = -1
    issues = (await editor("validate", config=bad))["result"]["issues"]
    assert any(i["path"][-1] == "sleepTimeout" and i["severity"] == "error" for i in issues)
    result = (await editor("save", config=bad, revision=loaded["revision"]))["result"]
    assert result == {"saved": False, "reason": "invalid", "issues": result["issues"]}
    assert "Kuchnia" not in panels_file.read_text(encoding="utf-8")  # server-side check, nothing written

    before = panels_file.read_text(encoding="utf-8")
    result = (await editor("save", config=config, revision=loaded["revision"]))["result"]
    assert result["saved"] is True
    assert yaml.safe_load(panels_file.read_text(encoding="utf-8"))["nspanels"]["living_room"]["cards"][0]["title"] == "Kuchnia"
    assert panels_file.with_name("panels.yaml.bak").read_text(encoding="utf-8") == before
    assert list((panels_file.parent / ".nspanel-backups").glob("panels.yaml.*"))

    # Changed on disk after loading: conflict, unless forced.
    panels_file.write_text(panels_file.read_text(encoding="utf-8") + "\n# edited by hand\n", encoding="utf-8")
    config["nspanels"]["living_room"]["cards"][0]["title"] = "Salon 2"
    result = (await editor("save", config=config, revision=result["revision"]))["result"]
    assert result == {"saved": False, "reason": "conflict"}
    assert "edited by hand" in panels_file.read_text(encoding="utf-8")
    result = (await editor("save", config=config, revision=None, force=True))["result"]
    assert result["saved"] is True and "Salon 2" in panels_file.read_text(encoding="utf-8")


async def test_yaml_and_reload(editor, panels_file: Path) -> None:
    text = (await editor("yaml", config={"nspanels": {}}))["result"]["yaml"]
    assert "nspanels: {}" in text
    parsed = (await editor("yaml", yaml="nspanels:\n  a: {cards: []}\n"))["result"]
    assert parsed["config"] == {"nspanels": {"a": {"cards": []}}}
    error = await editor("yaml", yaml="nspanels: [\n")
    assert error["success"] is False and error["error"]["code"] == "invalid_yaml"
    reloaded = (await editor("reload"))["result"]
    assert reloaded["reloaded"] is True and reloaded["state"] == "loaded"


async def test_editor_is_admin_only(hass: HomeAssistant, mqtt_mock, panels_file: Path, hass_ws_client,
                                    hass_read_only_access_token) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/editor/load"})
    response = await client.receive_json()
    assert response["success"] is False and response["error"]["code"] == "unauthorized"
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_editor_works_while_the_configuration_is_broken(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                                              hass_ws_client) -> None:
    panels_file.write_text("nspanels:\n  p: {cards: []}\n", encoding="utf-8")
    hass.config.components.add("frontend")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    with patch("custom_components.nspanel_lovelace_ui.editor.panel_custom.async_register_panel",
               new=AsyncMock()) as register:
        assert not await hass.config_entries.async_setup(entry.entry_id)  # invalid file
    assert register.await_args.kwargs["require_admin"] is True
    assert register.await_args.kwargs["frontend_url_path"] == "nspanel-lovelace-ui"
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": f"{DOMAIN}/editor/load"})
    loaded = (await client.receive_json())["result"]
    assert any(i["code"] == "required" and i["path"][-1] == "panelRecvTopic" for i in loaded["issues"])
