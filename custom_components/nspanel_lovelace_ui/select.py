"""Select per panel: show one of the configured cards (e.g. a camera card when the doorbell rings)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NSPanelConfigEntry
from .const import DOMAIN
from .entity import NSPanelEntity


async def async_setup_entry(hass: HomeAssistant, entry: NSPanelConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(CardSelect(entry, worker.name) for worker in entry.runtime_data.workers.values())


class CardSelect(NSPanelEntity, SelectEntity):
    """Options are the card titles (a duplicate title gets its key or a number)."""

    def __init__(self, entry: NSPanelConfigEntry, panel: str) -> None:
        super().__init__(entry, panel, "card")

    def _options(self) -> dict[str, str]:
        options: dict[str, str] = {}
        for card in self.runtime.cards(self._panel):
            label = card["title"]
            if label in options:
                label = f"{label} ({card['key']})" if card["key"] else f"{label} ({len(options) + 1})"
            options[label] = card["iid"]
        return options

    @property
    def options(self) -> list[str]:
        return list(self._options())

    @property
    def current_option(self) -> str | None:
        iid = self.runtime.panel_page.get(self._panel, {}).get("iid")
        return next((label for label, card in self._options().items() if card == iid), None)

    async def async_select_option(self, option: str) -> None:
        iid = self._options().get(option)
        if iid is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_card",
                                         translation_placeholders={"card": option})
        self.runtime.async_navigate(self._panel, iid)
