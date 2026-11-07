# -*- coding: utf-8 -*-
"""Форматы Heroes Lore: языковой файл, шрифт .mf, PNG (без внешних библиотек)."""
import struct
import zlib

N_BASE = 1065            # значение, подставляемое вместо 95 в az.class
N_SLOTS = N_BASE + 9     # всего координат в .mf (хватает до U+0451 'ё')
CHAR_LIMIT = 0x452       # значение, подставляемое вместо 256 в az.class
ORIG_SLOTS = 104


def java_utf(text):
    """Modified UTF-8, как у DataInputStream.readUTF."""
    out = bytearray()
    for ch in text:
        c = ord(ch)
        if 1 <= c <= 0x7F:
            out.append(c)
        elif c <= 0x7FF:
            out += bytes((0xC0 | c >> 6, 0x80 | c & 0x3F))
        else:
            out += bytes((0xE0 | c >> 12, 0x80 | c >> 6 & 0x3F, 0x80 | c & 0x3F))
    if len(out) > 65533:
        raise ValueError("слишком длинная строка")
    return bytes(out)


def load_lang(data):
    count = (struct.unpack(">I", data[4:8])[0] + 4) // 4
    strings = []
    for i in range(count):
        rel = struct.unpack(">I", data[4 + 4 * i:8 + 4 * i])[0]
        pos = 8 + 4 * i + rel
        size = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        strings.append(data[pos + 4:pos + 4 + size].decode("utf-8"))
    return strings


def save_lang(strings):
    table = bytearray()
    body = bytearray()
    start = 4 * len(strings)
    for i, text in enumerate(strings):
        raw = java_utf(text)
        table += struct.pack(">I", start + len(body) - 4 * i - 4)
        body += struct.pack(">HH", len(raw) + 2, len(raw)) + raw
    return struct.pack(">I", len(table) + len(body)) + bytes(table) + bytes(body)


def read_png(b):
    i = 8
    idat = b""
    pal = []
    while i < len(b):
        size = struct.unpack(">I", b[i:i + 4])[0]
        kind = b[i + 4:i + 8]
        chunk = b[i + 8:i + 8 + size]
        i += 12 + size
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", chunk[:10])
        elif kind == b"PLTE":
            pal = [tuple(chunk[j:j + 3]) for j in range(0, size, 3)]
        elif kind == b"IDAT":
            idat += chunk
    if ctype != 3:
        raise ValueError("нужен PNG с палитрой")
    raw = zlib.decompress(idat)
    stride = (w * depth + 7) // 8
    rows = []
    prev = [0] * stride
    p = 0
    for _ in range(h):
        f = raw[p]
        line = list(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for x in range(stride):
            a = line[x - 1] if x else 0
            up = prev[x]
            c = prev[x - 1] if x else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + up) & 255
            elif f == 3:
                line[x] = (line[x] + (a + up) // 2) & 255
            elif f == 4:
                t = a + up - c
                pa, pb, pc = abs(t - a), abs(t - up), abs(t - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else up if pb <= pc else c)) & 255
        prev = line
        rows.append([(line[x * depth // 8] >> (8 - depth - x * depth % 8)) & ((1 << depth) - 1)
                     for x in range(w)])
    return w, h, rows, pal


def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def write_png(rows, palette):
    """PLTE обязан идти сразу за IHDR: игра правит палитру по смещению 33."""
    h = len(rows)
    w = len(rows[0])
    raw = b"".join(b"\0" + bytes(r) for r in rows)
    out = b"\x89PNG\r\n\x1a\n"
    out += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
    out += _chunk(b"PLTE", b"".join(bytes(c) for c in palette))
    out += _chunk(b"tRNS", b"\0")
    out += _chunk(b"IDAT", zlib.compress(raw, 9))
    out += _chunk(b"IEND", b"")
    return out


class Font:
    def __init__(self, data):
        self.height_raw, self.d, self.e, self.f = data[4], data[5], data[6], data[7]
        self.has_c = self.height_raw > 100
        self.height = self.height_raw - 100 if self.has_c else self.height_raw
        n = 95 + (9 if self.has_c else 0)
        self.coords = list(struct.unpack(">%dH" % n, data[8:8 + 2 * n]))
        p = 8 + 2 * n
        size, self.n8, self.n11, self.n14 = struct.unpack(">4H", data[p:p + 8])
        self.png = data[p + 8:p + 8 + size]

    def pack(self, coords, png):
        if len(coords) != N_SLOTS:
            raise ValueError("нужно %d координат" % N_SLOTS)
        out = bytes(4) + bytes((self.height_raw, self.d, self.e, self.f))
        out += struct.pack(">%dH" % len(coords), *coords)
        out += struct.pack(">4H", len(png), self.n8, self.n11, self.n14)
        return out + png
