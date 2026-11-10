"""Config flow tests."""
from __future__ import annotations

from pathlib import Path
import shutil
from unittest.mock import patch

import pytest
import yaml

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nspanel_lovelace_ui.const import (
    CONF_CONFIG_FILE,
    CONF_IMPORT_FILE,
    DEFAULT_CONFIG_FILE,
    DOMAIN,
)

from .conftest import FIXTURES


@pytest.fixture(autouse=True)
def no_setup():
    """Config flow tests do not start the runtime."""
    with patch("custom_components.nspanel_lovelace_ui.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def mqtt_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain="mqtt", data={"broker": "localhost"})
    entry.add_to_hass(hass)
    return entry


async def _start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_user_flow_existing_file(hass: HomeAssistant, panels_file: Path, mqtt_entry) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE}


async def test_user_flow_missing_file(hass: HomeAssistant, mqtt_entry) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: "missing.yaml"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_config"}
    assert "File not found" in result["description_placeholders"]["error"]


async def test_user_flow_invalid_yaml(hass: HomeAssistant, mqtt_entry) -> None:
    Path(hass.config.path("bad.yaml")).write_text("nspanels:\n  p1:\n    cards: []\n", encoding="utf-8")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CONFIG_FILE: "bad.yaml"})
    assert result["errors"] == {"base": "invalid_config"}


async def test_user_flow_rejects_path_outside_config(hass: HomeAssistant, mqtt_entry) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: "../../etc/passwd"})
    assert result["errors"] == {"base": "path_outside_config"}


async def test_user_flow_requires_mqtt(hass: HomeAssistant, panels_file: Path) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    assert result["errors"] == {"base": "mqtt_not_configured"}


async def test_user_flow_esphome_without_mqtt(hass: HomeAssistant, panels_file: Path) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    config["use_ha_api"] = True
    panels_file.write_text(yaml.safe_dump(config), encoding="utf-8")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_import_appdaemon_apps_yaml(hass: HomeAssistant, mqtt_entry) -> None:
    shutil.copy(FIXTURES / "apps.yaml", hass.config.path("apps.yaml"))
    result = await _start(hass)
    with patch("custom_components.nspanel_lovelace_ui.config_flow.persistent_notification.async_create") as notify:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE, CONF_IMPORT_FILE: "apps.yaml"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Warnings (skipped app, weather conversion) are shown as a notification.
    assert "Skipped unrelated AppDaemon entry: other_app" in notify.call_args.args[1]

    converted = yaml.safe_load(Path(hass.config.path(DEFAULT_CONFIG_FILE)).read_text(encoding="utf-8"))
    panel = converted["nspanels"]["nspanel-1"]
    assert panel["panelRecvTopic"] == "tele/tasmota_panel/RESULT"
    assert panel["timeZone"] == "Europe/Warsaw"  # AppDaemon "timezone" renamed
    assert panel["screensaver"]["entities"][0] == {"entity": "weather.home"}
    assert "other_app" not in converted["nspanels"]


async def test_import_never_overwrites(hass: HomeAssistant, panels_file: Path, mqtt_entry) -> None:
    shutil.copy(FIXTURES / "apps.yaml", hass.config.path("apps.yaml"))
    before = panels_file.read_text(encoding="utf-8")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE, CONF_IMPORT_FILE: "apps.yaml"})
    assert result["errors"] == {CONF_CONFIG_FILE: "config_exists"}
    assert panels_file.read_text(encoding="utf-8") == before


async def test_single_instance(hass: HomeAssistant, panels_file: Path, mqtt_entry) -> None:
    MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reconfigure(hass: HomeAssistant, panels_file: Path, mqtt_entry) -> None:
    other = Path(hass.config.path("other.yaml"))
    shutil.copy(panels_file, other)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_CONFIG_FILE: "other.yaml"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_CONFIG_FILE] == "other.yaml"
