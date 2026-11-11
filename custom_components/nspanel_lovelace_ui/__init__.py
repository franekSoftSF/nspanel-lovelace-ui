"""NSPanel Lovelace UI: native Home Assistant backend for the Lovelace UI panel firmware."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import download
from .config import ConfigError, load_config, resolve_path
from .const import (
    ATTR_PANEL,
    CONF_CONFIG_FILE,
    CONF_FIRMWARE_BASE_URL,
    CONF_FIRMWARE_DOWNLOAD,
    DATA_DOWNLOAD_ATTEMPTED,
    DOMAIN,
    FIRMWARE_FOLDER,
    SERVICE_DOWNLOAD_FIRMWARE,
    SERVICE_RELOAD,
    SERVICE_UPDATE_BERRY_DRIVER,
)
from .firmware import FirmwareError, FirmwarePackage, install_zip, load_package, validate_base_url
from .http import async_get_http_state
from .runtime import NSPanelRuntime

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.UPDATE]

type NSPanelConfigEntry = ConfigEntry[NSPanelRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions (reload, Berry driver update)."""

    async def _reload(call: ServiceCall) -> None:  # noqa: ARG001
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    async def _update_berry(call: ServiceCall) -> None:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
        runtime: NSPanelRuntime = entries[0].runtime_data
        package = runtime.firmware
        if package is None or package.berry is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_berry_driver")
        url = runtime.firmware_url(package.berry.path.name)
        if url is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_http_url")
        names = [worker.name for worker in runtime.workers.values()]
        if panel := call.data.get(ATTR_PANEL):
            if panel not in names:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_panel",
                                             translation_placeholders={"panel": panel})
            names = [panel]
        try:
            for name in names:
                runtime.async_update_berry_driver(name, url)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def _download_firmware(call: ServiceCall) -> None:  # noqa: ARG001
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
        tag = download.release_tag(str((await async_get_integration(hass, DOMAIN)).version))
        try:
            await download.async_download_package(hass, tag, Path(hass.config.path(FIRMWARE_FOLDER)).parent)
        except FirmwareError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="download_failed",
                                     translation_placeholders={"error": str(err)}) from err
        ir.async_delete_issue(hass, DOMAIN, "firmware_download_failed")
        await hass.config_entries.async_reload(entries[0].entry_id)

    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _reload)
    hass.services.async_register(DOMAIN, SERVICE_DOWNLOAD_FIRMWARE, _download_firmware)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE_BERRY_DRIVER, _update_berry,
                                 schema=vol.Schema({vol.Optional(ATTR_PANEL): cv.string}))
    return True


def _base_url(hass: HomeAssistant, settings: dict[str, Any]) -> str | None:
    """http://host:port the panels can download from (Berry: plain HTTP only)."""
    if configured := settings.get(CONF_FIRMWARE_BASE_URL):
        return validate_base_url(str(configured))
    try:
        url = get_url(hass, allow_external=False, allow_cloud=False, allow_ip=True, prefer_external=False)
    except NoURLAvailableError:
        return None
    if urlsplit(url).scheme != "http":
        _LOGGER.warning("Home Assistant's internal URL %s is not plain HTTP; set %s in panels.yaml "
                        "for display firmware updates", url, CONF_FIRMWARE_BASE_URL)
        return None
    return validate_base_url(url)


def _apply_package(settings: dict[str, Any], package: FirmwarePackage, runtime: NSPanelRuntime) -> None:
    """Point the backend's on-panel update prompt (updateMode) at the local package."""
    for panel in settings["nspanels"].values():
        model = panel.get("model", "eu")
        item = package.tft.get(model)
        url = runtime.firmware_url(item.path.name) if item else None
        if url is None or f"displayURL-{model.upper()}" in panel:
            continue
        panel.setdefault("displayFirmwareVersion", package.version)
        panel[f"displayURL-{model.upper()}"] = url


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry) -> bool:
    """Load panels.yaml and start one worker per panel."""
    try:
        path = resolve_path(hass.config.config_dir, entry.data[CONF_CONFIG_FILE])
        settings, warnings = await hass.async_add_executor_job(load_config, path)
        base_url = _base_url(hass, settings)
    except (ConfigError, FirmwareError) as err:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="invalid_config",
            translation_placeholders={"error": str(err)},
        ) from err

    if warnings:
        _LOGGER.warning("%s: %s", path, "; ".join(warnings))
        ir.async_create_issue(
            hass, DOMAIN, "config_warnings", is_fixable=False, severity=ir.IssueSeverity.WARNING,
            translation_key="config_warnings",
            translation_placeholders={
                "file": entry.data[CONF_CONFIG_FILE],
                "warnings": "\n".join(f"- {warning}" for warning in warnings),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, "config_warnings")

    if not settings.get("use_ha_api") and not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady(translation_domain=DOMAIN, translation_key="mqtt_not_ready")

    runtime = NSPanelRuntime(hass, settings)
    runtime.http_state = async_get_http_state(hass)
    runtime.firmware_base_url = base_url
    folder = Path(hass.config.path(FIRMWARE_FOLDER))
    zip_error: FirmwareError | None = None
    try:
        if installed := await hass.async_add_executor_job(install_zip, folder):
            _LOGGER.info("Display firmware package %s unpacked into %s", installed, folder)
    except FirmwareError as err:  # keep the package that is already there
        zip_error = err
    try:
        runtime.firmware = await hass.async_add_executor_job(load_package, folder)
        if zip_error:
            raise zip_error
    except FirmwareError as err:
        _LOGGER.error("Display firmware package in %s ignored: %s", folder, err)
        ir.async_create_issue(hass, DOMAIN, "firmware_invalid", is_fixable=False,
                              severity=ir.IssueSeverity.ERROR, translation_key="firmware_invalid",
                              translation_placeholders={"folder": FIRMWARE_FOLDER, "error": str(err)})
    else:
        ir.async_delete_issue(hass, DOMAIN, "firmware_invalid")
    runtime.http_state.package = runtime.firmware
    if runtime.firmware is not None:
        _apply_package(settings, runtime.firmware, runtime)

    await runtime.async_start()
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Started %d NSPanel(s) from %s", len(runtime.workers), path)

    tag = download.release_tag(str((await async_get_integration(hass, DOMAIN)).version))
    attempted: set[str] = hass.data.setdefault(DATA_DOWNLOAD_ATTEMPTED, set())
    if (settings.get(CONF_FIRMWARE_DOWNLOAD, True) and tag not in attempted
            and download.needs_download(runtime.firmware, tag)):
        attempted.add(tag)  # once per Home Assistant run; the action retries on demand
        entry.async_create_background_task(
            hass, _async_download(hass, entry, tag), f"{DOMAIN} firmware download")
    return True


async def _async_download(hass: HomeAssistant, entry: NSPanelConfigEntry, tag: str) -> None:
    """Fetch the release's firmware package, then reload so it is checked and unpacked."""
    try:
        await download.async_download_package(hass, tag, Path(hass.config.path(FIRMWARE_FOLDER)).parent)
    except FirmwareError as err:
        _LOGGER.warning("Display firmware package %s not downloaded: %s", tag, err)
        ir.async_create_issue(hass, DOMAIN, "firmware_download_failed", is_fixable=False,
                              severity=ir.IssueSeverity.WARNING, translation_key="firmware_download_failed",
                              translation_placeholders={"url": download.asset_url(tag), "error": str(err),
                                                        "folder": str(Path(FIRMWARE_FOLDER).parent)})
        return
    ir.async_delete_issue(hass, DOMAIN, "firmware_download_failed")
    _LOGGER.info("Display firmware package %s downloaded", tag)
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NSPanelConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.http_state.package = None
        await entry.runtime_data.async_stop()
    return unloaded
