"""panels.yaml schema and validation - the one source of truth.

Used by the integration when it loads the file (config_manager.validate raises the first error)
and by the card editor (field forms from schema_json(), issues per field from collect_issues()).

An issue has a path into the configuration (e.g. ["nspanels", "hall", "cards", 0, "entity"]), a
code (translated by the editor, see MESSAGES), a severity ("error" blocks loading and saving,
"warning" does not) and parameters for the message.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from urllib.parse import urlsplit

from .libs.brightness import validate_brightness

# --- schema ---------------------------------------------------------------------------------


def L(en: str, pl: str) -> dict[str, str]:  # noqa: N802 - short label helper
    return {"en": en, "pl": pl}


def F(key: str, kind: str, label: dict, **extra: Any) -> dict[str, Any]:  # noqa: N802
    """A field: key, kind (string/template/int/bool/select/multiselect/entity/icon/color/brightness/
    item/items/strings/theme/time), label, and optional help, required, default, options,
    domains, min, max, advanced, cards (card types it applies to), weather (weather items only)."""
    return {"key": key, "kind": kind, "label": label, **extra}


def O(value: str, en: str, pl: str) -> dict[str, Any]:  # noqa: N802
    return {"value": value, "label": L(en, pl)}


CARD_TYPES = ["cardEntities", "cardGrid", "cardQR", "cardPower", "cardMedia", "cardThermo", "cardAlarm",
              "cardUnlock"]
SCREENSAVER_TYPES = ["screensaver", "screensaver2", "screensaver3"]
FONTS = ["small", "medium", "medium-icon", "large", "large-icon"]
PSEUDO_PREFIXES = ("navigate.", "iText.", "service.")
PSEUDO_ENTITIES = ("delete",)
HVAC_MODES = ["off", "heat", "cool", "heat_cool", "auto", "dry", "fan_only"]
ALARM_MODES = ["arm_home", "arm_away", "arm_night", "arm_vacation"]
THEME_KEYS = ["background", "time", "timeAMPM", "date", "tMainText", "tForecast1", "tForecast2", "tForecast3",
              "tForecast4", "tForecast1Val", "tForecast2Val", "tForecast3Val", "tForecast4Val", "bar",
              "tMainTextAlt2", "tTimeAdd"]

ITEM_FIELDS = [
    F("entity", "entity", L("Entity", "Encja"), required=True, pseudo=True,
      help=L("Home Assistant entity, or delete (empty slot), navigate.<card key>, iText.<text>, "
             "service.<domain>.<action>",
             "Encja Home Assistant albo delete (puste miejsce), navigate.<klucz karty>, iText.<tekst>, "
             "service.<domena>.<akcja>")),
    F("name", "template", L("Name", "Nazwa"), help=L("Text or a template (ha: …); default: friendly name",
                                                      "Tekst albo szablon (ha: …); domyślnie nazwa encji")),
    F("icon", "icon", L("Icon", "Ikona")),
    F("color", "color", L("Colour", "Kolor")),
    F("font", "select", L("Font", "Czcionka"), cards=["cardGrid", "statusIcon"],
      options=[O("small", "Small", "Mała"), O("medium", "Medium", "Średnia"),
               O("medium-icon", "Medium icon", "Średnia ikona"), O("large", "Large", "Duża"),
               O("large-icon", "Large icon (64 px, firmware 55)", "Duża ikona (64 px, firmware 55)")]),
    F("attribute", "string", L("Attribute", "Atrybut"), weather=True, default="temperature"),
    F("day", "int", L("Forecast day", "Dzień prognozy"), weather=True, min=0, max=14),
    F("hour", "int", L("Forecast hour", "Godzina prognozy"), weather=True, min=0, max=48),
    F("unit", "string", L("Unit", "Jednostka"), weather=True),
    F("speed", "template", L("Speed (-120…120)", "Prędkość (-120…120)"), cards=["cardPower"]),
    F("state", "string", L("Show only in state", "Pokaż tylko w stanie"), advanced=True),
    F("state_not", "string", L("Hide in state", "Ukryj w stanie"), advanced=True),
    F("state_template", "template", L("Hide when template is true", "Ukryj, gdy szablon jest prawdziwy"),
      advanced=True),
    F("status", "entity", L("Status entity", "Encja statusu"), advanced=True),
    F("data", "mapping", L("Action data", "Dane akcji"), advanced=True, pseudo_only="service."),
    F("effectList", "strings", L("Effect list", "Lista efektów"), advanced=True, domains=["light"]),
]

COMMON_CARD_FIELDS = [
    F("title", "string", L("Title", "Tytuł")),
    F("key", "string", L("Key (for navigate.<key>)", "Klucz (do navigate.<klucz>)")),
]
NAV_FIELDS = [
    F("navItem1", "item", L("Left button", "Lewy przycisk"), advanced=True, entity_optional=True),
    F("navItem2", "item", L("Right button", "Prawy przycisk"), advanced=True, entity_optional=True),
    F("sleepTimeout", "int", L("Screensaver after (s)", "Wygaszacz po (s)"), advanced=True, min=0),
]

CARDS: dict[str, dict[str, Any]] = {
    "cardEntities": {"label": L("Entities", "Encje"), "icon": "mdi:format-list-bulleted",
                     "fields": COMMON_CARD_FIELDS + NAV_FIELDS, "items": True},
    "cardGrid": {"label": L("Grid", "Siatka"), "icon": "mdi:view-grid",
                 "fields": COMMON_CARD_FIELDS + NAV_FIELDS, "items": True},
    "cardQR": {"label": L("QR code", "Kod QR"), "icon": "mdi:qrcode",
               "fields": COMMON_CARD_FIELDS + [
                   F("qrCode", "template", L("QR content", "Treść kodu QR"), required=True,
                     help=L("e.g. WIFI:S:MyNet;T:WPA;P:secret;; or ha: template",
                            "np. WIFI:S:MojaSiec;T:WPA;P:haslo;; albo szablon ha:"))] + NAV_FIELDS,
               "items": True},
    "cardPower": {"label": L("Power flow", "Przepływ energii"), "icon": "mdi:transmission-tower",
                  "fields": COMMON_CARD_FIELDS + NAV_FIELDS, "items": True},
    "cardMedia": {"label": L("Media player", "Odtwarzacz"), "icon": "mdi:play-box",
                  "fields": COMMON_CARD_FIELDS + [
                      F("entity", "entity", L("Media player", "Odtwarzacz"), required=True,
                        domains=["media_player"])] + NAV_FIELDS, "items": True},
    "cardThermo": {"label": L("Thermostat", "Termostat"), "icon": "mdi:thermostat",
                   "fields": COMMON_CARD_FIELDS + [
                       F("entity", "entity", L("Climate entity", "Encja klimatu"), required=True,
                         domains=["climate"]),
                       F("supported_modes", "multiselect", L("HVAC modes", "Tryby"),
                         options=[O(mode, mode, mode) for mode in HVAC_MODES])] + NAV_FIELDS, "items": False},
    "cardAlarm": {"label": L("Alarm", "Alarm"), "icon": "mdi:shield-home",
                  "fields": COMMON_CARD_FIELDS + [
                      F("entity", "entity", L("Alarm panel", "Panel alarmowy"), required=True,
                        domains=["alarm_control_panel"]),
                      F("supported_modes", "multiselect", L("Arm modes", "Tryby uzbrajania"),
                        options=[O(mode, mode, mode) for mode in ALARM_MODES])] + NAV_FIELDS, "items": False},
    "cardUnlock": {"label": L("Unlock (PIN)", "Odblokowanie (PIN)"), "icon": "mdi:lock-open-variant",
                   "fields": COMMON_CARD_FIELDS + [
                       F("pin", "string", L("PIN", "PIN"), required=True, pattern=r"^\d{1,8}$"),
                       F("destination", "navigate", L("Opens card", "Otwiera kartę"), required=True)] + NAV_FIELDS,
                   "items": False},
}

SCREENSAVER_FIELDS = [
    F("type", "select", L("Layout", "Układ"), default="screensaver",
      options=[O("screensaver", "Weather (default)", "Pogoda (domyślny)"),
               O("screensaver2", "Alternative", "Alternatywny"),
               O("screensaver3", "Icons over the buttons", "Ikony nad przyciskami")]),
    F("statusIcon1", "item", L("Status icon 1", "Ikona statusu 1")),
    F("statusIcon2", "item", L("Status icon 2", "Ikona statusu 2")),
    F("doubleTapToUnlock", "bool", L("Double tap to leave", "Podwójne dotknięcie, aby wyjść"), default=False),
    F("disable", "bool", L("No screensaver", "Bez wygaszacza"), default=False),
    F("theme", "theme", L("Colours", "Kolory"), advanced=True, keys=THEME_KEYS),
    F("sleepTimeout", "int", L("Screensaver after (s)", "Wygaszacz po (s)"), advanced=True, min=0),
]

PANEL_FIELDS = [
    F("panelRecvTopic", "string", L("Receive topic", "Temat odbioru"), required=True,
      help=L("e.g. tele/tasmota_XXXXXX/RESULT", "np. tele/tasmota_XXXXXX/RESULT")),
    F("panelSendTopic", "string", L("Send topic", "Temat wysyłania"), required=True,
      help=L("e.g. cmnd/tasmota_XXXXXX/CustomSend", "np. cmnd/tasmota_XXXXXX/CustomSend")),
    F("model", "select", L("Model", "Model"), default="eu",
      options=[O("eu", "EU", "EU"), O("us-p", "US portrait", "US pionowy"), O("us-l", "US landscape", "US poziomy")]),
    F("locale", "string", L("Language", "Język"), required=True, inherit=True, default="en_US",
      help=L("e.g. pl_PL, en_US", "np. pl_PL, en_US")),
    F("timeZone", "string", L("Time zone", "Strefa czasowa"), inherit=True,
      help=L("e.g. Europe/Warsaw; default: Home Assistant's", "np. Europe/Warsaw; domyślnie strefa HA")),
    F("timeFormat", "string", L("Time format", "Format godziny"), required=True, inherit=True, default="%H:%M"),
    F("dateFormat", "string", L("Date format", "Format daty"), required=True, inherit=True, default="full",
      help=L("Babel: full, long, medium, short or a pattern", "Babel: full, long, medium, short albo wzorzec")),
    F("sleepTimeout", "int", L("Screensaver after (s)", "Wygaszacz po (s)"), default=20, min=0),
    F("sleepBrightness", "brightness", L("Screensaver brightness", "Jasność wygaszacza"), default=10),
    F("screenBrightness", "brightness", L("Screen brightness", "Jasność ekranu"), default=100),
    F("defaultCard", "navigate", L("Default card", "Karta domyślna")),
    F("updateMode", "select", L("Display updates on the panel", "Aktualizacje ekranu na panelu"),
      default="auto-notify",
      options=[O("auto-notify", "Ask on the panel", "Pytaj na panelu"), O("auto", "Automatic", "Automatycznie"),
               O("manual", "Only from Home Assistant", "Tylko z Home Assistant")]),
    F("weatherIcons", "select", L("Weather icons", "Ikony pogody"), default="color",
      options=[O("color", "Colour pictures (firmware 55)", "Kolorowe obrazki (firmware 55)"),
               O("font", "Font icons", "Ikony z czcionki")]),
    F("timeTemplate", "template", L("Text instead of the clock", "Tekst zamiast zegara"), advanced=True),
    F("timeAdditionalTemplate", "template", L("Text after the time", "Tekst po godzinie"), advanced=True),
    F("dateAdditionalTemplate", "template", L("Text after the date", "Tekst po dacie"), advanced=True),
    F("temp_unit", "select", L("Thermostat unit", "Jednostka termostatu"), advanced=True, default="celsius",
      options=[O("celsius", "°C", "°C"), O("fahrenheit", "°F", "°F")]),
    F("defaultBackgroundColor", "select", L("Background", "Tło"), advanced=True, default="ha-dark",
      options=[O("ha-dark", "Home Assistant dark", "Ciemne Home Assistant"), O("black", "Black", "Czarne")]),
    F("sleepTracking", "entity", L("Sleep tracking entity", "Encja śledzenia snu"), advanced=True),
    F("sleepTrackingZones", "strings", L("Sleep states", "Stany snu"), advanced=True,
      default=["not_home", "off"]),
    F("sleepOverride", "override", L("Brightness override", "Wymuszenie jasności"), advanced=True),
    F("largeIconFontId", "int", L("Large icon font ID", "ID czcionki dużych ikon"), advanced=True, min=0, max=9),
    F("weatherPictureBase", "int", L("Weather picture ID", "ID obrazków pogody"), advanced=True, min=0,
      max=1000),
    F("featExperimentalSliders", "int", L("Experimental sliders", "Eksperymentalne suwaki"), advanced=True,
      min=0, max=1),
]

GLOBAL_FIELDS = [
    F("use_ha_api", "bool", L("ESPHome panels (use_ha_api)", "Panele ESPHome (use_ha_api)"), default=False),
    F("firmware_download", "bool", L("Download the display firmware", "Pobieraj firmware ekranu"), default=True),
    F("firmware_base_url", "string", L("Firmware address for the panels", "Adres firmware dla paneli"),
      help=L("Plain HTTP, e.g. http://192.168.1.10:8123", "Zwykłe HTTP, np. http://192.168.1.10:8123")),
]

MESSAGES = {
    "required": L("Required.", "Wymagane."),
    "type_string": L("Must be text.", "Musi być tekstem."),
    "type_int": L("Must be a whole number.", "Musi być liczbą całkowitą."),
    "type_bool": L("Must be true or false.", "Musi być prawdą albo fałszem."),
    "type_list": L("Must be a list.", "Musi być listą."),
    "type_mapping": L("Must be an object.", "Musi być obiektem."),
    "range": L("Must be from {min} to {max}.", "Musi być od {min} do {max}."),
    "min": L("Must be at least {min}.", "Musi być co najmniej {min}."),
    "one_of": L("Allowed: {options}.", "Dozwolone: {options}."),
    "pattern": L("Invalid format.", "Nieprawidłowy format."),
    "no_panels": L("Add at least one panel.", "Dodaj co najmniej jeden panel."),
    "panel_name": L("Panel name must be text.", "Nazwa panelu musi być tekstem."),
    "unique_topic": L("Already used by panel {other}.", "Używany już przez panel {other}."),
    "topic_wildcard": L("No + or # (wildcards) allowed.", "Bez znaków + i # (symboli wieloznacznych)."),
    "send_topic_suffix": L("Must end with /CustomSend for firmware updates and the buzzer.",
                           "Musi kończyć się na /CustomSend dla aktualizacji firmware i buzzera."),
    "no_cards": L("Add at least one card.", "Dodaj co najmniej jedną kartę."),
    "unknown_card_type": L("Unknown card type {value}.", "Nieznany typ karty {value}."),
    "entity_format": L("Use domain.object_id (e.g. light.kitchen).", "Użyj domena.obiekt (np. light.kuchnia)."),
    "entity_missing": L("{entity} does not exist in Home Assistant.", "{entity} nie istnieje w Home Assistant."),
    "entity_domain": L("Expected {domains}.", "Oczekiwano: {domains}."),
    "navigate_missing": L("No card with key {target}.", "Brak karty z kluczem {target}."),
    "duplicate_key": L("Key {value} is used by another card.", "Klucz {value} ma już inna karta."),
    "brightness": L("{detail}", "{detail}"),
    "base_url": L("Must look like http://192.168.1.10:8123.", "Musi wyglądać jak http://192.168.1.10:8123."),
    "empty_template": L("Must not be empty.", "Nie może być puste."),
    "items_empty": L("This card shows nothing without entities.", "Bez encji ta karta nic nie pokaże."),
    "color": L("Use [r, g, b], #rrggbb or a number.", "Użyj [r, g, b], #rrggbb albo liczby."),
    "firmware_url": L("Must be an http:// URL without spaces or ;.", "Musi być adresem http:// bez spacji i ;."),
    "icon_unknown": L("{icon} is not in the panel icon font (MDI 7.4.47); the panel shows alert-circle-outline.",
                      "Ikony {icon} nie ma w foncie panelu (MDI 7.4.47); panel pokaże alert-circle-outline."),
}

ICON_PREFIXES = ("ha:", "text:")  # templates and plain text are not font icons


def icon_known(value: str) -> bool:
    """True if the panel font has this icon (mdi:name or name), or the value is not an icon name."""
    from .libs.icon_mapping import icons

    text = value.strip()
    return not text or text.startswith(ICON_PREFIXES) or text.removeprefix("mdi:") in icons


def schema_json() -> dict[str, Any]:
    """Everything the editor needs to draw its forms (no callables)."""
    return {"version": 1, "global": GLOBAL_FIELDS, "panel": PANEL_FIELDS, "screensaver": SCREENSAVER_FIELDS,
            "screensaver_types": SCREENSAVER_TYPES, "cards": CARDS, "card_types": CARD_TYPES,
            "item": ITEM_FIELDS, "fonts": FONTS, "theme_keys": THEME_KEYS, "messages": MESSAGES,
            "pseudo_prefixes": list(PSEUDO_PREFIXES), "pseudo_entities": list(PSEUDO_ENTITIES)}


# --- validation -----------------------------------------------------------------------------

@dataclass
class Issue:
    path: list
    code: str
    severity: str = "error"
    params: dict = field(default_factory=dict)

    def text(self) -> str:
        message = MESSAGES.get(self.code, {"en": self.code})["en"].format(**self.params)
        return f"{'.'.join(str(part) for part in self.path[1:]) or 'config'}: {message}"

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "code": self.code, "severity": self.severity, "params": self.params,
                "text": self.text()}


_ENTITY_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class _Checker:
    def __init__(self, entity_ids: set[str] | None) -> None:
        self.issues: list[Issue] = []
        self.entity_ids = entity_ids

    def add(self, path, code, severity="error", **params):
        self.issues.append(Issue(list(path), code, severity, params))

    def field(self, path, spec, value, *, required_value=None):
        kind = spec["kind"]
        if value is None:
            if spec.get("required"):
                self.add(path, "required")
            return
        if kind in ("string", "template", "navigate", "icon"):
            if kind == "icon" and isinstance(value, dict):  # state -> icon map
                for state, icon in value.items():
                    if isinstance(icon, str) and not icon_known(icon):
                        self.add([*path, state], "icon_unknown", "warning", icon=icon)
                return
            if isinstance(value, (dict, list)) or (kind in ("navigate", "icon") and not isinstance(value, str)):
                self.add(path, "type_string")
                return
            text = value if isinstance(value, str) else str(value)  # YAML numbers/booleans are fine as text
            if spec.get("required") and not text.strip():
                self.add(path, "required")
            if spec.get("pattern") and not re.match(spec["pattern"], text):
                self.add(path, "pattern")
            if kind == "icon" and not icon_known(text):
                self.add(path, "icon_unknown", "warning", icon=text)
        elif kind == "int":
            if type(value) is not int:
                self.add(path, "type_int")
                return
            if "max" in spec and "min" in spec and not spec["min"] <= value <= spec["max"]:
                self.add(path, "range", min=spec["min"], max=spec["max"])
            elif "min" in spec and value < spec["min"]:
                self.add(path, "min", min=spec["min"])
        elif kind == "bool":
            if type(value) is not bool:
                self.add(path, "type_bool")
        elif kind == "select":
            allowed = [option["value"] for option in spec["options"]]
            if value not in allowed and not (spec["key"] == "defaultBackgroundColor" and isinstance(value, int)):
                self.add(path, "one_of", options=", ".join(allowed))
        elif kind == "multiselect" or kind == "strings":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                self.add(path, "type_list")
        elif kind == "entity":
            self.entity(path, value, spec)
        elif kind == "color":
            self.color(path, value)
        elif kind == "brightness":
            try:
                validate_brightness(value)
            except ValueError as err:
                self.add(path, "brightness", detail=str(err))
        elif kind == "item":
            self.item(path, value, None, entity_required=not spec.get("entity_optional"))
        elif kind == "mapping":
            if not isinstance(value, dict):
                self.add(path, "type_mapping")
        elif kind == "theme":
            if not isinstance(value, dict):
                self.add(path, "type_mapping")
                return
            for key, color in value.items():
                self.color([*path, key], color)
        elif kind == "override":
            if not isinstance(value, dict):
                self.add(path, "type_mapping")
                return
            self.entity([*path, "entity"], value.get("entity"), {"required": True})
            if type(value.get("brightness", 0)) is not int or not 0 <= value.get("brightness", 0) <= 100:
                self.add([*path, "brightness"], "range", min=0, max=100)

    def color(self, path, value):
        if isinstance(value, dict):
            return  # state -> colour map
        if isinstance(value, int) and not isinstance(value, bool):
            return
        if isinstance(value, list) and len(value) == 3 and all(type(c) is int and 0 <= c <= 255 for c in value):
            return
        if isinstance(value, str) and (value.startswith("ha:") or _HEX.match(value) or value.startswith("rgb(")
                                       or value.startswith("[")):
            return
        self.add(path, "color")

    def entity(self, path, value, spec, *, pseudo=False):
        if value is None:
            if spec.get("required"):
                self.add(path, "required")
            return
        if not isinstance(value, str) or not value.strip():
            self.add(path, "required" if value == "" else "type_string")
            return
        if pseudo and (value in PSEUDO_ENTITIES or value.startswith(PSEUDO_PREFIXES)):
            return
        if not _ENTITY_ID.match(value):
            self.add(path, "entity_format")
            return
        domains = spec.get("domains")
        if domains and value.split(".")[0] not in domains:
            self.add(path, "entity_domain", "warning", domains=", ".join(domains))
        if self.entity_ids is not None and value not in self.entity_ids:
            self.add(path, "entity_missing", "warning", entity=value)

    def item(self, path, item, card_type, entity_required=True):  # noqa: ARG002 - card_type for later rules
        if not isinstance(item, dict):
            self.add(path, "type_mapping")
            return
        for spec in ITEM_FIELDS:
            value = item.get(spec["key"])
            if spec["key"] == "entity":
                if value is not None or entity_required:
                    self.entity([*path, "entity"], value, spec, pseudo=True)
            elif value is not None:
                self.field([*path, spec["key"]], spec, value)

    def fields(self, path, specs, data, inherited=None):
        for spec in specs:
            value = data.get(spec["key"])
            if value is None and spec.get("inherit") and inherited is not None:
                value = inherited.get(spec["key"])
                if value is not None:
                    continue  # validated at the top level
            self.field([*path, spec["key"]], spec, value)


def collect_issues(config: Any, entity_ids: set[str] | None = None) -> list[Issue]:
    """All problems of a configuration; entity_ids enables 'does not exist' warnings."""
    check = _Checker(entity_ids)
    if not isinstance(config, dict):
        check.add([], "type_mapping")
        return check.issues
    panels = config.get("nspanels")
    if not isinstance(panels, dict):
        check.add(["nspanels"], "type_mapping")
        return check.issues
    if not panels:
        check.add(["nspanels"], "no_panels")
    check.fields([], GLOBAL_FIELDS, config)
    for key in ("locale", "timeZone", "timeFormat", "dateFormat"):
        if key in config and not isinstance(config[key], str):
            check.add([key], "type_string")
    if isinstance(config.get("firmware_base_url"), str):
        url = urlsplit(config["firmware_base_url"])
        if url.scheme != "http" or not url.hostname or url.path not in ("", "/") or url.query:
            check.add(["firmware_base_url"], "base_url")
    use_ha_api = config.get("use_ha_api") is True
    topics: dict[str, str] = {}
    for name, panel in panels.items():
        base = ["nspanels", name]
        if not isinstance(name, str) or not name.strip():
            check.add(base, "panel_name")
            continue
        if not isinstance(panel, dict):
            check.add(base, "type_mapping")
            continue
        check.fields(base, PANEL_FIELDS, panel, config)
        recv = panel.get("panelRecvTopic")
        if isinstance(recv, str) and recv.strip():
            if recv in topics:
                check.add([*base, "panelRecvTopic"], "unique_topic", other=topics[recv])
            topics.setdefault(recv, name)
        if not use_ha_api:
            for key in ("panelRecvTopic", "panelSendTopic"):
                topic = panel.get(key)
                if isinstance(topic, str) and (any(char in topic for char in "+#") or "\x00" in topic):
                    check.add([*base, key], "topic_wildcard")
            send = panel.get("panelSendTopic")
            if isinstance(send, str) and send.strip() and not send.endswith("/CustomSend"):
                check.add([*base, "panelSendTopic"], "send_topic_suffix", "warning")
        if panel.get("timeTemplate") is not None and isinstance(panel["timeTemplate"], str) \
                and not panel["timeTemplate"].strip():
            check.add([*base, "timeTemplate"], "empty_template")
        for key in ("displayFirmwareVersion",):
            if key in panel and (type(panel[key]) is not int or panel[key] < 16):
                check.add([*base, key], "min", min=16)
        for model in ("EU", "US-P", "US-L"):
            url = panel.get(f"displayURL-{model}")
            if url is not None and (not isinstance(url, str) or urlsplit(url).scheme != "http"
                                    or any(c.isspace() for c in url) or ";" in url):
                check.add([*base, f"displayURL-{model}"], "firmware_url")
        _screensaver(check, base, panel.get("screensaver"))
        keys = _cards(check, base, panel, config)
        for target_path, target in _navigate_targets(panel, base):
            if target != "UP" and target not in keys:
                check.add(target_path, "navigate_missing", "warning", target=target)
    return check.issues


def _screensaver(check: _Checker, base: list, screensaver: Any) -> None:
    path = [*base, "screensaver"]
    if screensaver is None:
        check.add(path, "required")
        return
    if not isinstance(screensaver, dict):
        check.add(path, "type_mapping")
        return
    check.fields(path, SCREENSAVER_FIELDS, screensaver)
    if "entity" in screensaver and not isinstance(screensaver["entity"], str):
        check.add([*path, "entity"], "type_string")
    entities = screensaver.get("entities", [])
    if not isinstance(entities, list):
        check.add([*path, "entities"], "type_list")
        return
    for index, item in enumerate(entities):
        check.item([*path, "entities", index], item, "screensaver")


def _cards(check: _Checker, base: list, panel: dict, config: dict) -> set[str]:
    keys: dict[str, list] = {}
    for list_key in ("cards", "hiddenCards"):
        cards = panel.get(list_key, config.get(list_key, []) if list_key == "hiddenCards" else None)
        path = [*base, list_key]
        if cards is None:
            check.add(path, "required")
            continue
        if not isinstance(cards, list):
            check.add(path, "type_list")
            continue
        if list_key == "cards" and not cards:
            check.add(path, "no_cards")
        for index, card in enumerate(cards):
            card_path = [*path, index]
            if not isinstance(card, dict):
                check.add(card_path, "type_mapping")
                continue
            card_type = card.get("type")
            if card_type not in CARDS:
                check.add([*card_path, "type"], "unknown_card_type", value=str(card_type))
                continue
            spec = CARDS[card_type]
            check.fields(card_path, spec["fields"], card)
            entities = card.get("entities", [])
            if not isinstance(entities, list):
                check.add([*card_path, "entities"], "type_list")
            else:
                for item_index, item in enumerate(entities):
                    check.item([*card_path, "entities", item_index], item, card_type)
                if spec["items"] and not entities and not card.get("entity"):
                    check.add([*card_path, "entities"], "items_empty", "warning")
            key = card.get("key")
            if isinstance(key, str) and key:
                if key in keys:
                    check.add([*card_path, "key"], "duplicate_key", "warning", value=key)
                keys.setdefault(key, card_path)
    return set(keys)


def _navigate_targets(panel: dict, base: list):
    """(path, target) of every navigate.<key> in a panel (defaultCard, destinations, items)."""
    def target(value):
        return value.split(".", 1)[1] if isinstance(value, str) and value.startswith("navigate.") else None

    if (value := target(panel.get("defaultCard"))) is not None:
        yield [*base, "defaultCard"], value
    for list_key in ("cards", "hiddenCards"):
        cards = panel.get(list_key)
        if not isinstance(cards, list):
            continue
        for index, card in enumerate(cards):
            if not isinstance(card, dict):
                continue
            path = [*base, list_key, index]
            if (value := target(card.get("destination"))) is not None:
                yield [*path, "destination"], value
            items = card.get("entities") if isinstance(card.get("entities"), list) else []
            for item_index, item in enumerate(items):
                if isinstance(item, dict) and (value := target(item.get("entity"))) is not None:
                    yield [*path, "entities", item_index, "entity"], value
