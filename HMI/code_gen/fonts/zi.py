"""Reader/writer for Nextion .zi fonts (version 6, 3-bit anti-aliased, UTF-8).

Format reverse-engineered by hagronnestad/nextion-font-editor (ZI v5 spec) and verified here:
re-encoding the icon fonts that Nextion Editor generated for this project reproduces every
glyph byte for byte (32 px: 7120/7120, 48 px: 7119/7119, 80 px: 4584/4584 readable glyphs).

Layout:
    0x00  44-byte header (see HEADER below)
    0x2C  font name + encoding, e.g. "NotoSans-Regularutf-8" (total length at 0x11,
          name length without the encoding at 0x20)
          character map: 10 bytes per glyph, sorted by code point
              u16 code point, u8 width, u8 x-offset?, u8 ?, u24 data offset, u16 data length
              (offsets are relative to the start of the character map)
          glyph data: 0x03 + run-length coded 3-bit alpha, row-major, width x height pixels
Pure Python, no dependencies (used by the build scripts and by the tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import struct

MAGIC = b"\x04\xff\x00\x0a"
ENCODING_UTF8 = 0x18
VERSION = 6
HEADER_SIZE = 0x2C
ALPHA_MAX = 7
LARGE_FONT_GLYPHS = 4096
ENCODING_SUFFIX = b"utf-8"


@dataclass
class Glyph:
    codepoint: int
    width: int
    data: bytes  # encoded, including the leading 0x03
    x_offset: int = 0
    unknown: int = 0

    def pixels(self, height: int) -> list[int]:
        return decode(self.data, self.width * height)


@dataclass
class ZiFont:
    name: str
    height: int
    glyphs: dict[int, Glyph] = field(default_factory=dict)

    @property
    def codepoints(self) -> set[int]:
        return set(self.glyphs)

    def to_bytes(self) -> bytes:
        # Nextion stores "<font name><encoding>" and the name length at 0x20; Nextion Editor
        # derives the encoding it shows from that suffix (a missing "utf-8" shows as garbage).
        name = self.name.encode("ascii") + ENCODING_SUFFIX
        if len(name) > 255:
            raise ValueError("font name too long")
        glyphs = [self.glyphs[cp] for cp in sorted(self.glyphs)]
        if any(not 0 <= g.codepoint <= 0xFFFF for g in glyphs):
            raise ValueError("Nextion fonts only support 16-bit code points")
        table = bytearray()
        data = bytearray()
        offset = 10 * len(glyphs)
        for g in glyphs:
            if not 0 < g.width <= 255 or len(g.data) > 0xFFFF:
                raise ValueError(f"glyph {g.codepoint:#x} too large")
            table += struct.pack("<HBBB", g.codepoint, g.width, g.x_offset, g.unknown)
            table += (offset + len(data)).to_bytes(3, "little") + struct.pack("<H", len(g.data))
            data += g.data
        body = name + bytes(table) + bytes(data)
        if offset + len(data) >= 1 << 24:
            raise ValueError("font larger than 16 MiB")
        header = bytearray(HEADER_SIZE)
        header[0:4] = MAGIC
        header[4] = ENCODING_UTF8
        header[5] = 0x02  # same as Nextion Editor's UTF-8 fonts
        header[6] = 0  # variable width
        header[7] = self.height
        header[8:12] = b"\xff\xff\x00\xff"
        struct.pack_into("<I", header, 0x0C, len(glyphs))
        header[0x10] = VERSION
        header[0x11] = len(name)
        struct.pack_into("<I", header, 0x14, len(body))
        struct.pack_into("<I", header, 0x18, HEADER_SIZE)
        header[0x1C:0x20] = b"\xff\x00\x01\x01"
        # 0x20: length of the font name without the encoding suffix.
        header[0x20] = len(name) - len(ENCODING_SUFFIX)
        # 0x24: the glyph count for small fonts, 0x10000 for the large icon fonts (observed:
        # 3 -> 3, 2248 -> 2248, 7120 -> 0x10000). Threshold between those is not known.
        struct.pack_into("<I", header, 0x24, 0x10000 if len(glyphs) > LARGE_FONT_GLYPHS else len(glyphs))
        return bytes(header) + body

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ZiFont":
        if raw[:3] != MAGIC[:3] or len(raw) < HEADER_SIZE:
            raise ValueError("not a .zi font")
        count = struct.unpack_from("<I", raw, 0x0C)[0]
        name_len = raw[0x11]
        height = raw[7]
        base = HEADER_SIZE + name_len
        full = raw[HEADER_SIZE:base]
        if not full.endswith(ENCODING_SUFFIX) or raw[0x20] != name_len - len(ENCODING_SUFFIX):
            raise ValueError("only UTF-8 fonts are supported")
        font = cls(full[:raw[0x20]].decode("ascii", "replace"), height)
        for i in range(count):
            pos = base + 10 * i
            cp, width, x_offset, unknown = struct.unpack_from("<HBBB", raw, pos)
            offset = int.from_bytes(raw[pos + 5:pos + 8], "little")
            length = struct.unpack_from("<H", raw, pos + 8)[0]
            font.glyphs[cp] = Glyph(cp, width, bytes(raw[base + offset:base + offset + length]), x_offset, unknown)
        return font

    @classmethod
    def load(cls, path) -> "ZiFont":
        with open(path, "rb") as file:
            return cls.from_bytes(file.read())

    def save(self, path) -> int:
        raw = self.to_bytes()
        with open(path, "wb") as file:
            file.write(raw)
        return len(raw)


def decode(data: bytes, expected: int | None = None) -> list[int]:
    """Glyph bytes (with the 0x03 prefix) -> list of alpha values 0..7."""
    if not data or data[0] != 0x03:
        raise ValueError("only 3-bit anti-aliased glyphs (0x03) are supported")
    px: list[int] = []
    for byte in data[1:]:
        mode, value = byte >> 6, byte & 0x3F
        if mode == 0:  # run of transparent (bit 5 = 0) or opaque (bit 5 = 1) pixels
            px += [ALPHA_MAX if value & 0x20 else 0] * (value & 0x1F)
        elif mode == 1:  # n transparent, then 1 or 2 opaque
            px += [0] * (value & 0x1F) + [ALPHA_MAX] * (2 if value & 0x20 else 1)
        elif mode == 2:  # up to 7 transparent, then one alpha pixel
            px += [0] * (value >> 3) + [value & 7]
        else:  # two alpha pixels
            px += [value >> 3, value & 7]
    if expected is not None:
        if len(px) < expected:
            raise ValueError(f"glyph decodes to {len(px)} pixels, expected {expected}")
        px = px[:expected]
    return px


def encode(px: list[int]) -> bytes:
    """Alpha values 0..7 -> glyph bytes, using the same choices as Nextion Editor."""
    out = bytearray([0x03])
    i, n = 0, len(px)

    def run(start: int, value: int) -> int:
        j = start
        while j < n and px[j] == value:
            j += 1
        return j - start

    while i < n:
        p = px[i]
        if p == 0:
            t = run(i, 0)
            if t >= 31 or i + t >= n:
                k = min(t, 31)
                out.append(k)
                i += k
                continue
            q = px[i + t]
            if q == ALPHA_MAX:
                o = run(i + t, ALPHA_MAX)
                out.append((0x60 if o >= 2 else 0x40) | t)
                i += t + min(o, 2)
                continue
            if t <= 7:
                out.append(0x80 | (t << 3) | q)
                i += t + 1
                continue
            out.append(t)
            i += t
            continue
        if p == ALPHA_MAX:
            o = run(i, ALPHA_MAX)
            if o >= 2:
                k = min(o, 31)
                out.append(0x20 | k)
                i += k
                continue
        q = px[i + 1] if i + 1 < n else 0
        out.append(0xC0 | (p << 3) | q)
        i += 2
    return bytes(out)
