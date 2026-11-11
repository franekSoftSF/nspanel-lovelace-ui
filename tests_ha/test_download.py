"""Firmware package download from the GitHub release (integration version = release tag)."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nspanel_lovelace_ui import download
from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN
from custom_components.nspanel_lovelace_ui.firmware import FirmwareError, load_package

from .conftest import wait_for

REAL_DOWNLOAD = download.async_download_package  # the conftest mock replaces it during tests


async def _tag(hass: HomeAssistant) -> str:
    return download.release_tag(str((await async_get_integration(hass, DOMAIN)).version))


def _package(folder: Path, release: str) -> None:
    from .test_firmware import make_package

    make_package(folder)
    manifest = json.loads((folder / "firmware.json").read_text(encoding="utf-8"))
    manifest["release"] = release
    (folder / "firmware.json").write_text(json.dumps(manifest), encoding="utf-8")


def _zip_writer(tmp_path: Path, release: str):
    async def fake(hass: HomeAssistant, tag: str, base: Path) -> Path:
        source = tmp_path / f"src-{tag}"
        _package(source, release)
        target = base / download.ASSET
        base.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w") as zf:
            for item in source.iterdir():
                zf.write(item, f"firmware/{item.name}")
        return target
    return fake


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    # Not asserted: a mocked download finishes at once and its reload may overlap the first setup.
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize(("release", "tag", "expected"), [
    (None, "v5.2.1", True),
    ("v5.2.0", "v5.2.1", True),
    ("v5.2.1", "v5.2.1", False),
    ("v5.3.0", "v5.2.1", False),  # a newer package is never replaced by an older one
    ("my-build", "v5.2.1", False),  # self-built package name: keep it
])
def test_needs_download(tmp_path: Path, release, tag, expected) -> None:
    package = None
    if release:
        _package(tmp_path, release)
        package = load_package(tmp_path)
    assert download.needs_download(package, tag) is expected


async def test_download_writes_zip(hass: HomeAssistant, aioclient_mock, tmp_path: Path) -> None:
    aioclient_mock.get(download.asset_url("v5.2.1"), content=b"PK-data")
    path = await REAL_DOWNLOAD(hass, "v5.2.1", tmp_path / "nspanel_lovelace_ui")
    assert path == tmp_path / "nspanel_lovelace_ui" / "nspanel-firmware.zip"
    assert path.read_bytes() == b"PK-data"
    assert not (path.parent / "nspanel-firmware.zip.part").exists()


async def test_download_http_error(hass: HomeAssistant, aioclient_mock, tmp_path: Path) -> None:
    aioclient_mock.get(download.asset_url("v9.9.9"), status=404)
    with pytest.raises(FirmwareError, match="HTTP 404"):
        await REAL_DOWNLOAD(hass, "v9.9.9", tmp_path)
    assert not any(tmp_path.iterdir())


async def test_setup_downloads_missing_package(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                               firmware_download, tmp_path: Path) -> None:
    tag = await _tag(hass)
    firmware_download.side_effect = _zip_writer(tmp_path, tag)
    entry = await _setup(hass)
    await wait_for(hass, lambda: entry.state is ConfigEntryState.LOADED and entry.runtime_data.firmware is not None)
    assert entry.runtime_data.firmware.release == tag
    assert firmware_download.await_count == 1
    base = Path(hass.config.path("nspanel_lovelace_ui"))
    assert (base / "nspanel-firmware.zip.installed").exists()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "firmware_download_failed") is None


async def test_download_tried_once_per_run(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                           firmware_download, tmp_path: Path) -> None:
    # The release asset is older than the integration: no endless download/reload loop.
    firmware_download.side_effect = _zip_writer(tmp_path, "v5.0.0")
    entry = await _setup(hass)
    await wait_for(hass, lambda: entry.state is ConfigEntryState.LOADED and entry.runtime_data.firmware is not None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert firmware_download.await_count == 1


async def test_download_failure_creates_issue(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                              firmware_download) -> None:
    entry = await _setup(hass)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert firmware_download.await_count == 1
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "firmware_download_failed")
    assert issue is not None
    assert "offline (tests)" in issue.translation_placeholders["error"]


async def test_download_disabled(hass: HomeAssistant, mqtt_mock, panels_file: Path, firmware_download) -> None:
    panels_file.write_text("firmware_download: false\n" + panels_file.read_text(encoding="utf-8"),
                           encoding="utf-8")
    await _setup(hass)
    assert firmware_download.await_count == 0


async def test_current_package_not_downloaded(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                                              firmware_download) -> None:
    _package(Path(hass.config.path("nspanel_lovelace_ui", "firmware")), await _tag(hass))
    await _setup(hass)
    assert firmware_download.await_count == 0


async def test_download_action(hass: HomeAssistant, mqtt_mock, panels_file: Path,
                               firmware_download, tmp_path: Path) -> None:
    panels_file.write_text("firmware_download: false\n" + panels_file.read_text(encoding="utf-8"),
                           encoding="utf-8")
    entry = await _setup(hass)
    with pytest.raises(HomeAssistantError, match="offline"):
        await hass.services.async_call(DOMAIN, "download_firmware", blocking=True)
    firmware_download.side_effect = _zip_writer(tmp_path, await _tag(hass))
    await hass.services.async_call(DOMAIN, "download_firmware", blocking=True)
    await hass.async_block_till_done()
    assert entry.runtime_data.firmware is not None


async def test_invalid_download_option(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    panels_file.write_text("firmware_download: maybe\n" + panels_file.read_text(encoding="utf-8"),
                           encoding="utf-8")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
