"""Switch per panel: the screen is awake (a card) or asleep (the screensaver).

Off = the sleep_screen action with brightness 0 (dark until a touch or on); on = wake_screen.
The state follows the panel, so automations can also trigger on it.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .entity import NSPanelEntity


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(ScreenSwitch(entry, worker.name) for worker in entry.runtime_data.workers.values())


class ScreenSwitch(NSPanelEntity, SwitchEntity):

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        super().__init__(entry, panel, "screen")

    @property
    def is_on(self) -> bool | None:
        if self._panel not in self.runtime.panel_page:
            return None  # the panel has not shown a page yet
        return not self.runtime.on_screensaver(self._panel)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.runtime.async_wake(self._panel)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.runtime.async_sleep(self._panel, 0)
