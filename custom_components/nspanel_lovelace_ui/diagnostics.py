"""Diagnostics download (Settings → Devices & services → NSPanel Lovelace UI → ⋮ → Download diagnostics)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from . import NSPanelConfigEntry
from .const import DOMAIN

# Credentials the add-on format allowed in panels.yaml, plus personal entity names in sleep settings.
TO_REDACT = {"mqtt_password", "mqtt_username", "home_assistant_token", "password", "token", "pin",
             "sleepTracking", "firmware_base_url"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: NSPanelConfigEntry) -> dict[str, Any]:
    runtime = entry.runtime_data
    package = runtime.firmware
    return {
        "integration_version": str((await async_get_integration(hass, DOMAIN)).version),
        "config_file": entry.data,
        "settings": async_redact_data(runtime.settings, TO_REDACT),
        "panels": {
            worker.name: {
                "display": runtime.panel_state.get(worker.name),
                "flash": runtime.panel_flash.get(worker.name),
                "page": runtime.panel_page.get(worker.name),
                "cards": len(runtime.cards(worker.name)),
                "worker_started": worker.panel is not None,
            }
            for worker in runtime.workers.values()
        },
        "firmware_package": None if package is None else {
            "version": package.version,
            "release": package.release,
            "models": sorted(package.tft),
            "berry_driver": package.berry.path.name if package.berry else None,
        },
        "firmware_base_url_set": runtime.firmware_base_url is not None,
    }
