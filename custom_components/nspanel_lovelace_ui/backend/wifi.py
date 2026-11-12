"""Wi-Fi QR codes for cardQR (the ``wifi:`` option): build, parse and redact ``WIFI:`` strings.

Format (ZXing "Wi-Fi network config", read by Android and iOS cameras):
    WIFI:T:WPA;S:<ssid>;P:<password>;H:true;;
Special characters \\ ; , : " in the SSID and the password are escaped with a backslash.
The password never goes to the log: redact() hides it in logged panel messages.
"""
from __future__ import annotations

import re
from typing import Any

SECURITY = ("WPA", "WEP", "nopass")
SHOW = ("none", "ssid", "ssid_password")
PASSWORD_SOURCES = ("password", "passwordEntity", "passwordSecret")
SSID_MAX_BYTES = 32
QR_MAX_BYTES = 80  # HMI cardQR keeps the code in vaQR (Max. Text Size 80)

_SPECIAL = re.compile(r'([\\;,:"])')
_FIELD = re.compile(r'([A-Z]+):((?:\\.|[^;\\])*);')
_REDACT = re.compile(r'(WIFI:(?:[^~]*?;)?P:)((?:\\.|[^;\\~])*)')
_ROW = re.compile(r"(~text~iText\.wifi_password~[^~]*~[^~]*~[^~]*~)([^~]*)")  # ~type~id~icon~colour~name~value
_HEX = re.compile(r"^[0-9A-Fa-f]+$")


def escape(value: str) -> str:
    return _SPECIAL.sub(r"\\\1", value)


def unescape(value: str) -> str:
    return re.sub(r"\\(.)", r"\1", value)


def build(ssid: str, security: str = "WPA", password: str = "", hidden: bool = False) -> str:
    """The QR text for a network; no password for an open network ("nopass")."""
    security = security if security in SECURITY else "WPA"
    text = f"WIFI:T:{security};S:{escape(ssid)};"
    if security != "nopass" and password:
        text += f"P:{escape(password)};"
    if hidden:
        text += "H:true;"
    return text + ";"


def parse(text: Any) -> dict[str, Any] | None:
    """Fields of a WIFI: string (any field order), None if it is not one."""
    if not isinstance(text, str) or not text.startswith("WIFI:"):
        return None
    fields = {key: unescape(value) for key, value in _FIELD.findall(text[5:])}
    if "S" not in fields:
        return None
    kind = fields.get("T", "").upper()
    security = "nopass" if kind in ("", "NOPASS") else "WEP" if kind == "WEP" else "WPA"  # WPA2/WPA3/SAE -> WPA
    result: dict[str, Any] = {"ssid": fields["S"], "security": security}
    if security != "nopass" and fields.get("P"):
        result["password"] = fields["P"]
    if fields.get("H", "").lower() == "true":
        result["hidden"] = True
    return result


def redact(message: str) -> str:
    """Hide Wi-Fi passwords in a panel message before it is logged (the code and the password row)."""
    if "WIFI:" in message:
        message = _REDACT.sub(r"\1***", message)
    if "iText.wifi_password~" in message:
        message = _ROW.sub(r"\1***", message)
    return message


def password_problem(security: str, password: str) -> str | None:
    """Message code if the password cannot work for this security type (templates are not checked)."""
    if security == "nopass" or password.startswith("ha:"):
        return None
    if security == "WEP":
        ok = len(password) in (5, 13) or (len(password) in (10, 26) and _HEX.match(password))
        return None if ok else "wifi_wep_length"
    ok = 8 <= len(password) <= 63 or (len(password) == 64 and _HEX.match(password))
    return None if ok else "wifi_wpa_length"
