"""Button per panel: wake the screen up (like a touch on the screensaver)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .entity import NSPanelEntity


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(WakeButton(entry, worker.name) for worker in entry.runtime_data.workers.values())


class WakeButton(NSPanelEntity, ButtonEntity):

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        super().__init__(entry, panel, "wake")

    async def async_press(self) -> None:
        self.runtime.async_wake(self._panel)
