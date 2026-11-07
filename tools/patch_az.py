# -*- coding: utf-8 -*-
"""Патч az.class: кириллица в шрифтах. Все правки той же длины, поэтому
смещения переходов и атрибуты StackMap остаются верными."""
import struct
import sys

from hl_format import CHAR_LIMIT, N_BASE

BIPUSH, SIPUSH, LDC = 0x10, 0x11, 0x12
NEVER = 0x7FFF


def parse_cp(d):
    count = struct.unpack(">H", d[8:10])[0]
    p = 10
    utf = {}
    i = 1
    while i < count:
        tag = d[p]
        if tag == 1:
            size = struct.unpack(">H", d[p + 1:p + 3])[0]
            utf[i] = bytes(d[p + 3:p + 3 + size])
            p += 3 + size
        elif tag in (3, 4, 9, 10, 11, 12):
            p += 5
        elif tag in (5, 6):
            p += 9
            i += 1
        elif tag in (7, 8):
            p += 3
        else:
            raise ValueError("тег %d" % tag)
        i += 1
    return count, p, utf


def skip_member(d, p):
    attrs = struct.unpack(">H", d[p + 6:p + 8])[0]
    p += 8
    for _ in range(attrs):
        p += 6 + struct.unpack(">I", d[p + 2:p + 6])[0]
    return p


def find_code(d, cp_end, utf, name, desc):
    p = cp_end + 6
    p += 2 + 2 * struct.unpack(">H", d[p:p + 2])[0]
    fields = struct.unpack(">H", d[p:p + 2])[0]
    p += 2
    for _ in range(fields):
        p = skip_member(d, p)
    methods = struct.unpack(">H", d[p:p + 2])[0]
    p += 2
    for _ in range(methods):
        n, ds = struct.unpack(">HH", d[p + 2:p + 6])
        if utf[n] == name and utf[ds] == desc:
            q = p + 8
            for _ in range(struct.unpack(">H", d[p + 6:p + 8])[0]):
                if utf[struct.unpack(">H", d[q:q + 2])[0]] == b"Code":
                    return q + 14
                q += 6 + struct.unpack(">I", d[q + 2:q + 6])[0]
        p = skip_member(d, p)
    raise ValueError("метод не найден: %r" % name)


def patch(src):
    d = bytearray(src)
    count, cp_end, utf = parse_cp(d)
    idx_n, idx_never = count, count + 1
    if idx_never > 255:
        raise ValueError("индекс константы не помещается в ldc")

    def put(code, off, old, new):
        if bytes(d[code + off:code + off + len(old)]) != bytes(old):
            raise ValueError("неожиданный байткод по смещению %d" % off)
        d[code + off:code + off + len(new)] = bytes(new)

    def sipush(v):
        return (SIPUSH, v >> 8, v & 255)

    load = find_code(d, cp_end, utf, b"a", b"(Ljava/io/InputStream;II)V")
    put(load, 89, (BIPUSH, 95), (LDC, idx_n))            # new short[95 + 9]
    put(load, 115, (BIPUSH, 95), (LDC, idx_n))           # цикл чтения координат

    width = find_code(d, cp_end, utf, b"a", b"(C)I")
    put(width, 17, sipush(256), sipush(CHAR_LIMIT))
    put(width, 23, sipush(192), sipush(NEVER))           # À..Þ -> строчные
    put(width, 54, (BIPUSH, 127), (LDC, idx_never))      # акценты -> латиница/точка

    draw = find_code(d, cp_end, utf, b"a", b"(Ljavax/microedition/lcdui/Graphics;[CIIIII)I")
    put(draw, 254, sipush(256), sipush(CHAR_LIMIT))
    put(draw, 263, sipush(192), sipush(NEVER))
    put(draw, 300, (BIPUSH, 127), (LDC, idx_never))

    extra = b"\x03" + struct.pack(">i", N_BASE) + b"\x03" + struct.pack(">i", NEVER)
    d[8:10] = struct.pack(">H", count + 2)
    d[cp_end:cp_end] = extra
    return bytes(d)


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        result = patch(f.read())
    with open(sys.argv[2], "wb") as f:
        f.write(result)
