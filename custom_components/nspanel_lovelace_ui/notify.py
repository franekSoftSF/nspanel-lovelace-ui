"""Notify entity per panel: notify.send_message shows the text on the panel."""
from __future__ import annotations

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .entity import NSPanelEntity


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(PanelNotify(entry, worker.name) for worker in entry.runtime_data.workers.values())


class PanelNotify(NSPanelEntity, NotifyEntity):
    """On the screensaver the text replaces the weather; on a card it opens a notification page."""

    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        super().__init__(entry, panel, "notification")

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        self.runtime.async_notify(self._panel, message, title or "")
