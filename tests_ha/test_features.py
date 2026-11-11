"""Firmware 55 features: weather icons/colours/pictures, grid layout (#1190), timeTemplate (#1405), flash progress."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from homeassistant.components.update import ATTR_UPDATE_PERCENTAGE
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_mqtt_message

from custom_components.nspanel_lovelace_ui.backend import weather
from custom_components.nspanel_lovelace_ui.backend.libs.helper import rgb_dec565
from custom_components.nspanel_lovelace_ui.backend.libs.icon_mapping import get_icon_char
from custom_components.nspanel_lovelace_ui.const import CONF_CONFIG_FILE, DEFAULT_CONFIG_FILE, DOMAIN

from .conftest import RECV, published, wait_for
from .test_firmware import BASE, make_package

FORECAST = [
    {"datetime": "2026-11-12T12:00:00+00:00", "condition": "sunny", "temperature": 19.5},
    {"datetime": "2026-11-13T12:00:00+00:00", "condition": "rainy", "temperature": 14.9},
    {"datetime": "2026-11-14T12:00:00+00:00", "condition": "lightning-rainy", "temperature": 9.9},
    {"datetime": "2026-11-15T12:00:00+00:00", "condition": "snowy", "temperature": 10.0},
]


def _recv(hass: HomeAssistant, message: str) -> None:
    async_fire_mqtt_message(hass, RECV, json.dumps({"CustomRecv": message}))


def _edit(panels_file: Path, change) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    change(config, config["nspanels"]["living_room"])
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    hass.states.async_set("light.bed_light", "off", {"friendly_name": "Lampka"})
    hass.states.async_set("switch.decorative_lights", "on", {"friendly_name": "Dekor"})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CONFIG_FILE: DEFAULT_CONFIG_FILE})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await wait_for(hass, lambda: "pageType~pageStartup" in [p for p in published_all(hass)])
    return entry


def published_all(hass: HomeAssistant) -> list[str]:
    return published(hass.data["_mqtt_mock"])


@pytest.fixture(autouse=True)
def _keep_mock(hass: HomeAssistant, mqtt_mock):
    hass.data["_mqtt_mock"] = mqtt_mock


# --- weather module (task 2) -------------------------------------------------------------

def test_weather_icons_and_colours() -> None:
    assert weather.mdi_icon("partlycloudy") == "weather-partly-cloudy"
    assert weather.mdi_icon("partlycloudy", night=True) == "weather-night-partly-cloudy"
    assert weather.mdi_icon("exceptional") == "weather-cloudy-alert"
    assert weather.mdi_icon("unknown-condition") == "alert-circle-outline"
    # windy-variant had no colour before (a typo assigned nothing).
    assert weather.color("windy-variant") == rgb_dec565([180, 180, 180])
    assert weather.color("sunny") == rgb_dec565([253, 217, 60])
    assert weather.color("sunny", night=True) == rgb_dec565([252, 244, 151])
    assert weather.picture_index("sunny") == 0
    assert weather.picture_index("partlycloudy", night=True) == 4
    assert weather.picture_index("sunny", forecast=True) == len(weather.PICTURES)
    assert weather.forecast_is_night({"is_daytime": False}, hourly=True)
    assert not weather.forecast_is_night({"is_daytime": False}, hourly=False)


# --- screensaver: forecast colours, night icon, colour pictures (tasks 1 and 2) ------------

@pytest.fixture
def weather_panel(hass: HomeAssistant, panels_file: Path) -> Path:
    def change(config, panel):
        panel["screensaver"] = {"entities": [{"entity": "weather.home"}] + [
            {"entity": "weather.home", "day": day} for day in range(4)]}
    _edit(panels_file, change)

    async def forecasts(call: ServiceCall):
        return {"weather.home": {"forecast": FORECAST}}

    hass.services.async_register("weather", "get_forecasts", forecasts, supports_response=SupportsResponse.ONLY)
    hass.states.async_set("weather.home", "partlycloudy", {"temperature": 17.9})
    hass.states.async_set("sun.sun", "below_horizon")
    return panels_file


def _weather_payload(hass: HomeAssistant) -> list[str]:
    return [p for p in published_all(hass) if p.startswith("weatherUpdate~")][-1].split("~")[1:]


async def test_forecast_uses_its_own_condition(hass: HomeAssistant, weather_panel: Path) -> None:
    entry = await _setup(hass)
    _recv(hass, "event,startup,54,eu")  # firmware 54: font icons only
    _recv(hass, "event,renderCurrentPage")  # the screensaver asks for its content
    await wait_for(hass, lambda: any(
        p.startswith("weatherUpdate~") and get_icon_char("weather-pouring") not in p
        and get_icon_char("weather-lightning-rainy") in p for p in published_all(hass)))
    fields = _weather_payload(hass)
    # Today at night: moon behind the cloud; each forecast day keeps its own icon and colour.
    assert fields[2] == get_icon_char("weather-night-partly-cloudy")
    assert fields[8] == get_icon_char("weather-sunny") and fields[9] == str(weather.color("sunny"))
    assert fields[14] == get_icon_char("weather-rainy") and fields[15] == str(weather.color("rainy"))
    assert fields[20] == get_icon_char("weather-lightning-rainy")
    assert fields[26] == get_icon_char("weather-snowy") and fields[27] == str(weather.color("snowy"))
    assert not any(p.startswith("weatherPics~") for p in published_all(hass))
    await hass.config_entries.async_unload(entry.entry_id)


async def test_colour_pictures_on_firmware_55(hass: HomeAssistant, weather_panel: Path) -> None:
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    _recv(hass, "event,renderCurrentPage")
    base = weather.PICTURE_BASE["eu"]
    expected = "~".join(["weatherPics", str(base + weather.picture_index("partlycloudy", night=True))] + [
        str(base + weather.picture_index(day["condition"], forecast=True)) for day in FORECAST])
    # (the first render comes before the forecast is loaded; the forecast arrives a moment later)
    await wait_for(hass, lambda: expected in published_all(hass))
    fields = _weather_payload(hass)
    assert fields[2] == "" and fields[8] == ""  # no font icon drawn under the pictures
    await hass.config_entries.async_unload(entry.entry_id)


async def test_pictures_off_for_other_backgrounds(hass: HomeAssistant, weather_panel: Path) -> None:
    _edit(weather_panel, lambda config, panel: panel["screensaver"].update(theme={"background": [0, 0, 64]}))
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: any(p.startswith("weatherUpdate~") for p in published_all(hass)))
    await wait_for(hass, lambda: "weatherPics~~~~~" in published_all(hass))  # hide any old pictures
    assert not any(p.startswith("weatherPics~") and p != "weatherPics~~~~~" for p in published_all(hass))
    await hass.config_entries.async_unload(entry.entry_id)


# --- grid layout follows visible entities (task 7, #1190) ---------------------------------

async def test_grid_layout_follows_visible_entities(hass: HomeAssistant, panels_file: Path) -> None:
    def change(config, panel):
        panel["cards"] = [{"type": "cardGrid", "title": "Grid", "entities": [
            {"entity": f"switch.s{i}"} for i in range(6)] + [{"entity": "switch.s6", "state": "on"}]}]
    _edit(panels_file, change)
    for i in range(7):
        hass.states.async_set(f"switch.s{i}", "off")
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    _recv(hass, "event,buttonPress2,screensaver,bExit,1")
    # 7 configured, but switch.s6 is hidden (state filter): 6 visible -> 3x2 cardGrid.
    await wait_for(hass, lambda: "pageType~cardGrid2" in published_all(hass))
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: published_all(hass)[-1] == "pageType~cardGrid")
    _recv(hass, "event,renderCurrentPage")
    await wait_for(hass, lambda: published_all(hass)[-1].startswith("entityUpd~Grid"))
    # The 7th becomes visible -> back to 4x2.
    hass.states.async_set("switch.s6", "on")
    await wait_for(hass, lambda: published_all(hass)[-1] == "pageType~cardGrid2")
    await hass.config_entries.async_unload(entry.entry_id)


# --- timeTemplate instead of the clock (task 8, #1405) -----------------------------------

async def test_time_template_replaces_the_clock(hass: HomeAssistant, panels_file: Path) -> None:
    _edit(panels_file, lambda config, panel: panel.update(
        timeTemplate="{{ states('sensor.panel_temp') }}°"))
    hass.states.async_set("sensor.panel_temp", "21.5")
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    await wait_for(hass, lambda: any(p.startswith("time~21.5°") for p in published_all(hass)))
    hass.states.async_set("sensor.panel_temp", "22.0")
    await wait_for(hass, lambda: any(p.startswith("time~22.0°") for p in published_all(hass)))
    await hass.config_entries.async_unload(entry.entry_id)


# --- flash progress (task 9, #995) --------------------------------------------------------

async def _start_install(hass: HomeAssistant, panels_file: Path):
    panels_file.write_text(f"firmware_base_url: {BASE}\n" + panels_file.read_text(encoding="utf-8"), encoding="utf-8")
    make_package(Path(hass.config.path("nspanel_lovelace_ui", "firmware")))
    entry = await _setup(hass)
    _recv(hass, "event,startup,54,eu")
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("update", DOMAIN, f"{entry.entry_id}_living_room_display_firmware")
    install = hass.async_create_task(
        hass.services.async_call("update", "install", {"entity_id": entity_id}, blocking=True))
    await wait_for(hass, lambda: published(hass.data["_mqtt_mock"], "cmnd/nspanel_test/FlashNextion"), block=False)
    return entry, entity_id, install


def _flashing(hass: HomeAssistant, flashing: dict) -> None:
    async_fire_mqtt_message(hass, RECV, json.dumps({"Flashing": flashing}))


async def test_flash_progress_is_shown(hass: HomeAssistant, panels_file: Path) -> None:
    entry, entity_id, install = await _start_install(hass, panels_file)
    _flashing(hass, {"complete": 42, "time_elapsed": 10})
    await wait_for(hass, lambda: hass.states.get(entity_id).attributes[ATTR_UPDATE_PERCENTAGE] == 42, block=False)
    _recv(hass, "event,startup,55,eu")
    async with asyncio.timeout(10):
        await install
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes[ATTR_UPDATE_PERCENTAGE] is None
    await hass.config_entries.async_unload(entry.entry_id)


async def test_flash_error_fails_the_install(hass: HomeAssistant, panels_file: Path) -> None:
    entry, entity_id, install = await _start_install(hass, panels_file)
    _flashing(hass, {"error": "download failed (HTTP status)"})
    with pytest.raises(HomeAssistantError):
        async with asyncio.timeout(10):
            await install
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)


def test_picture_files_match_the_backend_order() -> None:
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("build_pictures", root / "HMI/code_gen/weather/build_pictures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert list(module.SVGS) == weather.PICTURES
    files = sorted(p.name for p in (root / "HMI/pictures/weather").glob("*.png"))
    expected = [f"{i:02d}-{size}-{name}.png" for i, (size, name) in enumerate(
        [("main", n) for n in weather.PICTURES] + [("forecast", n) for n in weather.PICTURES])]
    assert files == expected


@pytest.mark.parametrize("variant", ["eu", "us-p", "us-l"])
def test_hmi_patches_apply_to_the_current_code(variant) -> None:
    """HMI/code_gen/patches_55.py finds all its anchors in the nextion2text dumps."""
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("patches_55", root / "HMI/code_gen/patches_55.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = module.screensaver_files(module.VARIANTS[variant], variant)
    serial = "\n".join(files["02-screensaver-tmSerial-TimerEvent.txt"])
    assert 'tInstruction.txt=="weatherPics"' in serial
    assert serial.index('"weatherPics"') < serial.index('tInstruction.txt=="color"')
    touch = "\n".join(files["03-screensaver-tc0-TouchPressEvent.txt"])
    # closing a notification asks the backend to send the screensaver (and its pictures) again
    assert touch.index('tSend.txt="event,renderCurrentPage"') > touch.index("vis tNotifyText,0")
    saved = (root / "HMI/patches/55" / variant / "02-screensaver-tmSerial-TimerEvent.txt").read_text(encoding="utf-8")
    assert saved.replace("\r\n", "\n").rstrip("\n") == serial


async def test_pictures_resent_after_a_repaint(hass: HomeAssistant, weather_panel: Path) -> None:
    """weatherUpdate repaints the icon boxes under the pictures: weatherPics must follow it."""
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    _recv(hass, "event,renderCurrentPage")
    base = weather.PICTURE_BASE["eu"]
    main = str(base + weather.picture_index("partlycloudy", night=True))
    await wait_for(hass, lambda: any(p.startswith(f"weatherPics~{main}~{base + 15}") for p in published_all(hass)))
    count = sum(p.startswith("weatherPics~") for p in published_all(hass))
    hass.states.async_set("weather.home", "partlycloudy", {"temperature": 18.4})  # same condition
    await wait_for(hass, lambda: any("18.4" in p for p in published_all(hass) if p.startswith("weatherUpdate~")))
    await wait_for(hass, lambda: sum(p.startswith("weatherPics~") for p in published_all(hass)) > count)
    sent = published_all(hass)
    last_pics = max(i for i, p in enumerate(sent) if p.startswith("weatherPics~"))
    last_update = max(i for i, p in enumerate(sent) if p.startswith("weatherUpdate~") and "18.4" in p)
    assert last_pics > last_update  # same picture IDs, sent again after the repaint
    await hass.config_entries.async_unload(entry.entry_id)


async def test_pictures_follow_visible_slots_and_icons(hass: HomeAssistant, weather_panel: Path) -> None:
    def change(config, panel):
        entities = panel["screensaver"]["entities"]
        entities[1]["state"] = "never"  # forecast day 0 hidden: day 1 moves into slot 1
        entities[3]["icon"] = "mdi:home"  # configured icon: keep the font icon
    _edit(weather_panel, change)
    entry = await _setup(hass)
    _recv(hass, "event,startup,55,eu")
    _recv(hass, "event,renderCurrentPage")
    base = weather.PICTURE_BASE["eu"]
    expected = "~".join(["weatherPics", str(base + weather.picture_index("partlycloudy", night=True)),
                         str(base + weather.picture_index("rainy", forecast=True)), "",
                         str(base + weather.picture_index("snowy", forecast=True)), ""])
    await wait_for(hass, lambda: expected in published_all(hass))
    await hass.config_entries.async_unload(entry.entry_id)
