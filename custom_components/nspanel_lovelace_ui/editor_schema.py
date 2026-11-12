"""Card editor side of the shared schema (the rules live in backend/config_schema.py)."""
from __future__ import annotations

from functools import lru_cache

from .backend.config_schema import CARD_TYPES, CARDS, Issue, collect_issues, schema_json  # noqa: F401


class EditorError(Exception):
    """A websocket request cannot be answered (code is sent to the editor)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ConflictError(Exception):
    """The file changed on disk since the editor loaded it."""


@lru_cache(maxsize=1)
def icon_names() -> list[str]:
    """MDI names the panel fonts contain (same mapping the backend uses)."""
    from .backend.libs.icon_mapping import icons

    return sorted(icons)
