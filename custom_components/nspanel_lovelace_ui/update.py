"""Update entity per panel: the display (.tft) firmware, flashed from the local package."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .const import DOMAIN, SIGNAL_PANEL_STATE

# The Berry driver reports progress ({"Flashing": {"complete": N}}) and failures to open the
# download; the install ends when the display restarts with the new version.
FLASH_TIMEOUT = 15 * 60


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    runtime = entry.runtime_data
    async_add_entities(DisplayFirmwareUpdate(entry, worker.name) for worker in runtime.workers.values())


class DisplayFirmwareUpdate(UpdateEntity):
    """Installed = version the display reports at startup; latest = local package version."""

    _attr_has_entity_name = True
    _attr_translation_key = "display_firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    # PROGRESS: Home Assistant only shows in_progress for entities that declare it.
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.PROGRESS
    _attr_should_poll = False

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        self._entry = entry
        self._panel = panel
        self._attr_unique_id = f"{entry.entry_id}_{panel}_display_firmware"
        settings = entry.runtime_data.worker_by_name(panel).settings
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{panel}")},
            name=f"NSPanel {panel}",
            manufacturer="Sonoff",
            model=f"NSPanel ({settings.get('model', 'eu')})",
        )
        self._flash_target: int | None = None
        self._flashed: asyncio.Future[int] | None = None

    @property
    def _state(self) -> dict[str, Any]:
        return self._entry.runtime_data.panel_state.get(self._panel, {})

    @property
    def _model(self) -> str:
        return self._state.get("model") or self._entry.runtime_data.worker_by_name(self._panel).settings.get("model", "eu")

    @property
    def installed_version(self) -> str | None:
        version = self._state.get("version")
        return None if version is None else str(version)

    @property
    def latest_version(self) -> str | None:
        package = self._entry.runtime_data.firmware
        if package is None or self._model not in package.tft:
            return None
        return str(package.version)

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        return int(latest_version) > int(installed_version)

    @property
    def release_url(self) -> str | None:
        package = self._entry.runtime_data.firmware
        return package.release_url if package else None

    @property
    def release_summary(self) -> str | None:
        package = self._entry.runtime_data.firmware
        return f"{package.release} ({self._model})" if package else None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_PANEL_STATE, self._panel_changed))

    @callback
    def _panel_changed(self, panel: str) -> None:
        if panel != self._panel:
            return
        version = self._state.get("version")
        flash = self._entry.runtime_data.panel_flash.get(self._panel, {})
        if self._flashed is not None and not self._flashed.done():
            if version is not None and version >= self._flash_target:
                self._flashed.set_result(version)
            elif flash.get("error"):
                self._flashed.set_exception(HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="flash_failed",
                    translation_placeholders={"error": flash["error"]}))
            elif "complete" in flash:
                self._attr_update_percentage = flash["complete"]
        self.async_write_ha_state()

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Send FlashNextion and wait until the display restarts with the new version.

        Home Assistant ends in_progress when this returns, so it waits (up to FLASH_TIMEOUT).
        """
        runtime = self._entry.runtime_data
        package = runtime.firmware
        if package is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_firmware_package")
        if self._state.get("model") is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="panel_not_reported")
        item = package.tft.get(self._model)
        if item is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_firmware_for_model",
                                     translation_placeholders={"model": self._model})
        url = runtime.firmware_url(item.path.name)
        if url is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_http_url")
        try:
            runtime.async_flash_display(self._panel, url)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        self._flash_target = package.version
        self._flashed = self.hass.loop.create_future()
        self._attr_in_progress = True
        self.async_write_ha_state()
        try:
            async with asyncio.timeout(FLASH_TIMEOUT):
                await self._flashed
        except TimeoutError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="flash_timeout",
                                     translation_placeholders={"minutes": str(FLASH_TIMEOUT // 60)}) from err
        finally:
            self._flashed = None
            self._flash_target = None
            self._attr_update_percentage = None
