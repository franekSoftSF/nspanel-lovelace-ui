"""cardQR Wi-Fi mode: WIFI: strings (escaping, parsing, redaction), validation, secrets, panel and editor."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import yaml

from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.nspanel_lovelace_ui.backend import config_manager, wifi
from custom_components.nspanel_lovelace_ui.backend.config_schema import collect_issues
from custom_components.nspanel_lovelace_ui.config import load_config
from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN

from .conftest import RECV, published, wait_for

NAMES = ("Sieć", "Hasło")  # the fixture panel is pl_PL


# --- WIFI: strings ------------------------------------------------------------------------------

@pytest.mark.parametrize(("ssid", "password", "expected"), [
    ("Dom", "haslo1234", "WIFI:T:WPA;S:Dom;P:haslo1234;;"),
    ('a\\b;c,d:e"f', 'p;a,s:s"w\\d', 'WIFI:T:WPA;S:a\\\\b\\;c\\,d\\:e\\"f;P:p\\;a\\,s\\:s\\"w\\\\d;;'),
    ("Kawiarnia Żółw", "zażółć gęślą", "WIFI:T:WPA;S:Kawiarnia Żółw;P:zażółć gęślą;;"),
])
def test_build_escapes_special_characters(ssid: str, password: str, expected: str) -> None:
    assert wifi.build(ssid, "WPA", password) == expected
    assert wifi.parse(expected) == {"ssid": ssid, "security": "WPA", "password": password}


def test_build_options() -> None:
    assert wifi.build("Gość", "nopass", "ignored") == "WIFI:T:nopass;S:Gość;;"
    assert wifi.build("Ukryta", "WEP", "abcde", hidden=True) == "WIFI:T:WEP;S:Ukryta;P:abcde;H:true;;"
    assert wifi.build("X", "bogus", "") == "WIFI:T:WPA;S:X;;"  # unknown type -> WPA, no empty P


def test_parse_any_order_and_types() -> None:
    assert wifi.parse("WIFI:S:MyNet;T:WPA2;P:secret12;H:true;;") == {
        "ssid": "MyNet", "security": "WPA", "password": "secret12", "hidden": True}
    assert wifi.parse("WIFI:S:Open;;") == {"ssid": "Open", "security": "nopass"}
    assert wifi.parse("WIFI:T:WEP;S:Old;P:12345;;")["security"] == "WEP"
    assert wifi.parse("https://example.com") is None
    assert wifi.parse("WIFI:T:WPA;P:x;;") is None  # no SSID
    assert wifi.parse(None) is None


def test_redact_hides_only_the_password() -> None:
    message = "entityUpd~Gość~~WIFI:T:WPA;S:Dom\\;P\\:x;P:se\\;cret12;;~text~iText.wifi_ssid~X~1~Sieć~Dom"
    redacted = wifi.redact(message)
    assert "se\\;cret12" not in redacted and "cret12" not in redacted
    assert redacted == "entityUpd~Gość~~WIFI:T:WPA;S:Dom\\;P\\:x;P:***;;~text~iText.wifi_ssid~X~1~Sieć~Dom"
    assert wifi.redact("entityUpd~A~~https://x") == "entityUpd~A~~https://x"
    row = "~text~iText.wifi_password~K~1~Hasło~tajne"
    assert wifi.redact("entityUpd~A~~WIFI:T:WPA;S:D;P:tajne;;" + row).endswith("~Hasło~***")


@pytest.mark.parametrize(("security", "password", "problem"), [
    ("WPA", "1234567", "wifi_wpa_length"), ("WPA", "12345678", None), ("WPA", "x" * 63, None),
    ("WPA", "x" * 64, "wifi_wpa_length"), ("WPA", "a1" * 32, None),  # 64 hex digits = raw key
    ("WEP", "abcde", None), ("WEP", "abcdef", "wifi_wep_length"), ("WEP", "0123456789", None),
    ("WPA", "ha:{{ states('input_text.pw') }}", None), ("nopass", "", None),
])
def test_password_rules(security: str, password: str, problem: str | None) -> None:
    assert wifi.password_problem(security, password) == problem


# --- validation (shared schema) -----------------------------------------------------------------

def _qr(**card):
    panel = {"panelRecvTopic": "tele/p/RESULT", "panelSendTopic": "cmnd/p/CustomSend", "locale": "pl_PL",
             "timeFormat": "%H:%M", "dateFormat": "full", "screensaver": {"entities": []},
             "cards": [{"type": "cardQR", "title": "Gość", **card}]}
    return {"nspanels": {"p": panel}}


def _issues(config, secrets=None):
    return {(tuple(i.path[4:]), i.code, i.severity) for i in collect_issues(config, None, secrets)}


def test_qr_card_needs_a_code_or_wifi() -> None:
    assert (("qrCode",), "required", "error") in _issues(_qr())
    assert _issues(_qr(qrCode="https://example.com")) == {(("entities",), "items_empty", "warning")}
    config = _qr(wifi={"ssid": "Dom", "password": "haslo1234"})  # the network rows fill the card
    assert _issues(config) == set()
    config_manager.validate(config)
    assert (("qrCode",), "wifi_qr_ignored", "warning") in _issues(_qr(qrCode="x", wifi={"ssid": "D", "password": "haslo1234"}))


def test_wifi_validation() -> None:
    assert (("wifi", "ssid"), "required", "error") in _issues(_qr(wifi={"password": "haslo1234"}))
    assert (("wifi", "ssid"), "wifi_ssid_long", "error") in _issues(_qr(wifi={"ssid": "ż" * 17, "password": "haslo1234"}))
    assert _issues(_qr(wifi={"ssid": "x" * 32, "password": "haslo1234"})) == set()
    assert (("wifi", "password"), "wifi_wpa_length", "error") in _issues(_qr(wifi={"ssid": "D", "password": "krotkie"}))
    assert (("wifi", "password"), "wifi_wep_length", "error") in _issues(
        _qr(wifi={"ssid": "D", "security": "WEP", "password": "krotkie"}))
    assert (("wifi", "password"), "wifi_password_missing", "warning") in _issues(_qr(wifi={"ssid": "D"}))
    assert _issues(_qr(wifi={"ssid": "D", "security": "nopass", "password": "x"})) == {
        (("wifi", "password"), "wifi_password_ignored", "warning")}
    both = _issues(_qr(wifi={"ssid": "D", "password": "haslo1234", "passwordSecret": "wifi"}))
    assert {(("wifi", "password"), "wifi_password_sources", "error"),
            (("wifi", "passwordSecret"), "wifi_password_sources", "error")} <= both
    assert (("wifi", "security"), "one_of", "error") in _issues(_qr(wifi={"ssid": "D", "security": "WPA9"}))
    assert (("wifi", "password"), "wifi_tilde", "error") in _issues(_qr(wifi={"ssid": "D", "password": "haslo~1234"}))
    secret = _qr(wifi={"ssid": "D", "passwordSecret": "wifi_pw"})
    assert _issues(secret, {"wifi_pw"}) == set()
    assert (("wifi", "passwordSecret"), "secret_missing", "warning") in _issues(secret, {"other"})


def test_loader_takes_the_password_from_secrets(tmp_path: Path) -> None:
    folder = tmp_path / "nspanel_lovelace_ui"
    folder.mkdir()
    path = folder / "panels.yaml"
    path.write_text(yaml.safe_dump(_qr(wifi={"ssid": "Dom", "passwordSecret": "wifi_pw"})), encoding="utf-8")
    config, warnings = load_config(path, tmp_path)
    assert warnings == ["wifi.passwordSecret: wifi_pw is not in secrets.yaml"]
    (tmp_path / "secrets.yaml").write_text("wifi_pw: tajne-haslo-1\n", encoding="utf-8")
    config, warnings = load_config(path, tmp_path)
    assert warnings == [] and config["nspanels"]["p"]["cards"][0]["wifi"]["password"] == "tajne-haslo-1"
    assert "tajne" not in path.read_text(encoding="utf-8")  # only in memory


def test_import_recognises_a_wifi_code() -> None:
    apps = yaml.safe_dump({"nspanel-1": {"module": "nspanel-lovelace-ui", "class": "NsPanelLovelaceUIManager",
                                         "config": {"panelRecvTopic": "tele/p/RESULT", "panelSendTopic": "cmnd/p/CustomSend",
                                                    "cards": [{"type": "cardQR", "title": "Gość",
                                                               "qrCode": "WIFI:S:Dom;T:WPA;P:haslo1234;;"}]}}})
    result = config_manager.import_yaml(apps, "Europe/Warsaw", integration=True)
    card = result["config"]["nspanels"]["nspanel-1"]["cards"][0]
    assert card["wifi"] == {"ssid": "Dom", "security": "WPA", "password": "haslo1234", "show": "ssid"}
    assert "qrCode" not in card
    assert not any("haslo1234" in warning for warning in result["warnings"])


# --- panel --------------------------------------------------------------------------------------

async def test_panel_gets_the_code_and_the_network(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                                   caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    config["nspanels"]["living_room"]["cards"] = [{"type": "cardQR", "title": "Gość", "wifi": {
        "ssid": "Dom;1", "passwordEntity": "input_text.wifi", "show": "ssid_password"}}]
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    hass.states.async_set("input_text.wifi", "tajne:haslo")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    def send(message):
        async_fire_mqtt_message(hass, RECV, json.dumps({"CustomRecv": message}))

    send("event,startup,55,eu")
    send("event,buttonPress2,screensaver,bExit,1")
    await wait_for(hass, lambda: "pageType~cardQR" in published(mqtt_mock))
    send("event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("entityUpd~Gość") for p in published(mqtt_mock)))
    update = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~Gość"))
    assert "~WIFI:T:WPA;S:Dom\\;1;P:tajne\\:haslo;;~" in update
    rows = update.split("~text~")[1:]
    assert [row.split("~")[0] for row in rows] == ["iText.wifi_ssid", "iText.wifi_password"]
    assert rows[0].endswith(f"~{NAMES[0]}~Dom;1") and rows[1].endswith(f"~{NAMES[1]}~tajne:haslo")
    # Our debug log hides the password (Home Assistant's own MQTT debug log prints every payload).
    ours = [r.getMessage() for r in caplog.records if not r.name.startswith("homeassistant.components.mqtt")]
    assert any("Sent Message" in m and "P:***" in m for m in ours)
    assert not any("tajne" in m for m in ours)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


# --- editor -------------------------------------------------------------------------------------

async def test_editor_wifi_helper(hass: HomeAssistant, mqtt_mock, panels_file: Path, hass_ws_client) -> None:
    (Path(hass.config.config_dir) / "secrets.yaml").write_text("wifi_pw: tajne-haslo-1\n", encoding="utf-8")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    ids = iter(range(1, 100))

    async def call(command, **data):
        await client.send_json({"id": next(ids), "type": f"{DOMAIN}/editor/{command}", **data})
        return (await client.receive_json())["result"]

    assert (await call("wifi", parse="WIFI:T:WPA;S:Dom;P:x\\;y;;"))["wifi"] == {
        "ssid": "Dom", "security": "WPA", "password": "x;y"}
    preview = await call("wifi", wifi={"ssid": "Dom", "passwordSecret": "wifi_pw"})
    assert preview["svg"].startswith("<svg") and preview["password"] is True and preview["source"] == "passwordSecret"
    assert "tajne" not in json.dumps(preview)  # only the picture leaves the server
    missing = await call("wifi", wifi={"ssid": "Dom", "passwordEntity": "input_text.none"})
    assert missing["password"] is False
    assert (await call("wifi", text="https://example.com"))["svg"].startswith("<svg")
    loaded = await call("load")
    assert loaded["secrets"] == ["wifi_pw"]  # names only
    issues = (await call("validate", config=_qr(wifi={"ssid": "D", "passwordSecret": "nope"})))["issues"]
    assert any(i["code"] == "secret_missing" for i in issues)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
