"""cardChart / cardLChart: history buckets, display limits (HMI cardChart/cardLChart) and the panel payload."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.nspanel_lovelace_ui.backend import charts
from custom_components.nspanel_lovelace_ui.backend.config_schema import collect_issues
from custom_components.nspanel_lovelace_ui.backend.libs import home_assistant as bridge

from .conftest import published, wait_for
from .test_entities import _recv, _setup, _unload

T0 = datetime(2026, 11, 12, 0, 0, tzinfo=timezone.utc)


def test_buckets_carry_the_previous_state() -> None:
    points = [(T0 - timedelta(hours=1), 5.0), (T0 + timedelta(minutes=30), 7.0), (T0 + timedelta(hours=2, minutes=10), 1.0)]
    end = T0 + timedelta(hours=3)
    assert charts.buckets(points, T0, end, 3, "mean") == [6.0, 7.0, 4.0]
    assert charts.buckets(points, T0, end, 3, "max") == [7.0, 7.0, 7.0]
    assert charts.buckets(points, T0, end, 3, "last") == [7.0, 7.0, 1.0]
    counter = [(T0, 100.0), (T0 + timedelta(minutes=50), 103.5), (T0 + timedelta(hours=1, minutes=30), 104.0)]
    assert charts.buckets(counter, T0, end, 3, "change") == [3.5, 0.5, 0.0]
    assert charts.buckets([], T0, end, 2) == [None, None]


@pytest.mark.parametrize(("span", "step"), [(10, 2.5), (17, 5), (0.8, 0.2), (2500, 1000)])
def test_nice_steps(span: float, step: float) -> None:
    assert charts.nice_step(span) == step


def test_bar_payload_keeps_bars_under_the_display_limit() -> None:
    payload = charts.bar_payload([1200.0, 2500.0, None, 300.0], ["0:00", "", "", "18:00"], "W", 1234, 200)
    colour, label, ticks, *bars = payload.split("~")
    assert colour == "1234" and label == "W ×1000"  # 2500 W -> 25 (2.5 shown) ×1000
    assert bars == ["12^0:00", "25", "0", "3^18:00"]
    assert max(int(bar.split("^")[0]) for bar in bars) <= charts.BAR_MAX
    assert [int(t) for t in ticks.split(":")] == [10, 20, 30]  # ticks above the top bar are not drawn
    small = charts.bar_payload([1.5, 3.2], ["", ""], "kWh", 1, 200).split("~")
    assert small[1] == "kWh" and small[3:] == ["15", "32"]
    many = charts.bar_payload([1.0] * 100, [""] * 100, "x", 1, 120)
    assert len(many) <= 120 and many.endswith("~10")  # the oldest bars are dropped


def test_line_payload() -> None:
    payload = charts.line_payload([(30, -2.0), (90, 1.5), (150, 4.0)], [(0, "0:00"), (120, "2:00")], "°C", 7, 400)
    colour, label, ticks, xticks, *points = payload.split("~")
    assert (colour, label, xticks) == ("7", "°C", "0^0:00+120^2:00")
    assert points == ["30:-20", "90:15", "150:40"]
    assert all(int(t) % 10 == 0 for t in ticks.split(":"))  # whole numbers when below zero
    values = [int(t) for t in ticks.split(":")]
    assert values[0] <= -20 and values[-1] >= 40
    long = charts.line_payload([(i, 20.5) for i in range(200)], [(0, "")], "x", 1, 300)
    assert len(long) <= 300


def test_schema_has_both_charts() -> None:
    def config(card):
        return {"nspanels": {"p": {"panelRecvTopic": "tele/p/RESULT", "panelSendTopic": "cmnd/p/CustomSend",
                                   "screensaver": {"entities": []}, "cards": [card]}}}
    def card_issues(card):
        return [(i.path[4:], i.code) for i in collect_issues(config(card)) if i.path[3:4] == [0]]
    assert card_issues({"type": "cardChart"}) == [(["entity"], "required")]
    assert card_issues({"type": "cardLChart", "entity": "sensor.t", "hours": 168, "points": 60}) == []
    assert (["bars"], "range") in card_issues({"type": "cardChart", "entity": "sensor.t", "bars": 80})


async def test_bar_chart_on_the_panel(hass: HomeAssistant, mqtt_mock, panels_file: Path) -> None:
    config = yaml.safe_load(panels_file.read_text(encoding="utf-8"))
    config["nspanels"]["living_room"]["cards"].insert(0, {
        "type": "cardChart", "title": "Prąd", "entity": "sensor.power", "hours": 6, "bars": 6, "color": [255, 0, 0]})
    panels_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    hass.states.async_set("sensor.power", "800", {"unit_of_measurement": "W", "friendly_name": "Moc"})
    now = dt_util.utcnow()
    history = [(now - timedelta(hours=6, minutes=10), "400"), (now - timedelta(hours=3), "unavailable"),
               (now - timedelta(hours=1, minutes=30), "1600")]
    with patch.object(bridge, "get_history", return_value=history) as get_history:
        entry = await _setup(hass, mqtt_mock)
        _recv(hass, "event,buttonPress2,screensaver,bExit,1")
        await wait_for(hass, lambda: "pageType~cardChart" in published(mqtt_mock))
        _recv(hass, "event,renderCurrentPage")
        await wait_for(hass, lambda: any(p.startswith("entityUpd~Prąd~") for p in published(mqtt_mock)))
    update = next(p for p in published(mqtt_mock) if p.startswith("entityUpd~Prąd~"))
    fields = update.split("~")
    assert len(update) <= charts.BAR_COMMAND
    assert fields[14] == "63488" and fields[15] == "W ×100"  # red; 1600 W -> 16 (1.6 shown) ×100
    # 1 h bars; "unavailable" is skipped, a bar includes the value it starts with.
    assert [int(f.split("^")[0]) for f in fields[17:]] == [40, 40, 40, 40, 100, 160]
    assert get_history.call_args.args[0] == "sensor.power"
    await _unload(hass, entry)
