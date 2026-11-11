"""Shared base of the per-panel entities (one device per panel)."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_PANEL_STATE


class NSPanelEntity(Entity):
    """Entity of one panel; refreshed when the runtime reports a change of that panel."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry, panel: str, key: str) -> None:
        self._entry = entry
        self._panel = panel
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{panel}_{key}"
        settings = entry.runtime_data.worker_by_name(panel).settings
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{panel}")},
            name=f"NSPanel {panel}",
            manufacturer="Sonoff",
            model=f"NSPanel ({settings.get('model', 'eu')})",
        )

    @property
    def runtime(self):
        return self._entry.runtime_data

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_PANEL_STATE, self._on_panel_state))

    @callback
    def _on_panel_state(self, panel: str) -> None:
        if panel == self._panel:
            self.async_write_ha_state()
