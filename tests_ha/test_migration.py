"""Migration helpers: firmware zip, !secret import, disabling the AppDaemon apps, import default."""
from __future__ import annotations

from pathlib import Path
import shutil
from unittest.mock import patch
import zipfile

import pytest
import yaml

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nspanel_lovelace_ui.config import (
    ConfigError,
    disable_appdaemon_apps,
    find_appdaemon_apps,
    import_config,
)
from custom_components.nspanel_lovelace_ui.const import (
    CONF_CONFIG_FILE,
    CONF_DISABLE_APPS,
    CONF_IMPORT_FILE,
    DEFAULT_CONFIG_FILE,
    DOMAIN,
)
from custom_components.nspanel_lovelace_ui.firmware import FirmwareError, install_zip, load_package

from .conftest import FIXTURES
from .test_firmware import make_package

APPS = FIXTURES / "apps.yaml"


def make_zip(tmp: Path, archive: Path, prefix: str = "firmware/", **kwargs) -> dict:
    manifest = make_package(tmp, **kwargs)
    with zipfile.ZipFile(archive, "w") as zf:
        for item in tmp.iterdir():
            zf.write(item, prefix + item.name)
    return manifest


# --- firmware zip ---------------------------------------------------------------------------

@pytest.mark.parametrize("prefix", ["firmware/", ""])
def test_install_zip_next_to_folder(tmp_path: Path, prefix: str) -> None:
    folder = tmp_path / "nspanel_lovelace_ui" / "firmware"
    folder.parent.mkdir()
    make_zip(tmp_path / "src", folder.parent / "nspanel-firmware.zip", prefix)
    assert install_zip(folder) == "nspanel-firmware.zip"
    assert load_package(folder).version == 55
    assert not (folder.parent / "nspanel-firmware.zip").exists()
    assert (folder.parent / "nspanel-firmware.zip.installed").exists()
    assert not (folder.parent / ".firmware-unpack").exists()
    assert install_zip(folder) is None  # not unpacked twice


def test_install_zip_replaces_old_package(tmp_path: Path) -> None:
    folder = tmp_path / "firmware"
    make_package(folder, version=54, models=("eu", "us-p"))
    make_zip(tmp_path / "src", folder / "nspanel-firmware.zip", models=("eu",), berry=False)
    install_zip(folder)
    package = load_package(folder)
    assert package.version == 55
    assert set(package.tft) == {"eu"}
    assert not (folder / "autoexec.be").exists()
    assert not (folder / "nspanel-us-p-v5.2.0.tft").exists()


@pytest.mark.parametrize("entry", ["../evil.tft", "firmware/sub/x.tft"])
def test_install_zip_rejects_paths(tmp_path: Path, entry: str) -> None:
    folder = tmp_path / "firmware"
    make_package(folder, version=54)
    archive = tmp_path / "nspanel-firmware.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(entry, b"x")
    with pytest.raises(FirmwareError):
        install_zip(folder)
    assert load_package(folder).version == 54  # the old package stays
    assert archive.exists()
    assert not (tmp_path / "evil.tft").exists()


def test_install_zip_checks_hashes(tmp_path: Path) -> None:
    folder = tmp_path / "firmware"
    src = tmp_path / "src"
    make_package(src)
    (src / "nspanel-eu-v5.2.0.tft").write_bytes(b"broken")
    with zipfile.ZipFile(tmp_path / "nspanel-firmware.zip", "w") as zf:
        for item in src.iterdir():
            zf.write(item, item.name)
    with pytest.raises(FirmwareError, match="bytes"):
        install_zip(folder)
    assert load_package(folder) is None


async def test_setup_unpacks_zip(hass: HomeAssistant, mqtt_mock, panels_file: Path, tmp_path: Path) -> None:
    base = Path(hass.config.path("nspanel_lovelace_ui"))
    make_zip(tmp_path / "src", base / "nspanel-firmware.zip")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.firmware.version == 55
    assert (base / "nspanel-firmware.zip.installed").exists()


async def test_setup_keeps_package_on_broken_zip(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    base = Path(hass.config.path("nspanel_lovelace_ui"))
    make_package(base / "firmware", version=54)
    (base / "nspanel-firmware.zip").write_bytes(b"not a zip")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.firmware.version == 54
    assert ir.async_get(hass).async_get_issue(DOMAIN, "firmware_invalid")


# --- import: secrets, disable, default ----------------------------------------------------------

def test_import_resolves_secrets(tmp_path: Path) -> None:
    apps = tmp_path / "appdaemon" / "apps"
    apps.mkdir(parents=True)
    text = APPS.read_text(encoding="utf-8").replace('"tele/tasmota_panel/RESULT"', "!secret panel_recv")
    (apps / "apps.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "appdaemon" / "secrets.yaml").write_text("panel_recv: tele/secret_panel/RESULT\n", encoding="utf-8")
    target = tmp_path / "panels.yaml"
    result = import_config(apps / "apps.yaml", target, tmp_path)
    assert result.panels == ["nspanel-1"]
    config = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert config["nspanels"]["nspanel-1"]["panelRecvTopic"] == "tele/secret_panel/RESULT"


def test_import_missing_secret(tmp_path: Path) -> None:
    source = tmp_path / "apps.yaml"
    source.write_text(APPS.read_text(encoding="utf-8").replace('"pl_PL"', "!secret nope"), encoding="utf-8")
    with pytest.raises(ConfigError, match="nope"):
        import_config(source, tmp_path / "panels.yaml", tmp_path)


def test_disable_appdaemon_apps_keeps_comments(tmp_path: Path) -> None:
    source = tmp_path / "apps.yaml"
    original = "# my apps\r\n" + APPS.read_text(encoding="utf-8").replace("\n", "\r\n") + (
        "panel2:  # second\r\n    module: nspanel-lovelace-ui\r\n    disable: false\r\n    config: {}\r\n")
    source.write_bytes(original.encode("utf-8"))
    backup = disable_appdaemon_apps(source, ["nspanel-1", "panel2"])
    assert backup.read_bytes() == original.encode("utf-8")
    text = source.read_bytes().decode("utf-8")
    assert text.startswith("# my apps\r\nnspanel-1:\r\n  disable: true\r\n  module: nspanel-lovelace-ui\r\n")
    assert "    disable: true\r\n    config: {}" in text
    assert "disable: false" not in text
    data = yaml.safe_load(text)
    assert data["nspanel-1"]["disable"] is True and data["panel2"]["disable"] is True
    assert "disable" not in data["other_app"]
    # A second run keeps the first backup (the true original).
    disable_appdaemon_apps(source, ["nspanel-1"])
    assert backup.read_bytes() == original.encode("utf-8")


def test_disable_unknown_app(tmp_path: Path) -> None:
    source = tmp_path / "apps.yaml"
    shutil.copy(APPS, source)
    with pytest.raises(ConfigError):
        disable_appdaemon_apps(source, ["missing"])


def test_find_appdaemon_apps(tmp_path: Path) -> None:
    assert find_appdaemon_apps(str(tmp_path)) is None
    apps = tmp_path / "appdaemon" / "apps"
    apps.mkdir(parents=True)
    (apps / "apps.yaml").write_text("hello:\n  module: hello\n", encoding="utf-8")
    assert find_appdaemon_apps(str(tmp_path)) is None
    shutil.copy(APPS, apps / "apps.yaml")
    assert find_appdaemon_apps(str(tmp_path)) == "appdaemon/apps/apps.yaml"


@pytest.fixture
def mqtt_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain="mqtt", data={"broker": "localhost"})
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def no_setup():
    with patch("custom_components.nspanel_lovelace_ui.async_setup_entry", return_value=True):
        yield


async def _flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return result


def _default(result, key: str):
    return next(field.default() for field in result["data_schema"].schema if field == key)


async def test_flow_suggests_and_disables_apps(hass: HomeAssistant, mqtt_entry, no_setup) -> None:
    apps = Path(hass.config.path("appdaemon", "apps", "apps.yaml"))
    apps.parent.mkdir(parents=True)
    shutil.copy(APPS, apps)
    result = await _flow(hass)
    assert _default(result, CONF_IMPORT_FILE) == "appdaemon/apps/apps.yaml"
    assert _default(result, CONF_DISABLE_APPS) is True
    with patch("custom_components.nspanel_lovelace_ui.config_flow.persistent_notification.async_create") as notify:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE,
                                CONF_IMPORT_FILE: "appdaemon/apps/apps.yaml", CONF_DISABLE_APPS: True})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert yaml.safe_load(apps.read_text(encoding="utf-8"))["nspanel-1"]["disable"] is True
    assert apps.with_name("apps.yaml.nspanel-backup").exists()
    assert "Disabled in appdaemon/apps/apps.yaml" in notify.call_args.args[1]


async def test_flow_can_keep_apps(hass: HomeAssistant, mqtt_entry, no_setup) -> None:
    shutil.copy(APPS, hass.config.path("apps.yaml"))
    result = await _flow(hass)
    assert _default(result, CONF_IMPORT_FILE) == ""
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE, CONF_IMPORT_FILE: "apps.yaml",
                            CONF_DISABLE_APPS: False})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert Path(hass.config.path("apps.yaml")).read_text(encoding="utf-8") == APPS.read_text(encoding="utf-8")


async def test_flow_does_not_disable_on_error(hass: HomeAssistant, no_setup) -> None:
    shutil.copy(APPS, hass.config.path("apps.yaml"))
    result = await _flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE, CONF_IMPORT_FILE: "apps.yaml"})
    assert result["errors"] == {"base": "mqtt_not_configured"}  # no MQTT: AppDaemon keeps the panel
    assert "disable" not in Path(hass.config.path("apps.yaml")).read_text(encoding="utf-8")
