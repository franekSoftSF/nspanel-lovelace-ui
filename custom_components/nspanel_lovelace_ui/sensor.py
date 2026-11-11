"""Sensor per panel: the page the panel shows (screensaver or the card title)."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .entity import NSPanelEntity


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(CurrentPage(entry, worker.name) for worker in entry.runtime_data.workers.values())


class CurrentPage(NSPanelEntity, SensorEntity):

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        super().__init__(entry, panel, "page")

    @property
    def _page(self) -> dict[str, Any]:
        return self.runtime.panel_page.get(self._panel, {})

    @property
    def native_value(self) -> str | None:
        page = self._page
        if not page:
            return None
        return "screensaver" if page["type"].startswith("screensaver") else page["title"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        page = self._page
        return {"card_type": page.get("type"), "card_key": page.get("key")} if page else {}
