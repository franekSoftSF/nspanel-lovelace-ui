"""Weather conditions: MDI icon (day/night), colour (Home Assistant palette) and colour picture.

Used by the screensaver and weather entities. The colour pictures (Meteocons, MIT) are compiled
into firmware 55+ (HMI/BUILD.md); `PICTURES` fixes their order, so picture ID = base + index.
"""
from datetime import datetime

from .libs.helper import rgb_dec565

# HA condition -> (MDI day, MDI night)
_MDI = {
    "clear-night": ("weather-night", "weather-night"),
    "cloudy": ("weather-cloudy", "weather-cloudy"),
    "exceptional": ("weather-cloudy-alert", "weather-cloudy-alert"),
    "fog": ("weather-fog", "weather-fog"),
    "hail": ("weather-hail", "weather-hail"),
    "lightning": ("weather-lightning", "weather-lightning"),
    "lightning-rainy": ("weather-lightning-rainy", "weather-lightning-rainy"),
    "partlycloudy": ("weather-partly-cloudy", "weather-night-partly-cloudy"),
    "pouring": ("weather-pouring", "weather-pouring"),
    "rainy": ("weather-rainy", "weather-rainy"),
    "snowy": ("weather-snowy", "weather-snowy"),
    "snowy-rainy": ("weather-snowy-rainy", "weather-snowy-rainy"),
    "sunny": ("weather-sunny", "weather-night"),
    "windy": ("weather-windy", "weather-windy"),
    "windy-variant": ("weather-windy-variant", "weather-windy-variant"),
}

# Colours of the Home Assistant frontend weather icons (one colour per glyph on the panel).
_SUN = [253, 217, 60]
_MOON = [252, 244, 151]
_CLOUD = [212, 212, 212]
_RAIN = [48, 179, 255]
_POURING = [30, 136, 229]
_LIGHTNING = [255, 193, 7]
_SNOW = [232, 244, 255]
_SLEET = [160, 200, 240]
_MIST = [180, 180, 180]
_ALERT = [244, 67, 54]
_COLORS = {
    "clear-night": _MOON,
    "cloudy": _CLOUD,
    "exceptional": _ALERT,
    "fog": _MIST,
    "hail": _SNOW,
    "lightning": _LIGHTNING,
    "lightning-rainy": _LIGHTNING,
    "partlycloudy": _CLOUD,
    "pouring": _POURING,
    "rainy": _RAIN,
    "snowy": _SNOW,
    "snowy-rainy": _SLEET,
    "sunny": _SUN,
    "windy": _MIST,
    "windy-variant": _MIST,
}

# Order of the colour pictures in the HMI (do not reorder: IDs are base + index).
PICTURES = [
    "clear-day", "clear-night", "cloudy", "partly-cloudy-day", "partly-cloudy-night",
    "drizzle", "rain", "thunderstorms", "thunderstorms-rain", "snow", "sleet", "hail",
    "fog", "wind", "tornado",
]
_PICTURE = {
    "clear-night": ("clear-night", "clear-night"),
    "cloudy": ("cloudy", "cloudy"),
    "exceptional": ("tornado", "tornado"),
    "fog": ("fog", "fog"),
    "hail": ("hail", "hail"),
    "lightning": ("thunderstorms", "thunderstorms"),
    "lightning-rainy": ("thunderstorms-rain", "thunderstorms-rain"),
    "partlycloudy": ("partly-cloudy-day", "partly-cloudy-night"),
    "pouring": ("rain", "rain"),
    "rainy": ("drizzle", "drizzle"),
    "snowy": ("snow", "snow"),
    "snowy-rainy": ("sleet", "sleet"),
    "sunny": ("clear-day", "clear-night"),
    "windy": ("wind", "wind"),
    "windy-variant": ("wind", "wind"),
}
# Pictures appended after the existing ones in each variant (HMI/BUILD.md).
PICTURE_BASE = {"eu": 26, "us-p": 24, "us-l": 24}
DISPLAY_VERSION_PICTURES = 55


def mdi_icon(condition, night=False):
    pair = _MDI.get(condition)
    return pair[1 if night else 0] if pair else "alert-circle-outline"


def color(condition, night=False):
    if night and condition in ("sunny", "partlycloudy"):
        return rgb_dec565(_MOON)
    return rgb_dec565(_COLORS.get(condition, _CLOUD))


def picture_index(condition, night=False, forecast=False):
    """Index into the picture list: main pictures first, then the forecast ones."""
    pair = _PICTURE.get(condition, ("cloudy", "cloudy"))
    index = PICTURES.index(pair[1 if night else 0])
    return index + (len(PICTURES) if forecast else 0)


def sun_is_down(sun_state):
    """Night for the current condition: sun.sun below the horizon."""
    return isinstance(sun_state, dict) and sun_state.get("state") == "below_horizon"


def forecast_is_night(item, hourly):
    """Hourly items carry is_daytime (most weather integrations); daily items are day."""
    if not hourly:
        return False
    if isinstance(item.get("is_daytime"), bool):
        return not item["is_daytime"]
    try:
        hour = datetime.fromisoformat(item.get("datetime")).astimezone().hour
    except (TypeError, ValueError):
        return False
    return hour < 6 or hour >= 21
