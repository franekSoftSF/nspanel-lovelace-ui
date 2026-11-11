"""Icon fonts (HMI/fonts/generated) and the integration's name -> character mapping must match."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "HMI" / "fonts" / "generated"
sys.path.insert(0, str(ROOT / "HMI" / "code_gen" / "fonts"))
zi = importlib.import_module("zi")

from custom_components.nspanel_lovelace_ui.backend.libs import icon_mapping  # noqa: E402

REPORT = json.loads((GENERATED / "report.json").read_text(encoding="utf-8"))
ICON_FONTS = sorted(REPORT["fonts"])
MAPPED = {ord(char) for char in icon_mapping.icons.values()}


@pytest.fixture(scope="module", params=ICON_FONTS)
def raw(request) -> bytes:
    return (GENERATED / request.param).read_bytes()


@pytest.fixture(scope="module")
def font(raw) -> "zi.ZiFont":
    return zi.ZiFont.from_bytes(raw)


def test_mapping_is_generated_from_the_same_mdi_release() -> None:
    header = (ROOT / "custom_components/nspanel_lovelace_ui/backend/libs/icon_mapping.py").read_text(
        encoding="utf-8").splitlines()[0]
    assert f"MDI {REPORT['mdi_version']}" in header
    assert len(MAPPED) == REPORT["icons"]
    assert all(0xE000 <= cp <= 0xFDFF for cp in MAPPED)


def test_every_mapped_icon_has_a_glyph_and_no_extra_icons(font) -> None:
    icon_glyphs = {cp for cp in font.codepoints if cp >= 0xE000}
    assert MAPPED - icon_glyphs == set()
    assert icon_glyphs - MAPPED == set()


def test_text_part_is_kept(font) -> None:
    text = {cp for cp in font.codepoints if cp < 0xE000}
    assert text in (set(), set(range(0x20, 0x100)))


def test_glyphs_decode_to_the_cell_size(font) -> None:
    glyphs = list(font.glyphs.values())
    for glyph in glyphs[:: max(1, len(glyphs) // 500)]:
        assert len(glyph.pixels(font.height)) == glyph.width * font.height


def test_file_round_trip(raw, font) -> None:
    assert font.to_bytes() == raw


def test_encoder_matches_decoder() -> None:
    samples = [[0] * 40, [7] * 40, [0, 0, 7, 3, 0, 7, 7, 7, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5] * 5, [0] * 31 + [7] * 3]
    for px in samples:
        assert zi.decode(zi.encode(px), len(px)) == px


def test_flash_budget() -> None:
    budget = REPORT["budget"]
    assert set(budget["variants"]) == {"eu", "us-p", "us-l"}
    for variant in budget["variants"].values():
        assert variant["estimated_tft"] < budget["flash_bytes"]


def test_lookup_names_aliases_and_fallback() -> None:
    assert icon_mapping.get_icon_char("mdi:home") == icon_mapping.icons["home"]
    # Old names that MDI kept as aliases still resolve ('lecturn' was renamed to 'lectern').
    assert icon_mapping.get_icon_char("mdi:lecturn") == icon_mapping.icons["lectern"]
    # Removed names fall back instead of showing an unrelated icon on a reused code point.
    assert icon_mapping.get_icon_char("mdi:google-home") == icon_mapping.icons["alert-circle-outline"]
    assert icon_mapping.get_icon_char("mdi:does-not-exist") == icon_mapping.icons["alert-circle-outline"]


# --- Nextion Editor build data (HMI/BUILD.md) ---------------------------------------------

hmi_info = importlib.import_module("hmi_info")


@pytest.mark.parametrize(("variant", "orientation", "icon_fonts", "next_index"), [
    ("eu", 3, {1: 32, 3: 48, 4: 80}, 8),
    ("us-p", 2, {1: 32, 3: 48, 4: 80}, 7),
    ("us-l", 3, {1: 32, 3: 48, 4: 80}, 8),
])
def test_hmi_font_indexes_match_build_guide(variant, orientation, icon_fonts, next_index) -> None:
    info = hmi_info.hmi_info(ROOT / hmi_info.VARIANTS[variant]["hmi"])
    assert info["model_crc"] == hmi_info.MODEL_CRC
    assert info["orientation"] == orientation
    assert info["encoding"] == 0x18  # utf-8
    fonts = {font["index"]: font for font in info["fonts"]}
    # Before the rebuild: Nextion Editor's fonts (7120 glyphs). After it (firmware 55): the
    # generated ones (7671) plus the 64 px icon font appended at next_index.
    rebuilt = fonts[1]["glyphs"] == 7671
    for index, height in icon_fonts.items():  # the fonts BUILD.md says to replace
        assert fonts[index]["height"] == height and fonts[index]["glyphs"] == (7671 if rebuilt else 7120)
    if rebuilt:
        assert len(fonts) == next_index + 1
        assert fonts[next_index]["height"] == 64 and fonts[next_index]["glyphs"] == 7447
    else:
        assert len(fonts) == next_index


def test_large_icon_font_default_follows_the_variant() -> None:
    from custom_components.nspanel_lovelace_ui.backend.ha_cards import large_icon_font_id

    assert large_icon_font_id({"model": "eu"}) == 8
    assert large_icon_font_id({"model": "us-l"}) == 8
    assert large_icon_font_id({"model": "us-p"}) == 7
    assert large_icon_font_id({"model": "us-p", "largeIconFontId": 9}) == 9


@pytest.mark.parametrize("variant", ["eu", "us-p", "us-l"])
def test_current_tft_passes_the_pre_flash_check(variant) -> None:
    folder = Path(hmi_info.VARIANTS[variant]["hmi"]).parent
    assert hmi_info.check_tft(variant, ROOT / folder / hmi_info.VARIANTS[variant]["tft"]) == []
