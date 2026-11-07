# -*- coding: utf-8 -*-
"""Добавляет глифы из font/*_cyr.txt к оригинальному шрифту .mf."""
from hl_format import Font, N_SLOTS, ORIG_SLOTS, read_png, write_png

PIXELS = {".": 0, "#": 1, "o": 2}


def read_glyphs(path, height):
    glyphs = {}
    current = None
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.rstrip("\r\n")
            if line.startswith("#") and current is None:
                continue
            if line.startswith("== "):
                current = line[3:].strip()
                if len(current) != 1:
                    raise ValueError("%s:%d: нужен один символ" % (path, number))
                glyphs[current] = []
            elif line.strip() and current is not None:
                glyphs[current].append(line)
            elif not line.strip():
                current = None
    for ch, rows in glyphs.items():
        if len(rows) != height or len({len(r) for r in rows}) != 1:
            raise ValueError("%s: глиф %r должен быть %d строк равной длины" % (path, ch, height))
    return glyphs


def build(original_mf, glyph_path):
    font = Font(original_mf)
    width, height, rows, palette = read_png(font.png)
    glyphs = read_glyphs(glyph_path, height)
    # строчной кириллицы может не быть (крупный шрифт): берём копию заглавной
    for lower in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя":
        if lower not in glyphs and lower.upper() in glyphs:
            glyphs[lower] = glyphs[lower.upper()]

    coords = font.coords + [None] * (N_SLOTS - len(font.coords))
    sheet = [list(r) for r in rows]
    x = width
    for ch in sorted(glyphs):
        slot = ord(ch) - 33
        if slot < ORIG_SLOTS or slot + 1 >= N_SLOTS:
            raise ValueError("символ %r нельзя добавить в шрифт" % ch)
        coords[slot] = x
        for y in range(height):
            sheet[y].extend(PIXELS[c] for c in glyphs[ch][y])
        x += len(glyphs[ch][0])
        coords[slot + 1] = x
    last = width
    for i in range(ORIG_SLOTS, N_SLOTS):
        if coords[i] is None:
            coords[i] = last
        else:
            last = coords[i]
    png = write_png(sheet, palette)
    return font.pack(coords, png), sheet, palette
