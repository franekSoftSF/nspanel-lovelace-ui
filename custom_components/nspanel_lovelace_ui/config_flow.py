"""Config flow: point the integration at panels.yaml, optionally importing AppDaemon apps.yaml."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .config import (
    ConfigError,
    ConfigExistsError,
    PathOutsideConfigError,
    import_config,
    load_config,
    resolve_path,
)
from .const import CONF_CONFIG_FILE, CONF_IMPORT_FILE, DEFAULT_CONFIG_FILE, DOMAIN

_LOGGER = logging.getLogger(__name__)

_TEXT = selector.TextSelector()


class NSPanelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NSPanel Lovelace UI."""

    VERSION = 1

    async def _async_validate(self, user_input: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        config_dir = self.hass.config.config_dir
        try:
            target = resolve_path(config_dir, user_input[CONF_CONFIG_FILE])
            if source_name := (user_input.get(CONF_IMPORT_FILE) or "").strip():
                source = resolve_path(config_dir, source_name)
                result = await self.hass.async_add_executor_job(import_config, source, target)
                if result.warnings:
                    for warning in result.warnings:
                        _LOGGER.warning("Import: %s", warning)
                    persistent_notification.async_create(
                        self.hass,
                        "\n".join(f"- {warning}" for warning in result.warnings),
                        title=f"NSPanel Lovelace UI: {result.format} import",
                        notification_id=f"{DOMAIN}_import",
                    )
            settings = await self.hass.async_add_executor_job(load_config, target)
        except PathOutsideConfigError:
            errors["base"] = "path_outside_config"
        except ConfigExistsError:
            errors[CONF_CONFIG_FILE] = "config_exists"
        except ConfigError as err:
            errors["base"] = "invalid_config"
            placeholders["error"] = str(err)
        else:
            if not settings.get("use_ha_api") and not self.hass.config_entries.async_entries("mqtt"):
                errors["base"] = "mqtt_not_configured"
        return errors, placeholders

    def _schema(self, defaults: dict[str, Any], with_import: bool) -> vol.Schema:
        fields: dict[Any, Any] = {
            vol.Required(CONF_CONFIG_FILE, default=defaults.get(CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE)): _TEXT,
        }
        if with_import:
            fields[vol.Optional(CONF_IMPORT_FILE, default=defaults.get(CONF_IMPORT_FILE, ""))] = _TEXT
        return vol.Schema(fields)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        if user_input is not None:
            errors, placeholders = await self._async_validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title="NSPanel Lovelace UI",
                    data={CONF_CONFIG_FILE: user_input[CONF_CONFIG_FILE]},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input or {}, with_import=True),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"error": ""}
        if user_input is not None:
            errors, placeholders = await self._async_validate(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_CONFIG_FILE: user_input[CONF_CONFIG_FILE]})
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._schema(user_input or dict(entry.data), with_import=True),
            errors=errors,
            description_placeholders=placeholders,
        )
