"""Reading, validating and importing panels.yaml (blocking: run in the executor)."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml

from .backend.config_manager import ConfigError, import_yaml, parse_yaml, validate


class PathOutsideConfigError(ConfigError):
    """The file is not inside the Home Assistant configuration folder."""


class ConfigExistsError(ConfigError):
    """An import would overwrite an existing panels.yaml."""


@dataclass
class ImportResult:
    format: str
    warnings: list[str] = field(default_factory=list)


def resolve_path(config_dir: str, relative: str) -> Path:
    """Resolve a user-entered path; only files inside the HA config folder are allowed."""
    base = Path(config_dir).resolve()
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise PathOutsideConfigError(relative)
    return path


class _DuplicateKeyLoader(yaml.SafeLoader):
    """PyYAML semantics (the last duplicate wins), but remember every duplicate."""

    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self.duplicates: list[str] = []

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                self.duplicates.append(f"line {key_node.start_mark.line + 1}: duplicate key '{key}' (the last one is used)")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _parse_lenient(text: str) -> tuple[dict[str, Any], list[str]]:
    """Strict parse (add-on editor rules); duplicate keys only warn, like AppDaemon and the add-on runtime."""
    try:
        return parse_yaml(text), []
    except ConfigError as err:
        if not str(err).startswith("Invalid YAML: Duplicate YAML key"):
            raise
    loader = _DuplicateKeyLoader(text)
    try:
        data = loader.get_single_data()
    except yaml.YAMLError as err:
        raise ConfigError(f"Invalid YAML: {err}") from err
    finally:
        loader.dispose()
    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a YAML mapping.")
    return data, loader.duplicates


def load_config(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Parse and validate panels.yaml; returns the config and non-fatal warnings."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ConfigError(f"File not found: {path}") from err
    except OSError as err:
        raise ConfigError(f"Cannot read {path}: {err}") from err
    data, warnings = _parse_lenient(text)
    config = validate(data)
    for name, panel in config["nspanels"].items():
        font_id = panel.get("largeIconFontId", 7 if panel.get("model", "eu") == "us-p" else 8)
        if type(font_id) is not int or not 0 <= font_id <= 9:
            raise ConfigError(f"{name}.largeIconFontId must be a font ID from 0 to 9 (the HMI reads one digit)")
        if panel.get("weatherIcons", "color") not in ("color", "font"):
            raise ConfigError(f"{name}.weatherIcons must be color or font")
        base = panel.get("weatherPictureBase")
        if base is not None and (type(base) is not int or not 0 <= base <= 1000):
            raise ConfigError(f"{name}.weatherPictureBase must be the picture ID of 00-main-clear-day")
        if "timeTemplate" in panel and not (isinstance(panel["timeTemplate"], str) and panel["timeTemplate"].strip()):
            raise ConfigError(f"{name}.timeTemplate must be a template text")
        if config.get("use_ha_api"):
            continue
        for key in ("panelRecvTopic", "panelSendTopic"):
            topic = panel[key]
            if any(char in topic for char in "+#") or "\x00" in topic:
                raise ConfigError(f"{key} must be a plain MQTT topic without wildcards: {topic}")
    return config, warnings


def import_config(source: Path, target: Path) -> ImportResult:
    """Convert an AppDaemon apps.yaml (or an add-on panels.yaml) into ``target``.

    Never overwrites: an existing target raises ConfigExistsError.
    """
    if target.exists():
        raise ConfigExistsError(str(target))
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as err:
        raise ConfigError(f"Cannot read {source}: {err}") from err
    result = import_yaml(text)
    if result["errors"]:
        raise ConfigError("; ".join(result["errors"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Imported from {source.name} ({result['format']} format) by the NSPanel Lovelace UI integration.\n"
              "# Review the warnings in the Home Assistant log / notification.\n")
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(header + yaml.safe_dump(result["config"], allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    os.replace(tmp, target)
    return ImportResult(result["format"], list(result["warnings"]))
