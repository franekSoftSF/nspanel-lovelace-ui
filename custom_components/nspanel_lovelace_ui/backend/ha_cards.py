from . import libs  # noqa: F401
from .libs import home_assistant as _home_assistant  # noqa: F401
from .libs import panel_cmd as _panel_cmd  # noqa: F401
from .libs.light_temperature import temperature_slider
from .libs.sensor_display import format_sensor_value
from . import ha_icons
from . import ha_colors
from .libs.localization import get_translation
from . import panel_cards
from . import weather
from . import wifi as wifi_qr
from . import charts
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging
import babel.dates
from .libs.icon_mapping import get_icon_char
from .libs.helper import rgb_dec565, scale
import time
import threading
import datetime
import json
import math

DEFAULT_SCREENSAVER_COLOR_MAPPING = {
    "background": 0,
    "time": 65535,
    "timeAMPM": 65535,
    "date": 65535,
    "tMainText": 65535,
    "tForecast1": 65535,
    "tForecast2": 65535,
    "tForecast3": 65535,
    "tForecast4": 65535,
    "tForecast1Val": 65535,
    "tForecast2Val": 65535,
    "tForecast3Val": 65535,
    "tForecast4Val": 65535,
    "bar": 65535,
    "tMainTextAlt2": 65535,
    "tTimeAdd": 65535,
}


def get_screensaver_color_output(theme):
    colors = []
    for key, default_color in DEFAULT_SCREENSAVER_COLOR_MAPPING.items():
        config_color = theme.get(key, default_color)
        if isinstance(config_color, list):
            config_color = rgb_dec565(config_color)
        colors.append(str(config_color))
    return "~".join(colors)

class HAEntity(panel_cards.Entity):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    @staticmethod
    def _normalize_state_filter(value):
        # YAML parses bare `on`/`off` as booleans, but HA states are strings.
        if value is True:
            return "on"
        if value is False:
            return "off"
        return str(value)

    def _resolve_internal_overwrite(self, overwrite, default=None):
        status_entity = self.config.get("status")
        if not isinstance(overwrite, dict):
            return overwrite
        if status_entity:
            status_data = libs.home_assistant.get_entity_data(status_entity)
            state = status_data.get("state", "off") if status_data else "off"
        else:
            state = "off"
        return overwrite.get(state, overwrite.get("off", default))

    def prerender(self):
        for field in ("color", "icon", "value", "name", "speed", "state_template"):
            template = self.config.get(field)
            if isinstance(template, str) and template and (template.startswith("ha:") or
                    field == "state_template" or
                    (field == "speed" and ("{{" in template or "{%" in template))):
                libs.home_assistant.cache_template(template, self.entity_id)

    def render(self, cardType=""):
        self.weather_condition = None
        # AppDaemon compatibility: a true condition hides the item entirely.
        condition = self.config.get("state_template")
        if isinstance(condition, str) and condition:
            condition = libs.home_assistant.get_template(condition, self.entity_id)
        if (condition is True
                or (isinstance(condition, str) and condition.strip().lower() in ("true", "on", "yes", "1"))
                or (type(condition) in (int, float) and condition != 0)):
            return ""

        # Resolve from config each time: do not replace the subscribed expression.
        self.name_overwrite = self.config.get("name")
        for field in ("name", "icon", "color"):
            configured = self.config.get(field)
            if isinstance(configured, str) and configured.startswith("ha:"):
                resolved = libs.home_assistant.get_template(configured, self.entity_id)
                # Icon templates render literal text with optional <I>mdi:...</I> tags.
                # Keep this marker at the renderer boundary, not in the shared cache.
                if field == "icon" and resolved is not None:
                    resolved = "ha:" + str(resolved)
                if field == "name" and resolved is not None:
                    resolved = str(resolved)
                setattr(self, field + "_overwrite", resolved)
            elif field in ("icon", "color") and self.etype in ("navigate", "iText"):
                setattr(self, field + "_overwrite", self._resolve_internal_overwrite(configured))

        if self.etype in ["delete", "navigate", "iText"]:
            out = super().render()
            if self.etype == "navigate" and "status" in self.config:
                status_out = HAEntity(self.locale,
                                    {
                                        'entity': f'{self.config.get("status")}',
                                    }, self.panel
                                ).render().split("~")
                out_parts = out.split("~")
                status_out[2] = out_parts[2]
                if self.config.get("icon") is not None:
                    status_out[3] = out_parts[3]
                if self.config.get("color") is not None:
                    status_out[4] = out_parts[4]
                if self.config.get("name"):
                    status_out[5] = out_parts[5]
                status_out = "~".join(status_out)
                return status_out
            return out

        # get data from HA
        status_entity = self.config.get("status")
        data = libs.home_assistant.get_entity_data(status_entity if status_entity else self.entity_id)
        if data:
            self.state = data.get("state")
            self.attributes = data.get("attributes", [])
        elif self.etype == "service" and not status_entity:
            # A service.* button has no state of its own.
            self.state = ""
            self.attributes = {}
        else:
            self.state = "not found"
            self.attributes = []
            return "~text~iid.404~X~6666~not found~"

        state_filter = self.config.get("state")
        if state_filter is not None and self.state != self._normalize_state_filter(state_filter):
            return ""
        state_not_filter = self.config.get("state_not")
        if state_not_filter is not None and self.state == self._normalize_state_filter(state_not_filter):
            return ""

        # HA Entities
        entity_type_panel = "text"
        # Like AppDaemon, a service.* button looks like its status entity, or like a script.
        style_type = self.etype
        if style_type == "service":
            style_type = status_entity.split(".")[0] if status_entity else "script"
        icon_char = ha_icons.get_icon_ha(style_type, self.state, device_class=self.attributes.get("device_class", None), media_content_type=self.attributes.get("media_content_type", None), overwrite=self.icon_overwrite)

        color = ha_colors.get_entity_color(style_type, self.state, self.attributes, self.color_overwrite)

        name = self.name_overwrite if self.name_overwrite is not None else self.attributes.get("friendly_name", "unknown")
        value = ""

        match self.etype:
            case 'switch' | 'input_boolean' | 'automation':
                entity_type_panel = "switch"
                value = 1 if self.state == "on" else 0
            case 'lock':
                entity_type_panel = "button"
                value = get_translation(self.locale, "frontend.ui.card.lock.lock") if self.state == "unlocked" else get_translation(
                    self.locale, "frontend.ui.card.lock.unlock")
            case 'input_text':
                value = self.state
            case 'input_select' | 'select':
                entity_type_panel = "input_sel"
                value = self.state
            case 'light':
                entity_type_panel = "light"
                value = 1 if self.state == "on" else 0
            case 'fan':
                entity_type_panel = "fan"
                value = 1 if self.state == "on" else 0
            case 'button' | 'input_button':
                entity_type_panel = "button"
                value = get_translation(
                    self.locale, "frontend.ui.card.button.press")
            case 'scene':
                entity_type_panel = "button"
                value = get_translation(
                    self.locale, "frontend.ui.card.scene.activate")
            case 'script' | 'service':
                entity_type_panel = "button"
                value = get_translation(
                    self.locale, "frontend.ui.card.script.run")
            case 'number' | 'input_number':
                entity_type_panel = "number"
                min_v = self.attributes.get("min", 0)
                max_v = self.attributes.get("max", 100)
                value = f"{self.state}|{min_v}|{max_v}"
            case 'timer':
                entity_type_panel = "timer"
                value = get_translation(
                    self.locale, f"backend.component.timer.state._.{self.state}")
            case 'alarm_control_panel':
                value = get_translation(
                    self.locale, f"frontend.state_badge.alarm_control_panel.{self.state}")
            case 'vacuum':
                entity_type_panel = "button"
                if self.state == "docked":
                    value = get_translation(
                        self.locale, "frontend.ui.card.vacuum.actions.start_cleaning")
                else:
                    value = get_translation(
                        self.locale, "frontend.ui.card.vacuum.actions.return_to_base")
            case 'media_player':
                entity_type_panel = "media_pl"
                value = self.state
            case 'sun':
                value = get_translation(
                    self.locale, f"backend.component.sun.state._.{self.state}")
            case 'person':
                value = get_translation(
                    self.locale, f"backend.component.person.state._.{self.state}")
            case 'climate':
                # TODO: temp unit
                temp_unit = "celsius"
                state_value = get_translation(
                    self.locale, f"backend.component.climate.state._.{self.state}")
                temperature = self.attributes.get("temperature", "")
                temperature_unit = "°C" if (temp_unit == "celsius") else "°F"
                value = f"{state_value} {temperature}{temperature_unit}"
                currently_tanslation = get_translation(
                    self.locale, "frontend.ui.card.climate.currently")
                current_temperature = self.attributes.get(
                    "current_temperature", "")
                value += f"\r\n{currently_tanslation}: {current_temperature}{temperature_unit}"
            case 'cover':
                entity_type_panel = "shutter"
                device_class = self.attributes.get("device_class", "window")
                icon_up = ""
                icon_stop = ""
                icon_down = ""
                icon_up_status = "disable"
                icon_stop_status = "disable"
                icon_down_status = "disable"
                bits = self.attributes.get("supported_features")
                pos = self.attributes.get("current_position")
                assumed_state = self.attributes.get("assumed_state", False)
                if pos is None:
                    pos = "disable"
                if bits & 0b00000001:  # SUPPORT_OPEN
                    if (pos != 100 and not (self.state == "open" and pos == "disable")):
                        icon_up_status = "enable"
                    icon_up = ha_icons.get_action_icon(
                        etype=self.etype, action="open", device_class=device_class)
                if bits & 0b00000010:  # SUPPORT_CLOSE
                    if (pos != 0 and not (self.state == "closed" and pos == "disable")):
                        icon_down_status = "enable"
                    icon_down = ha_icons.get_action_icon(
                        etype=self.etype, action="close", device_class=device_class)
                if bits & 0b00001000:  # SUPPORT_STOP
                    icon_stop = ha_icons.get_action_icon(
                        etype=self.etype, action="stop", device_class=device_class)
                    icon_stop_status = "enable"
                if assumed_state:
                    icon_up_status = "enable"
                    icon_stop_status = "enable"
                    icon_down_status = "enable"
                value = f"{icon_up}|{icon_stop}|{icon_down}|{icon_up_status}|{icon_stop_status}|{icon_down_status}"
            case 'sensor':
                device_class = self.attributes.get("device_class", "")
                unit_of_measurement = self.attributes.get("unit_of_measurement", "")
                value = format_sensor_value(self.state, libs.home_assistant.sensor_display_precision.get(status_entity or self.entity_id))
                # limit value to 4 chars on us-p
                if self.panel.model == "us-p" and cardType == "cardEntities":
                    value = value[:4]
                    if value.endswith("."):
                        value = value[:-1]

                # Keep grid values unitless so the TFT retains the font suffix.
                if cardType in ["cardGrid", "cardGrid2"] and not self.icon_overwrite:
                    icon_char = value
                if device_class != "temperature":
                    value = value + " "
                value = value + unit_of_measurement
            case 'binary_sensor':
                device_class = self.attributes.get("device_class", "")
                value = get_translation(self.locale, f"backend.component.binary_sensor.state.{device_class}.{self.state}")
            case 'weather':
                attr = self.config.get("attribute", "temperature")
                value = str(self.attributes.get(attr, self.state))
                # Condition shown by this item (today or a forecast entry) and whether it is night:
                # drives the icon, its colour and the colour picture of firmware 55+.
                condition = self.state
                night = weather.sun_is_down(libs.home_assistant.get_entity_data("sun.sun"))

                # settings for forecast
                forecast_type = None
                if self.config.get("day") is not None:
                    forecast_type = "daily"
                    pos = self.config.get("day")
                    datetime_format = "E"
                if self.config.get("hour") is not None:
                    forecast_type = "hourly"
                    pos = self.config.get("hour")
                    datetime_format = "H:mm"
                if forecast_type:
                    forecast = libs.home_assistant.get_forecast(self.entity_id, forecast_type).get(self.entity_id,{}).get("forecast", [])
                    if len(forecast) > pos:
                        forcast_pos = forecast[pos]
                        forcast_condition = forcast_pos.get("condition", "")
                        forcast_date = datetime.datetime.fromisoformat(forcast_pos.get("datetime")).astimezone()

                        condition = forcast_condition
                        night = weather.forecast_is_night(forcast_pos, forecast_type == "hourly")
                        name = babel.dates.format_datetime(forcast_date, datetime_format, locale=self.locale)

                        attr = self.config.get("attribute", "temperature")
                        value = str(forcast_pos.get(attr, "not found"))
                    else:
                        name = "unknown"
                if self.icon_overwrite is None:
                    icon_char = get_icon_char(weather.mdi_icon(condition, night))
                if self.color_overwrite is None:
                    color = weather.color(condition, night)
                self.weather_condition = (condition, night, forecast_type is not None)
                # add units
                if attr in ["temperature", "apparent_temperature", "templow"]:
                    value += self.config.get("unit", "°C")
                else:
                    value += self.config.get("unit", "")
            case _:
                name = "unsupported"

        if self.value_overwrite and self.value_overwrite.startswith("ha:"):
            resolved = libs.home_assistant.get_template(self.value_overwrite, self.entity_id)
            value = "" if resolved is None else resolved


        # Grid icon/value fonts use TFT IDs 0–3, unlike screensaver status fonts.
        if cardType in ("cardGrid", "cardGrid2"):
            grid_font = {"small": 0, "medium-icon": 1, "medium": 2, "large": 3,
                         # MDI 7 firmware (HMI 55+): sharp 64 px icon font, appended as the last font:
                         # index 8 (EU, US landscape: 8 fonts before) or 7 (US portrait: 7), HMI/BUILD.md.
                         "large-icon": large_icon_font_id(self.panel.settings if self.panel else {}),
                         }.get(self.config.get("font"))
            if grid_font is not None:
                icon_char = f"{icon_char}¬{grid_font}"

        return f"~{entity_type_panel}~iid.{self.iid}~{icon_char}~{color}~{name}~{value}"

def large_icon_font_id(settings):
    default = 7 if settings.get("model", "eu") == "us-p" else 8
    return settings.get("largeIconFontId", default)


class HACard(panel_cards.Card):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)
        # Generate Entity for each Entity in Config
        self.entities = []
        if "entity" in config:
            entity = HAEntity(locale, config, panel)
            self.entities.append(entity)
        if "entities" in config:
            for e in config.get("entities"):
                entity = HAEntity(locale, e, panel)
                self.entities.append(entity)

    def _nav_item(self, number):
        """navItem1/navItem2 with an entity replace the left/right button (AppDaemon behaviour, #1470)."""
        attr = f"_nav_item{number}"
        if not hasattr(self, attr):
            config = self.config.get(f"navItem{number}")
            setattr(self, attr, HAEntity(self.locale, config, self.panel)
                    if isinstance(config, dict) and config.get("entity") else None)
        return getattr(self, attr)

    def navigation_entities(self):
        return [item for item in (self._nav_item(1), self._nav_item(2)) if item]

    def send_update(self, result, layout=None):
        """entityUpd; if the layout changed while the page is shown, open the page again first.

        Some pages only ever show elements on an update and hide them when the page opens
        (cardAlarm arm buttons, the cardThermo dual set point), so a smaller layout needs a fresh page.
        """
        previous = getattr(self, "_layout", None)
        self._layout = layout
        if layout is not None and previous is not None and previous != layout and self.panel.current_card is self:
            libs.panel_cmd.page_type(self.panel.msg_out_queue, self.panel.sendTopic, self.type)
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

    def navigation_up_icon(self):
        if not self.hidden:
            return None
        if self.config.get("navItem1"):
            return self.config.get("navItem1")
        return None

    def get_iid_entities(self):
        return [(e.iid, e.entity_id) for e in self.entities + self.navigation_entities()]

    def get_entities(self):
        entities = [e.entity_id for e in self.entities + self.navigation_entities()]
        for entity in self.entities + self.navigation_entities():
            status_entity = entity.config.get("status")
            if status_entity and status_entity not in entities:
                entities.append(status_entity)
        return entities + [self.iid]

    def gen_nav(self):
        leftBtn = "delete~~~~~"
        if self.iid_prev:
            leftBtn = panel_cards.Entity(self.locale,
                                         {
                                             'entity': f'navigate.{self.iid_prev}',
                                             'icon': 'mdi:arrow-left-bold',
                                             'color': [255, 255, 255],
                                         }, self.panel
                                         ).render()[1:]
        rightBtn = "delete~~~~~"
        if self.iid_next:
            rightBtn = panel_cards.Entity(self.locale,
                                          {
                                              'entity': f'navigate.{self.iid_next}',
                                              'icon': 'mdi:arrow-right-bold',
                                              'color': [255, 255, 255],
                                          }, self.panel
                                          ).render()[1:]
        if self.hidden:
            if self.navigation_up_icon():
                upNavIconAttributes=self.navigation_up_icon()
                leftBtn = panel_cards.Entity(self.locale,
                                         {
                                             'entity': f'navigate.UP',
                                             'icon': upNavIconAttributes['icon'] if upNavIconAttributes.get('icon') else 'mdi:arrow-up-bold',
                                             'color': upNavIconAttributes['color'] if upNavIconAttributes.get('color') else [255, 255, 255],
                                         }, self.panel
                                         ).render()[1:]
            else:
                leftBtn = panel_cards.Entity(self.locale,
                                            {
                                                'entity': f'navigate.UP',
                                                'icon': 'mdi:arrow-up-bold',
                                                'color': [255, 255, 255],
                                            }, self.panel
                                            ).render()[1:]
        if self._nav_item(1):
            leftBtn = self._nav_item(1).render()[1:] or "delete~~~~~"
        if self._nav_item(2):
            rightBtn = self._nav_item(2).render()[1:] or "delete~~~~~"
        result = f"{leftBtn}~{rightBtn}"
        return result

class EntitiesCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)
        self.grid = self.type == "cardGrid"
        if len(self.entities) > 6 and self.grid:
            self.type = "cardGrid2"

    def render(self):
        rendered = [e.render(cardType=self.type) for e in self.entities]
        if self.grid:
            # Issue #1190: the layout follows the *visible* items (state / state_template can
            # hide some). On a change, switch the page first; the panel then asks for the content.
            layout = "cardGrid2" if sum(1 for item in rendered if item) > 6 else "cardGrid"
            if layout != self.type:
                self.type = layout
                if self.panel.current_card is self:
                    libs.panel_cmd.page_type(self.panel.msg_out_queue, self.panel.sendTopic, layout)
                    return
                rendered = [e.render(cardType=self.type) for e in self.entities]
        result = f"{self.title}~{self.gen_nav()}" + "".join(rendered)
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

WIFI_ROW_NAMES = {"en": ("Network", "Password"), "pl": ("Sieć", "Hasło"), "de": ("Netzwerk", "Passwort")}


class QRCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)
        self.qrcode = config.get("qrCode", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.wifi = config.get("wifi") if isinstance(config.get("wifi"), dict) else None

    def get_entities(self):
        entities = super().get_entities()
        password_entity = self.wifi.get("passwordEntity") if self.wifi else None
        return entities + [password_entity] if password_entity else entities

    def _wifi_password(self):
        """Plain text, a template (ha: …), an entity state or a secret (resolved when the file was loaded)."""
        password = self.wifi.get("password")
        if password is None and self.wifi.get("passwordEntity"):
            data = libs.home_assistant.get_entity_data(self.wifi["passwordEntity"])
            password = data.get("state") if data and data.get("state") not in ("unknown", "unavailable") else ""
        password = "" if password is None else str(password)
        if password.startswith("ha:"):
            resolved = libs.home_assistant.get_template(password, self.iid)
            password = "" if resolved is None else str(resolved)
        return password

    def _wifi_rows(self, ssid, password):
        show = self.wifi.get("show", "ssid")
        if show == "none" or self.entities:
            return []
        names = WIFI_ROW_NAMES.get(str(self.locale)[:2], WIFI_ROW_NAMES["en"])
        color = rgb_dec565([68, 115, 158])
        clean = lambda text: str(text).replace("~", "-")  # noqa: E731 - ~ separates the fields
        rows = [f"~text~iText.wifi_ssid~{get_icon_char('mdi:wifi')}~{color}~{names[0]}~{clean(ssid)}"]
        if show == "ssid_password" and password:
            rows.append(f"~text~iText.wifi_password~{get_icon_char('mdi:key-variant')}~{color}~{names[1]}~{clean(password)}")
        return rows

    def render(self):
        rows = []
        if self.wifi:
            ssid = str(self.wifi.get("ssid", ""))
            security = self.wifi.get("security", "WPA")
            password = self._wifi_password() if security != "nopass" else ""
            qrcode = wifi_qr.build(ssid, security, password, self.wifi.get("hidden") is True)
            rows = self._wifi_rows(ssid, password)
        else:
            qrcode = str(self.qrcode)
            if qrcode.startswith("ha:"):
                resolved = libs.home_assistant.get_template(qrcode, self.iid)
                qrcode = "" if resolved is None else str(resolved)
        if len(qrcode.encode("utf-8")) > wifi_qr.QR_MAX_BYTES:
            logging.warning("cardQR %r: the code has %d bytes, the panel keeps only %d - shorten it",
                            self.title, len(qrcode.encode("utf-8")), wifi_qr.QR_MAX_BYTES)
        rows += [row for row in (e.render() for e in self.entities) if row]
        # The panel draws the code with no rows (centred) or with two rows; with exactly one row it
        # draws nothing (HMI cardQR), so a blank second row keeps the code visible.
        if len(rows) == 1:
            rows.append("~text~iText.qr_blank~~0~~")
        result = f"{self.title}~{self.gen_nav()}~{qrcode}{''.join(rows[:2])}"
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

class ChartCard(HACard):
    """cardChart (bars) and cardLChart (line) from the recorder history of one numeric entity.

    The chart is drawn when its page opens (the display redraws the whole chart on every update),
    not on every state change of the entity.
    """

    def get_entities(self):
        return [e.entity_id for e in self.navigation_entities()] + [self.iid]

    def _span(self):
        hours = self.config.get("hours", 24)
        return datetime.timedelta(hours=hours if isinstance(hours, int) and 1 <= hours <= 24 * 31 else 24)

    def render(self):
        entity_id = self.config.get("entity", "")
        data = libs.home_assistant.get_entity_data(entity_id) or {}
        attributes = data.get("attributes") or {}
        title = self.title or attributes.get("friendly_name", entity_id)
        prefix = f"{title}~{self.gen_nav()}~"
        colour = rgb_dec565(self.config.get("color") or [3, 169, 244])
        y_label = str(self.config.get("yAxisLabel", attributes.get("unit_of_measurement", "")))
        span = self._span()
        end = datetime.datetime.now(datetime.timezone.utc)
        start = end - span
        points = [(when, value) for when, state in libs.home_assistant.get_history(entity_id, start, end)
                  if (value := charts.to_float(state)) is not None]
        try:
            zone = ZoneInfo(self.panel.settings.get("timeZone", ""))
        except (ZoneInfoNotFoundError, ValueError, TypeError, AttributeError):
            zone = None
        line = self.type == "cardLChart"
        count = self.config.get("points" if line else "bars", 48 if line else 12)
        count = count if isinstance(count, int) and 2 <= count <= 200 else (48 if line else 12)
        aggregate = self.config.get("aggregate", "mean")
        values = charts.buckets(points, start, end, count, aggregate if aggregate in charts.AGGREGATES else "mean")
        step = span / count
        local = lambda moment: moment.astimezone(zone) if zone else moment.astimezone()  # noqa: E731
        if line:
            minutes = int(span.total_seconds() // 60)
            series = [(int((step * (i + 0.5)).total_seconds() // 60), v) for i, v in enumerate(values) if v is not None]
            ticks = [(int((span / 4 * i).total_seconds() // 60), charts.time_label(local(start + span / 4 * i), span))
                     for i in range(5) if (span / 4 * i).total_seconds() // 60 <= minutes]
            body = charts.line_payload(series, ticks, y_label, colour, charts.LINE_COMMAND - 10 - len(prefix))
        else:
            every = charts.label_every(count)
            labels = [charts.time_label(local(start + step * i), span) if i % every == 0 else "" for i in range(count)]
            body = charts.bar_payload(values, labels, y_label, colour, charts.BAR_COMMAND - 10 - len(prefix))
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, prefix + body)


class PowerCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    def render(self):
        result = f"{self.title}~{self.gen_nav()}"
        for e in self.entities:
            # A hidden item (state filters) still takes its 6 fields, or the next items would shift.
            result += e.render() or "~delete~~~~~"
            speed_input = e.config.get("speed", 0)
            if isinstance(speed_input, str) and (speed_input.startswith("ha:") or "{{" in speed_input or "{%" in speed_input):
                speed_input = libs.home_assistant.get_template(speed_input, e.entity_id)
            try:
                numeric = float(speed_input)
                # The TFT supports signed speeds: negative values reverse flow.
                speed = int(max(-120, min(120, numeric))) if math.isfinite(numeric) else 0
            except (TypeError, ValueError, OverflowError):
                speed = 0
            result += f"~{speed}"
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

class MediaCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    def render(self):
        main_entity = self.entities[0]
        media_icon = main_entity.render()
        attributes = main_entity.attributes if isinstance(main_entity.attributes, dict) else {}  # [] if missing
        if not self.title:
            self.title = attributes.get("friendly_name", main_entity.entity_id)
        clean = lambda text: str(text or "").replace("~", "-")  # noqa: E731 - ~ separates the fields
        title = clean(attributes.get("media_title"))
        author = clean(attributes.get("media_artist"))
        volume = int((attributes.get("volume_level") or 0) * 100)
        iconplaypause = get_icon_char("pause") if main_entity.state == "playing" else get_icon_char("play")
        onoffbutton = "disable"
        shuffleBtn = "disable"

        bits = attributes.get("supported_features") or 0
        if bits & (128 | 256):  # MediaPlayerEntityFeature.TURN_ON | TURN_OFF
            if main_entity.state == "off":
                onoffbutton = 1374
            else:
                onoffbutton = rgb_dec565([255,152,0])

        if bits & 32768:  # MediaPlayerEntityFeature.SHUFFLE_SET
            shuffle = attributes.get("shuffle", "")
            if shuffle == False:
                shuffleBtn = get_icon_char('shuffle-disabled')
            elif shuffle == True:
                shuffleBtn = get_icon_char('shuffle')

        # generate button entities
        button_str = ""
        for e in self.entities[1:]:
            button_str += e.render()
        result = f"{self.title}~{self.gen_nav()}~{main_entity.entity_id}~{title}~~{author}~~{volume}~{iconplaypause}~{onoffbutton}~{shuffleBtn}{media_icon}{button_str}"
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

class ClimateCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    def render(self):
        main_entity = self.entities[0]

        temp_unit = self.panel.temp_unit
        if temp_unit == "celsius":
            temperature_unit_icon = get_icon_char("temperature-celsius")
            temperature_unit = "°C"

        else:
            temperature_unit_icon = get_icon_char("temperature-fahrenheit")
            temperature_unit = "°F"

        main_entity.render()
        if not self.title:
            self.title = main_entity.attributes.get("friendly_name", "unknown")
        current_temp = main_entity.attributes.get("current_temperature")
        current_temp = "" if current_temp is None else current_temp
        dest_temp    = main_entity.attributes.get("temperature", None)
        dest_temp2   = ""
        if dest_temp is None:
            dest_temp    = main_entity.attributes.get("target_temp_high") or 0
            dest_temp2   = main_entity.attributes.get("target_temp_low", None)
            if dest_temp2 != None and dest_temp2 != "null":
                dest_temp2   = int(dest_temp2*10)
            else:
                dest_temp2 = ""
        dest_temp    = int(dest_temp*10)

        hvac_action  = main_entity.attributes.get("hvac_action", "")
        state_value  = ""
        if hvac_action != "":
            state_value = get_translation(self.locale, f"frontend.state_attributes.climate.hvac_action.{hvac_action}")
            state_value += "\r\n("
        state_value += get_translation(self.locale, f"backend.component.climate.state._.{main_entity.state}")
        if hvac_action != "":
            state_value += ")"

        min_temp     = int(main_entity.attributes.get("min_temp", 0)*10)
        max_temp     = int(main_entity.attributes.get("max_temp", 0)*10)

        if temp_unit == "celsius":
            step_default = 0.5
        else:
            step_default = 0.5
        step_temp    = int(main_entity.attributes.get("target_temp_step", step_default)*10)
        icon_res_list = []
        icon_res = ""

        hvac_modes = main_entity.attributes.get("hvac_modes", [])
        if main_entity.config.get("supported_modes"):
            hvac_modes = main_entity.config.get("supported_modes")
        for mode in hvac_modes:
            icon_id = ha_icons.get_icon_ha("climate", mode)
            color_on = 64512
            if mode in ["auto", "heat_cool"]:
                color_on = 1024
            if mode == "heat":
                color_on = 64512
            if mode == "off":
                color_on = 35921
            if mode == "cool":
                color_on = 11487
            if mode == "dry":
                color_on = 60897
            if mode == "fan_only":
                color_on = 35921
            state = 0
            if(mode == main_entity.state):
                state = 1

            icon_res_list.append(f"~{icon_id}~{color_on}~{state}~{mode}")

        icon_res = "".join(icon_res_list)

        if len(icon_res_list) == 1 and not self.panel.model == "us-p":
            icon_res = "~"*4 + icon_res_list[0] + "~"*4*6
        elif len(icon_res_list) == 2 and not self.panel.model == "us-p":
            icon_res = "~"*4*2 + icon_res_list[0] + "~"*4*2 + icon_res_list[1] + "~"*4*2
        elif len(icon_res_list) == 3 and not self.panel.model == "us-p":
            icon_res = "~"*4*2 + icon_res_list[0] + "~"*4 + icon_res_list[1] + "~"*4 + icon_res_list[2] + "~"*4
        elif len(icon_res_list) == 4 and not self.panel.model == "us-p":
            icon_res = "~"*4 + icon_res_list[0] + "~"*4 + icon_res_list[1] + "~"*4 + icon_res_list[2] + "~"*4 + icon_res_list[3]
        elif len(icon_res_list) >= 5 or self.panel.model == "us-p":
            icon_res = "".join(icon_res_list) + "~"*4*(8-len(icon_res_list))

        currently_translation = get_translation(self.locale, "frontend.ui.card.climate.currently")
        state_translation = get_translation(self.locale, "frontend.ui.panel.config.devices.entities.state")
        action_translation = get_translation(self.locale, "frontend.ui.card.climate.operation").replace(' ','\r\n')

        detailPage = "1"
        if any(x in ["preset_modes", "swing_modes", "fan_modes"] for x in main_entity.attributes):
            detailPage = "0"

        result = f"{self.title}~{self.gen_nav()}~iid.{main_entity.iid}~{current_temp} {temperature_unit}~{dest_temp}~{state_value}~{min_temp}~{max_temp}~{step_temp}{icon_res}~{currently_translation}~{state_translation}~{action_translation}~{temperature_unit_icon}~{dest_temp2}~{detailPage}"
        self.send_update(result, layout=dest_temp2 != "")  # dual set point only shows, never hides

class AlarmCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    def render(self):
        main_entity = self.entities[0]
        main_entity.render()

        logging.debug("Alarm card state for '%s': %s", main_entity.entity_id, main_entity.state)

        icon = get_icon_char("shield-off")
        color = rgb_dec565([255,255,255])
        supported_modes = []
        numpad = "enable"
        if main_entity.state == "disarmed":
            color = rgb_dec565([13,160,53])
            icon = get_icon_char("shield-off")
            if not main_entity.attributes.get("code_arm_required", False):
                numpad = "disable"
            if self.config.get("supported_modes") is None:
                bits = main_entity.attributes.get("supported_features")
                if bits & 0b000001:
                    supported_modes.append("arm_home")
                if bits & 0b000010:
                    supported_modes.append("arm_away")
                if bits & 0b000100:
                    supported_modes.append("arm_night")
                if bits & 0b100000:
                    supported_modes.append("arm_vacation")
            else:
                supported_modes = self.config.get("supported_modes")
        else:
            supported_modes.append("disarm")

        if main_entity.state == "armed_home":
            color = rgb_dec565([223,76,30])
            icon = get_icon_char("shield-home")
        if main_entity.state == "armed_away":
            color = rgb_dec565([223,76,30])
            icon = get_icon_char("shield-lock")
        if main_entity.state == "armed_night":
            color = rgb_dec565([223,76,30])
            icon = get_icon_char("weather-night")
        if main_entity.state == "armed_vacation":
            color = rgb_dec565([223,76,30])
            icon = get_icon_char("shield-airplane")

        flashing = "disable"
        if main_entity.state in ["arming", "pending"]:
            color = rgb_dec565([243,179,0])
            icon = get_icon_char("shield")
            flashing = "enable"
        if main_entity.state == "triggered":
            color = rgb_dec565([223,76,30])
            icon = get_icon_char("bell-ring")
            flashing = "enable"

        #add button to show sensor state
        add_btn = ""
        if "open_sensors" in main_entity.attributes and main_entity.attributes.get("open_sensors") is not None:
            add_btn=f"{get_icon_char('progress-alert')}~{rgb_dec565([243,179,0])}~"

        # add padding to arm buttons
        arm_buttons = ""
        for b in supported_modes:
            modeName = f"frontend.ui.card.alarm_control_panel.{b}"
            arm_buttons += f"~{get_translation(self.locale, modeName)}~{b}"
        if len(supported_modes) < 4:
            arm_buttons += "~"*((4-len(supported_modes))*2)
        result = f"{self.title}~{self.gen_nav()}~{main_entity.entity_id}{arm_buttons}~{icon}~{color}~{numpad}~{flashing}~{add_btn}"
        # Arm buttons and the open sensors button only show on an update, never hide.
        self.send_update(result, layout=(len(supported_modes), bool(add_btn)))


class UnlockCard(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

    def render(self):

        color = rgb_dec565([255,0,0])
        icon = get_icon_char("lock")
        supported_modes = ["cardUnlock-unlock"]

        entity_id = self.config.get("destination")

        # add padding to arm buttons
        arm_buttons = ""
        for b in supported_modes:
            arm_buttons += f'~{get_translation(self.locale, "frontend.ui.card.lock.unlock")}~{b}'
            if len(supported_modes) < 4:
                arm_buttons += "~"*((4-len(supported_modes))*2)
        numpad = "enable"

        result = f"{self.title}~{self.gen_nav()}~{entity_id}{arm_buttons}~{icon}~{color}~{numpad}~disable~"
        libs.panel_cmd.entityUpd(self.panel.msg_out_queue, self.panel.sendTopic, result)

class Screensaver(HACard):
    def __init__(self, locale, config, panel):
        super().__init__(locale, config, panel)

        if not self.type:
            self.type = "screensaver"

        self.statusIcon1 = None
        if "statusIcon1" in config:
            self.statusIcon1 = HAEntity(locale, config.get("statusIcon1"), panel)
        self.statusIcon2 = None
        if "statusIcon2" in config:
            self.statusIcon2 = HAEntity(locale, config.get("statusIcon2"), panel)
        self.theme = config.get("theme")
        self.invalidate()

    def invalidate(self):
        self._last_payloads = {}

    def _send_changed(self, command, payload, force=False):
        """Send unless the panel already shows this payload; returns whether it was sent."""
        if force or self._last_payloads.get(command) != payload:
            command(self.panel.msg_out_queue, self.panel.sendTopic, payload)
            self._last_payloads[command] = payload
            return True
        return False

    def get_entities(self):
        ent = [e.entity_id for e in self.entities]
        if self.statusIcon1:
            ent.append(self.statusIcon1.entity_id)
        if self.statusIcon2:
            ent.append(self.statusIcon2.entity_id)
        return ent

    def _weather_picture_base(self):
        """Picture ID of the first colour weather picture, or None to keep the font icons."""
        settings = self.panel.settings
        if self.type != "screensaver" or len(self.entities) > 5 or settings.get("weatherIcons", "color") != "color":
            return None  # alternative layouts move the icons around; they keep the font icons
        if (getattr(self.panel, "display_version", None) or 0) < weather.DISPLAY_VERSION_PICTURES:
            return None  # the pictures exist from firmware 55
        background = (self.theme or {}).get("background", 0)
        if isinstance(background, list):
            background = rgb_dec565(background)
        if background != 0:
            return None  # the pictures are drawn on black
        return settings.get("weatherPictureBase", weather.PICTURE_BASE.get(settings.get("model", "eu"), 26))

    def render(self):
        rendered = [e.render(cardType=self.type) for e in self.entities]
        pictures = []
        base = self._weather_picture_base()
        if base is not None:
            # The HMI slots are positional: hidden entities (empty renders) take no slot.
            for index, item in enumerate(rendered):
                if not item:
                    continue
                if len(pictures) == 5:
                    break
                entity = self.entities[index]
                condition = getattr(entity, "weather_condition", None)
                if condition is None or entity.config.get("icon") is not None:
                    pictures.append("")  # not weather, or a configured icon: keep the font icon
                    continue
                pictures.append(str(base + weather.picture_index(condition[0], condition[1],
                                                                 forecast=len(pictures) > 0)))
                fields = item.split("~")
                fields[3] = ""  # no font icon under the picture
                rendered[index] = "~".join(fields)
        result = "".join(rendered)
        repainted = self._send_changed(libs.panel_cmd.weatherUpdate, result[1:])
        if self.type == "screensaver" and self.theme:
            repainted |= self._send_changed(
                libs.panel_cmd.screensaverColor,
                get_screensaver_color_output(self.theme),
            )
        if self.type == "screensaver" and \
                (getattr(self.panel, "display_version", None) or 0) >= weather.DISPLAY_VERSION_PICTURES:
            # Firmware 55+, always (empty fields hide pictures left from an earlier state) and
            # last: weatherUpdate and color repaint the font icon boxes under the pictures, so
            # the pictures are sent again whenever one of them was sent.
            pictures += [""] * (5 - len(pictures))
            self._send_changed(libs.panel_cmd.weatherPictures, "~".join(pictures), force=repainted)

        statusUpdateResult = ""
        icon1font = ""
        icon2font = ""
        if self.statusIcon1:
            si1 = (self.statusIcon1.render() or "~~~~~~").split('~')
            statusUpdateResult += f"{si1[3]}~{si1[4]}"
            icon1font = self.statusIcon1.font
        else:
            statusUpdateResult += "~"
        if self.statusIcon2:
            si2 = (self.statusIcon2.render() or "~~~~~~").split('~')
            statusUpdateResult += f"~{si2[3]}~{si2[4]}"
            icon2font = self.statusIcon2.font
        else:
            statusUpdateResult += "~~"

        self._send_changed(libs.panel_cmd.statusUpdate, f"{statusUpdateResult}~{icon1font}~{icon2font}")


def card_factory(locale, settings, panel):
    match settings["type"]:
        case 'cardEntities' | 'cardGrid':
            card = EntitiesCard(locale, settings, panel)
        case 'cardQR':
            card = QRCard(locale, settings, panel)
        case 'cardPower':
            card = PowerCard(locale, settings, panel)
        case 'cardMedia':
            card = MediaCard(locale, settings, panel)
        case 'cardThermo':
            card = ClimateCard(locale, settings, panel)
        case 'cardAlarm':
            card = AlarmCard(locale, settings, panel)
        case 'cardUnlock':
            card = UnlockCard(locale, settings, panel)
        case 'cardChart' | 'cardLChart':
            card = ChartCard(locale, settings, panel)
        case _:
            logging.error("card type %s not implemented", settings["type"])
            return "NotImplemented", None
    return card.iid, card

def option_list(options, limit):
    """Options for the display's "?"-separated lists: no "?" or "~" inside an option (it would split the
    list or the command), and only as many as fit into the display variable (indexes stay the same)."""
    out, size = [], 0
    for option in options or []:
        text = str(option).replace("?", "").replace("~", "-")
        if size + len(text.encode("utf-8")) + (1 if out else 0) > limit:
            break
        size += len(text.encode("utf-8")) + (1 if out else 0)
        out.append(text)
    return "?".join(out)


def _clock(seconds):
    """Minutes and seconds for the timer popup; hours count as minutes (1:30:00 -> 90:00)."""
    seconds = max(0, int(round(seconds)))
    return seconds // 60, seconds % 60


def _duration_seconds(text):
    try:
        parts = [float(part) for part in str(text).split(":")]
    except ValueError:
        return 0
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[-3] * 3600 + parts[-2] * 60 + parts[-1]


def detail_open(locale, detail_type, ha_entity_id, entity_id, msg_out_queue, sendTopic=None, options_list=None):
    data = libs.home_assistant.get_entity_data(ha_entity_id)
    if data:
        state = data.get("state")
        attributes = data.get("attributes", [])
    else:
        logging.error("popup entity %s not found", ha_entity_id)
        return

    match detail_type:
        case 'popupShutter' | 'cover':
            entityType   = "cover"
            device_class = attributes.get("device_class", "window")
            icon_id      = ha_icons.get_icon_ha(entityType, state)

            pos = attributes.get("current_position")
            if pos is None:
                pos_status = state
                pos = "disable"
            else:
                pos_status = pos

            pos_translation = ""
            icon_up   = ""
            icon_stop = ""
            icon_down = ""
            icon_up_status = "disable"
            icon_stop_status = "disable"
            icon_down_status = "disable"
            textTilt = ""
            iconTiltLeft = ""
            iconTiltStop = ""
            iconTiltRight = ""
            iconTiltLeftStatus = "disable"
            iconTiltStopStatus = "disable"
            iconTiltRightStatus = "disable"
            tilt_pos = "disable"

            bits = attributes.get("supported_features") or 0
            # The position slider only for covers that can go to a position (SUPPORT_SET_POSITION).
            slider = pos if bits & 0b00000100 else "disable"

            # position supported
            if bits & 0b00001111:
                pos_translation = get_translation(locale, "frontend.ui.card.cover.position")
            if bits & 0b00000001: # SUPPORT_OPEN
                if ( pos != 100 and not (state == "open" and pos == "disable") ):
                    icon_up_status = "enable"
                icon_up   = ha_icons.get_action_icon(etype=entityType, action="open", device_class=device_class)
            if bits & 0b00000010: # SUPPORT_CLOSE
                if ( pos != 0 and not (state == "closed" and pos == "disable") ):
                    icon_down_status = "enable"
                icon_down = ha_icons.get_action_icon(etype=entityType, action="close", device_class=device_class)
            if bits & 0b00001000: # SUPPORT_STOP
                icon_stop = ha_icons.get_action_icon(etype=entityType, action="stop", device_class=device_class)
                icon_stop_status = "enable"

            # tilt supported
            if bits & 0b11110000:
                textTilt = get_translation(locale, "frontend.ui.card.cover.tilt_position")
            if bits & 0b00010000: # SUPPORT_OPEN_TILT
                iconTiltLeft = get_icon_char('arrow-top-right')
                iconTiltLeftStatus = "enable"
            if bits & 0b00100000: # SUPPORT_CLOSE_TILT
                iconTiltRight = get_icon_char('arrow-bottom-left')
                iconTiltRightStatus = "enable"
            if bits & 0b01000000: # SUPPORT_STOP_TILT
                iconTiltStop = get_icon_char('stop')
                iconTiltStopStatus = "enable"
            if bits & 0b10000000: # SUPPORT_SET_TILT_POSITION
                tilt_pos = attributes.get("current_tilt_position")
                if tilt_pos is None:
                    tilt_pos = "disable"
                if(tilt_pos == 0):
                    iconTiltRightStatus = "disable"
                if(tilt_pos == 100):
                    iconTiltLeftStatus  = "disable"

            return f'{entity_id}~{slider}~{pos_translation}: {pos_status}~{pos_translation}~{icon_id}~{icon_up}~{icon_stop}~{icon_down}~{icon_up_status}~{icon_stop_status}~{icon_down_status}~{textTilt}~{iconTiltLeft}~{iconTiltStop}~{iconTiltRight}~{iconTiltLeftStatus}~{iconTiltStopStatus}~{iconTiltRightStatus}~{tilt_pos}'

        case 'popupLight' | 'light':
            switch_val = 1 if state == "on" else 0
            icon_color = 6666
            brightness = "disable"
            color_temp = "disable"
            color = "disable"
            effect_supported = "disable"

            if "onoff" not in (attributes.get("supported_color_modes") or []):
                brightness = 0
            if state == "on":
                if "brightness" in attributes and attributes.get("brightness"):
                    # scale 0-255 brightness from ha to 0-100
                    brightness = round(scale(attributes.get("brightness"),(0,255),(0,100)))
                else:
                    brightness = "disable"
                if "color_temp" in (attributes.get("supported_color_modes") or []):
                    color_temp = temperature_slider(attributes)
                else:
                    color_temp = "disable"
                list_color_modes = ["xy", "rgb", "rgbw", "rgbww", "hs"]
                if any(item in list_color_modes for item in (attributes.get("supported_color_modes") or [])):
                    color = "enable"
                else:
                    color = "disable"
                if attributes.get("effect_list"):
                    effect_supported = "enable"
            color_translation      = "Color"
            brightness_translation = get_translation(locale, "frontend.ui.card.light.brightness")
            color_temp_translation = get_translation(locale, "frontend.ui.card.light.color_temperature")
            return f'{entity_id}~~{icon_color}~{switch_val}~{brightness}~{color_temp}~{color}~{color_translation}~{color_temp_translation}~{brightness_translation}~{effect_supported}'
        case 'popupFan' | 'fan':
            switch_val = 1 if state == "on" else 0
            icon_color = ha_colors.get_entity_color("fan", state, attributes)
            speed = attributes.get("percentage")
            percentage_step = attributes.get("percentage_step")
            speedMax = 100
            if percentage_step is None:
                speed = "disable"
            else:
                if speed is None:
                    speed = 0
                speed = round(speed/percentage_step)
                speedMax = round(100/percentage_step)

            speed_translation = get_translation(locale, "frontend.ui.card.fan.speed")

            preset_mode = attributes.get("preset_mode") or ""
            preset_modes = option_list(attributes.get("preset_modes"), 380)

            return f'{entity_id}~~{icon_color}~{switch_val}~{speed}~{speedMax}~{speed_translation}~{preset_mode}~{preset_modes}'
        case 'popupThermo' | 'climate':
            icon_id      = ha_icons.get_icon_ha("climate", state)
            icon_color  = ha_colors.get_entity_color("climate", state, attributes)

            modes_out = ""
            for mode in ["preset_modes", "swing_modes", "fan_modes"]:
                heading = get_translation(locale, f"frontend.ui.card.climate.{mode[:-1]}")
                cur_mode = attributes.get(mode[:-1]) or ""
                modes = attributes.get(mode, [])
                if modes is not None:
                    if mode == "preset_modes":
                        translated_modes = []
                        for elem in modes:
                            translated_modes.append(get_translation(locale, f"frontend.state_attributes.climate.preset_mode.{elem}"))
                        if cur_mode:
                            cur_mode = get_translation(locale, f"frontend.state_attributes.climate.preset_mode.{cur_mode}")
                        modes_res = option_list(translated_modes, 120)
                    else:
                        modes_res = option_list(modes, 120)  # three lists share the 500 characters
                    if modes:
                        modes_out += f"{heading}~{mode}~{cur_mode}~{modes_res}~"

            return f"{entity_id}~{icon_id}~{icon_color}~{modes_out}"



        case 'popupInSel' | 'input_select' | 'select' | 'media_player':
            hatype = ha_entity_id.split(".")[0]
            options = []
            icon_color = 0
            icon_color = ha_colors.get_entity_color(detail_type, state, attributes)
            state = state
            if hatype in ["input_select", "select"]:
                options = attributes.get("options", [])
            elif hatype == "light":
                if options_list is not None:
                    options = options_list
                else:
                    options = attributes.get("effect_list", [])[:15]
                state = attributes.get("effect")
            elif hatype == "media_player":
                state = attributes.get("source", "")
                options = attributes.get("source_list", [])
            state = "" if state is None else str(state).replace("~", "-")
            options = option_list(options, 850)
            return f"{entity_id}~~{icon_color}~{hatype}~{state}~{options}~"


        case 'popupTimer' | 'timer':
            # Refreshed every second by the panel while it is active (LovelaceUIPanel.on_time_tick).
            icon_color = ha_colors.get_entity_color("timer", state, attributes)
            action1 = action2 = action3 = label1 = label2 = label3 = ""
            editable = 0
            if state in ["idle", "paused"]:
                editable = 1 if state == "idle" else 0
                remaining = attributes.get("remaining") if state == "paused" else attributes.get("duration")
                minutes, seconds = _clock(_duration_seconds(remaining))
                action2 = "start"
                label2 = get_translation(locale, "frontend.ui.card.timer.actions.start")
                if state == "paused":
                    action1, action3 = "cancel", "finish"
                    label1 = get_translation(locale, "frontend.ui.card.timer.actions.cancel")
                    label3 = get_translation(locale, "frontend.ui.card.timer.actions.finish")
            elif state == "active" and attributes.get("finishes_at"):
                try:
                    finishes_at = datetime.datetime.fromisoformat(attributes["finishes_at"])
                    left = (finishes_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                except (TypeError, ValueError):
                    left = _duration_seconds(attributes.get("remaining"))
                minutes, seconds = _clock(left)
                action1, action2, action3 = "pause", "cancel", "finish"
                label1 = get_translation(locale, "frontend.ui.card.timer.actions.pause")
                label2 = get_translation(locale, "frontend.ui.card.timer.actions.cancel")
                label3 = get_translation(locale, "frontend.ui.card.timer.actions.finish")
            else:  # unavailable, unknown: show 0:00 without buttons
                minutes, seconds = 0, 0
            return f'{entity_id}~~{icon_color}~{entity_id}~{minutes}~{seconds}~{editable}~{action1}~{action2}~{action3}~{label1}~{label2}~{label3}'
        case _:
            logging.error("popup type %s not implemented", detail_type)
            return "NotImplemented", None
