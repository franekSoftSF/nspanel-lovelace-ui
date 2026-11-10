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


def load_config(path: Path) -> dict[str, Any]:
    """Parse and validate panels.yaml (same rules as the add-on's editor)."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ConfigError(f"File not found: {path}") from err
    except OSError as err:
        raise ConfigError(f"Cannot read {path}: {err}") from err
    config = validate(parse_yaml(text))
    for panel in config["nspanels"].values():
        if config.get("use_ha_api"):
            continue
        for key in ("panelRecvTopic", "panelSendTopic"):
            topic = panel[key]
            if any(char in topic for char in "+#") or "\x00" in topic:
                raise ConfigError(f"{key} must be a plain MQTT topic without wildcards: {topic}")
    return config


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
