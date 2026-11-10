"""NSPanel Lovelace UI: native Home Assistant backend for the Lovelace UI panel firmware."""
from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .config import ConfigError, load_config, resolve_path
from .const import CONF_CONFIG_FILE, DOMAIN, SERVICE_RELOAD
from .runtime import NSPanelRuntime

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type NSPanelConfigEntry = ConfigEntry[NSPanelRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the reload action (re-reads panels.yaml)."""

    async def _reload(call: ServiceCall) -> None:  # noqa: ARG001
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _reload)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry) -> bool:
    """Load panels.yaml and start one worker per panel."""
    try:
        path = resolve_path(hass.config.config_dir, entry.data[CONF_CONFIG_FILE])
        settings = await hass.async_add_executor_job(load_config, path)
    except ConfigError as err:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="invalid_config",
            translation_placeholders={"error": str(err)},
        ) from err

    if not settings.get("use_ha_api") and not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady(translation_domain=DOMAIN, translation_key="mqtt_not_ready")

    runtime = NSPanelRuntime(hass, settings)
    await runtime.async_start()
    entry.runtime_data = runtime
    _LOGGER.info("Started %d NSPanel(s) from %s", len(runtime.workers), path)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NSPanelConfigEntry) -> bool:
    await entry.runtime_data.async_stop()
    return True
