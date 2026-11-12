"""Card editor side of the shared schema (the rules live in backend/config_schema.py)."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from .backend.config_schema import CARD_TYPES, CARDS, Issue, collect_issues, schema_json  # noqa: F401


class EditorError(Exception):
    """A websocket request cannot be answered (code is sent to the editor)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ConflictError(Exception):
    """The file changed on disk since the editor loaded it."""


@lru_cache(maxsize=1)
def icon_picker() -> dict:
    """Blocking: picker data for the editor (frontend/mdi-icons.json, made by update_mdi.py).

    Only icons the panel font has: [name, "alias alias", [tag indexes], (1 if deprecated)] rows
    and the MDI categories ("tags") they refer to.
    """
    return json.loads((Path(__file__).parent / "frontend" / "mdi-icons.json").read_text(encoding="utf-8"))


def default_icon(entity_id: str, state) -> str | None:
    """MDI name the panel shows for an entity row without an icon (None: no icon, e.g. delete).

    The same rules the cards use (backend/ha_icons.py): domain, state, device_class.
    """
    from .backend import ha_icons

    if not entity_id or entity_id == "delete":
        return None
    if entity_id.startswith(("navigate.", "iText.")):
        return "gesture-tap-button"
    if entity_id.startswith("service."):
        return ha_icons.default_icon_name("script", None)  # like a script unless a status entity is set
    if state is None:
        return None  # the panel shows "not found"
    domain = entity_id.split(".", 1)[0]
    attributes = state.attributes
    return ha_icons.default_icon_name(domain, state.state, attributes.get("device_class"),
                                      attributes.get("media_content_type"))
