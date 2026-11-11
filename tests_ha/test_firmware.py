"""Display firmware package, HTTP serving for Tasmota and the update entity."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from homeassistant.components.update import ATTR_IN_PROGRESS, ATTR_INSTALLED_VERSION, ATTR_LATEST_VERSION
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN
from custom_components.nspanel_lovelace_ui.firmware import (
    FirmwareError,
    load_package,
    validate_base_url,
)

from .conftest import RECV, published, wait_for

BASE = "http://192.168.1.10:8123"
TFT = bytes(range(256)) * 600  # 150 KiB of "firmware"


def make_package(folder: Path, version: int = 55, models=("eu",), berry: bool = True) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for model in models:
        name = f"nspanel-{model}-v5.2.0.tft"
        (folder / name).write_bytes(TFT)
        files[model] = {"file": name, "sha256": hashlib.sha256(TFT).hexdigest(), "size": len(TFT)}
    manifest = {"version": version, "release": "v5.2.0",
                "release_url": "https://github.com/franekSoftSF/nspanel-lovelace-ui/releases/tag/v5.2.0",
                "files": files}
    if berry:
        (folder / "autoexec.be").write_text("# berry\n", encoding="utf-8")
        data = (folder / "autoexec.be").read_bytes()
        manifest["berry"] = {"file": "autoexec.be", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    (folder / "firmware.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.fixture
def firmware_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("nspanel_lovelace_ui", "firmware"))


@pytest.fixture
def panels_with_base_url(panels_file: Path) -> Path:
    panels_file.write_text(f"firmware_base_url: {BASE}\n" + panels_file.read_text(encoding="utf-8"),
                           encoding="utf-8")
    return panels_file


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


def _startup(hass: HomeAssistant, version: int, model: str = "eu") -> None:
    async_fire_mqtt_message(hass, RECV, json.dumps({"CustomRecv": f"event,startup,{version},{model}"}))


def _entity_id(hass: HomeAssistant) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("update", DOMAIN, next(
        e.unique_id for e in er.async_get(hass).entities.values() if e.platform == DOMAIN))
    assert entity_id
    return entity_id


# --- package --------------------------------------------------------------------------------

def test_load_package(tmp_path: Path) -> None:
    assert load_package(tmp_path) is None
    make_package(tmp_path, models=("eu", "us-p"))
    package = load_package(tmp_path)
    assert package.version == 55
    assert set(package.tft) == {"eu", "us-p"}
    assert set(package.files()) == {"nspanel-eu-v5.2.0.tft", "nspanel-us-p-v5.2.0.tft", "autoexec.be"}


@pytest.mark.parametrize("change", [
    lambda m: m["files"]["eu"].update(sha256="0" * 64),
    lambda m: m["files"]["eu"].update(size=1),
    lambda m: m["files"]["eu"].update(file="../secrets.yaml"),
    lambda m: m["files"].update(xx=m["files"]["eu"]),
    lambda m: m.update(version="55"),
    lambda m: m.update(release_url="http://example.com"),
])
def test_invalid_package(tmp_path: Path, change) -> None:
    manifest = make_package(tmp_path)
    change(manifest)
    (tmp_path / "firmware.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(FirmwareError):
        load_package(tmp_path)


@pytest.mark.parametrize("url", ["https://ha.local:8123", "http://ha.local:8123/path", "http://u:p@ha.local",
                                 "http://ha.local;reboot", "ftp://ha.local"])
def test_base_url_must_be_plain_http(url: str) -> None:
    with pytest.raises(FirmwareError):
        validate_base_url(url)


def test_base_url_normalised() -> None:
    assert validate_base_url("http://192.168.1.10:8123/") == BASE


# --- HTTP ------------------------------------------------------------------------------------

async def test_http_serves_package_with_ranges(hass: HomeAssistant, hass_client_no_auth, mqtt_mock,
                                               panels_with_base_url: Path, firmware_dir: Path) -> None:
    make_package(firmware_dir)
    entry = await _setup(hass)
    runtime = entry.runtime_data
    client = await hass_client_no_auth()
    url = runtime.http_state.path("nspanel-eu-v5.2.0.tft")

    # What the Berry driver sends: HTTP/1.0 with "Range: bytes=<pos>-"; it reads Content-Length.
    response = await client.get(url, headers={"Range": "bytes=0-"})
    assert response.status == 206
    assert response.headers["Content-Length"] == str(len(TFT))
    assert await response.read() == TFT
    response = await client.get(url, headers={"Range": "bytes=1000-"})
    assert response.status == 206
    assert await response.read() == TFT[1000:]
    assert (await client.get(runtime.http_state.path("autoexec.be"))).status == 200

    for bad in (url.replace(runtime.http_state.token, "wrong-token"),
                runtime.http_state.path("firmware.json"),
                runtime.http_state.path("..%2Fpanels.yaml")):
        assert (await client.get(bad)).status in (400, 404)  # HA's security filter rejects ".." first

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert (await client.get(url)).status == 404  # nothing is served while unloaded


# --- update entity ------------------------------------------------------------------------

async def test_update_entity_flashes_from_local_url(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path,
                                                    firmware_dir: Path) -> None:
    make_package(firmware_dir)
    entry = await _setup(hass)
    entity_id = _entity_id(hass)
    assert hass.states.get(entity_id).attributes[ATTR_INSTALLED_VERSION] is None

    _startup(hass, 54)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes[ATTR_INSTALLED_VERSION] == "54"
    assert state.attributes[ATTR_LATEST_VERSION] == "55"

    install = hass.async_create_task(
        hass.services.async_call("update", "install", {"entity_id": entity_id}, blocking=True))
    url = BASE + entry.runtime_data.http_state.path("nspanel-eu-v5.2.0.tft")
    await wait_for(hass, lambda: published(mqtt_mock, "cmnd/nspanel_test/FlashNextion") == [url], block=False)
    assert hass.states.get(entity_id).attributes[ATTR_IN_PROGRESS] is True

    _startup(hass, 55)  # the display restarts with the new firmware; install() returns
    async with asyncio.timeout(10):
        await install
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes[ATTR_IN_PROGRESS] is False
    await hass.config_entries.async_unload(entry.entry_id)


async def test_on_panel_prompt_uses_local_package(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path,
                                                  firmware_dir: Path) -> None:
    make_package(firmware_dir)
    entry = await _setup(hass)
    runtime = entry.runtime_data
    worker = runtime.worker_by_name("living_room")
    assert worker.settings["displayFirmwareVersion"] == 55
    assert worker.settings["displayURL-EU"] == BASE + runtime.http_state.path("nspanel-eu-v5.2.0.tft")
    await hass.config_entries.async_unload(entry.entry_id)


async def test_update_berry_driver_action(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path,
                                          firmware_dir: Path) -> None:
    make_package(firmware_dir)
    entry = await _setup(hass)
    await hass.services.async_call(DOMAIN, "update_berry_driver", {"panel": "living_room"}, blocking=True)
    url = BASE + entry.runtime_data.http_state.path("autoexec.be")
    await wait_for(hass, lambda: published(mqtt_mock, "cmnd/nspanel_test/UpdateDriverVersion") == [url])
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "update_berry_driver", {"panel": "nope"}, blocking=True)
    await hass.config_entries.async_unload(entry.entry_id)


async def test_without_package(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path) -> None:
    entry = await _setup(hass)
    entity_id = _entity_id(hass)
    _startup(hass, 54)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_INSTALLED_VERSION] == "54"
    assert state.attributes[ATTR_LATEST_VERSION] is None
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("update", "install", {"entity_id": entity_id}, blocking=True)
    # Without a package the on-panel prompt keeps the upstream defaults.
    assert "displayURL-EU" not in entry.runtime_data.worker_by_name("living_room").settings
    await hass.config_entries.async_unload(entry.entry_id)


async def test_broken_package_creates_repair(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path,
                                             firmware_dir: Path) -> None:
    manifest = make_package(firmware_dir)
    manifest["files"]["eu"]["sha256"] = "0" * 64
    (firmware_dir / "firmware.json").write_text(json.dumps(manifest), encoding="utf-8")
    entry = await _setup(hass)
    assert entry.runtime_data.firmware is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, "firmware_invalid") is not None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_update_berry_driver_with_tapp(hass: HomeAssistant, mqtt_mock, panels_with_base_url: Path,
                                             firmware_dir: Path) -> None:
    """The recommended package carries nsp-lovelace-driver.tapp; the URL must end with .tapp."""
    manifest = make_package(firmware_dir, berry=False)
    tapp = firmware_dir / "nsp-lovelace-driver.tapp"
    tapp.write_bytes(b"PK\x03\x04 tapp")
    manifest["berry"] = {"file": tapp.name, "sha256": hashlib.sha256(tapp.read_bytes()).hexdigest(),
                         "size": tapp.stat().st_size}
    (firmware_dir / "firmware.json").write_text(json.dumps(manifest), encoding="utf-8")
    entry = await _setup(hass)
    await hass.services.async_call(DOMAIN, "update_berry_driver", {}, blocking=True)
    url = BASE + entry.runtime_data.http_state.path("nsp-lovelace-driver.tapp")
    await wait_for(hass, lambda: published(mqtt_mock, "cmnd/nspanel_test/UpdateDriverVersion") == [url])
    await hass.config_entries.async_unload(entry.entry_id)
