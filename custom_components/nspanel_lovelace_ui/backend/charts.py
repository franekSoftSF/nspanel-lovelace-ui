"""cardChart (bars) and cardLChart (line): recorder history -> the HMI chart payloads.

Payloads after "entityUpd~<title>~<navigation (12 fields)>~" (HMI n2t-out/cardChart.txt, cardLChart.txt):
  cardChart:  <colour>~<y label>~<y ticks a:b:c>~<value>[^<label>]~<value>…        (values from field 17)
  cardLChart: <colour>~<y label>~<y ticks a:b:c>~<x tick>[^<label>]+<x tick>…~<x>:<y>~<x>:<y>…  (points from 18)
All numbers are integers; the display shows y values and ticks divided by 10 (one decimal).

Limits of the display code, handled here:
  - bars: the scale is (height-24)/max on integers, so the largest bar must stay at about 176 (17.6
    shown) or the bars vanish; bigger values are divided by 10^n and the y label gets "×10^n";
    bars cannot go below zero (clipped); the whole command has at most 275 characters.
  - line: the command has at most 512 characters, each field at most 400.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

BAR_MAX = 170          # largest bar in display units (tenths)
BAR_COMMAND = 275      # strCommand of cardChart
LINE_COMMAND = 512     # strCommand of cardLChart
AGGREGATES = ("mean", "max", "min", "last", "change")


def to_float(state: Any) -> float | None:
    try:
        value = float(state)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def buckets(points: list[tuple[datetime, float]], start: datetime, end: datetime, count: int,
            aggregate: str = "mean") -> list[float | None]:
    """One value per interval; a state lasts until the next one (the value before an interval counts)."""
    span = (end - start) / count
    points = sorted(points)
    result: list[float | None] = []
    index = 0
    current: float | None = None
    while index < len(points) and points[index][0] <= start:
        current = points[index][1]
        index += 1
    for number in range(count):
        stop = start + span * (number + 1)
        values = [] if current is None else [current]
        first = current
        while index < len(points) and points[index][0] < stop:
            current = points[index][1]
            values.append(current)
            index += 1
        if not values:
            result.append(None)
        elif aggregate == "max":
            result.append(max(values))
        elif aggregate == "min":
            result.append(min(values))
        elif aggregate == "last":
            result.append(values[-1])
        elif aggregate == "change":  # counters (energy): growth in the interval, resets ignored
            result.append(max(0.0, values[-1] - (first if first is not None else values[0])))
        else:
            result.append(sum(values) / len(values))
    return result


def nice_step(span: float, count: int = 4) -> float:
    """1, 2, 2.5 or 5 × 10^n so that about count steps cover span."""
    raw = max(span, 1e-9) / count
    power = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if raw <= factor * power:
            return factor * power
    return 10 * power


def _ticks(low: float, high: float, step: float) -> list[float]:
    first = math.floor(low / step) * step
    ticks, value = [], first
    while value < high + step * 0.999 and len(ticks) < 12:
        ticks.append(round(value, 6))
        value += step
    return ticks


def _label_text(label: str, factor: int) -> str:
    return f"{label} ×{factor}" if factor > 1 else label


def bar_payload(values: list[float | None], labels: list[str], y_label: str, colour: int,
                budget: int) -> str:
    """cardChart fields after the navigation; budget = characters left in the command."""
    known = [max(0.0, v) for v in values if v is not None]
    top = max(known, default=0.0)
    factor = 1
    while top / factor * 10 > BAR_MAX:  # keep the largest bar under the display limit
        factor *= 10
    step = nice_step(top / factor)
    step = max(step, 0.1)
    ticks = [t for t in _ticks(0, max(top / factor, step), step) if t > 0]
    head = f"{colour}~{_label_text(y_label, factor)}~{':'.join(str(round(t * 10)) for t in ticks)}"
    bars = []
    for value, label in zip(values, labels):
        text = str(round(max(0.0, value or 0.0) / factor * 10))
        bars.append(f"{text}^{label}" if label else text)
    # Drop the oldest bars if the command would not fit (the newest are the interesting ones).
    while bars and len(head) + sum(len(b) + 1 for b in bars) > budget:
        bars.pop(0)
    return head + "".join(f"~{b}" for b in bars)


def line_payload(points: list[tuple[int, float]], x_ticks: list[tuple[int, str]], y_label: str,
                 colour: int, budget: int) -> str:
    """cardLChart fields after the navigation; x in minutes from the start, y in display units."""
    values = [v for _, v in points]
    low, high = (min(values), max(values)) if values else (0.0, 1.0)
    if high - low < 0.5:
        low, high = low - 0.5, high + 0.5
    step = nice_step(high - low)
    if low < 0:
        step = max(step, 1.0)  # the display shows negative ticks well only as whole numbers
    ticks = _ticks(low, high, step)
    x_field = "+".join(f"{x}^{label}" if label else str(x) for x, label in x_ticks) or "0"
    head = f"{colour}~{y_label}~{':'.join(str(round(t * 10)) for t in ticks)}~{x_field}"
    body = [f"{x}:{round(v * 10)}" for x, v in points]
    while len(body) > 2 and len(head) + sum(len(p) + 1 for p in body) > budget:
        body = body[::2] if len(body) > 4 else body[1:]  # thin out evenly
    return head + "".join(f"~{p}" for p in body)


def time_label(moment: datetime, span: timedelta) -> str:
    return moment.strftime("%H:%M") if span <= timedelta(hours=48) else moment.strftime("%d.%m")


def label_every(count: int, wanted: int = 4) -> int:
    return max(1, math.ceil(count / wanted))
