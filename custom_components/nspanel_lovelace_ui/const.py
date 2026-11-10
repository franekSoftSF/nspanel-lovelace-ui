"""Constants for the NSPanel Lovelace UI integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "nspanel_lovelace_ui"
CONF_CONFIG_FILE: Final = "config_file"
CONF_IMPORT_FILE: Final = "import_file"
DEFAULT_CONFIG_FILE: Final = "nspanel_lovelace_ui/panels.yaml"
ESPHOME_EVENT: Final = "esphome.nspanel.data"
SERVICE_RELOAD: Final = "reload"
