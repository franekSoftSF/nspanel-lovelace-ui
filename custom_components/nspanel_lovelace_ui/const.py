"""Constants for the NSPanel Lovelace UI integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "nspanel_lovelace_ui"
CONF_CONFIG_FILE: Final = "config_file"
CONF_IMPORT_FILE: Final = "import_file"
CONF_DISABLE_APPS: Final = "disable_appdaemon"
DEFAULT_CONFIG_FILE: Final = "nspanel_lovelace_ui/panels.yaml"
ESPHOME_EVENT: Final = "esphome.nspanel.data"
SERVICE_RELOAD: Final = "reload"
SERVICE_UPDATE_BERRY_DRIVER: Final = "update_berry_driver"
SIGNAL_PANEL_STATE: Final = f"{DOMAIN}_panel_state"
FIRMWARE_FOLDER: Final = "nspanel_lovelace_ui/firmware"
CONF_FIRMWARE_BASE_URL: Final = "firmware_base_url"
CONF_FIRMWARE_DOWNLOAD: Final = "firmware_download"
SERVICE_DOWNLOAD_FIRMWARE: Final = "download_firmware"
DATA_DOWNLOAD_ATTEMPTED: Final = f"{DOMAIN}_download_attempted"
ATTR_PANEL: Final = "panel"
