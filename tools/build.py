# -*- coding: utf-8 -*-
"""Сборка русской версии из английского JAR.

Запуск: python tools/build.py [путь к Heroes Lore_240_320_EN.jar]
Без аргумента JAR ищется в папке game/ проекта и рядом с проектом.
"""
import glob
import hashlib
import os
import re
import sys
import zipfile

from build_font import build as build_font, read_glyphs
from hl_format import load_lang, save_lang
from patch_az import patch
from text_format import read_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JAR = os.path.join(ROOT, "build", "Heroes_Lore_RU.jar")
LANG = "lang/language.fr-FR"
ALLOWED_LATIN = set(chr(c) for c in range(32, 127))
# Английская версия 2.0.7, 240x320 (multiscreen): патч az.class рассчитан на нее
BASE_SHA1 = "a0f63b67fc287d5bc4ac8dacf36214ed940e3add"


def sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def find_base_jar(argv):
    if argv:
        candidates = [argv[0]]
    else:
        candidates = []
        for folder in (os.path.join(ROOT, "game"), os.path.dirname(ROOT)):
            candidates += sorted(glob.glob(os.path.join(folder, "*.jar")))
    for path in candidates:
        if os.path.isfile(path) and sha1(path) == BASE_SHA1:
            return path
    if argv:
        raise SystemExit("%s: не тот JAR (нужна английская версия 2.0.7 240x320, SHA-1 %s)"
                         % (argv[0], BASE_SHA1))
    raise SystemExit("Не найден английский JAR игры. Положите его в папку game/ "
                     "или укажите путь: python tools/build.py путь/к/игре.jar")


def check(strings, english, charset):
    problems = 0
    for i, (ru, en) in enumerate(zip(strings, english)):
        bad = sorted({c for c in ru if c not in charset and c != "\n"})
        if bad:
            print("  строка %d: нет в шрифте: %s" % (i, " ".join(bad)))
            problems += 1
        if re.match(r"[|$]*", ru).group(0) != re.match(r"[|$]*", en).group(0):
            print("  строка %d: другой префикс диалога (| или $)" % i)
            problems += 1
    return problems


def manifest(data):
    text = data.decode("latin-1")
    text = re.sub(r"(?m)^MIDlet-Name: .*$", "MIDlet-Name: Heroes Lore RU\r", text)
    return text.encode("latin-1")


def main(argv):
    base = zipfile.ZipFile(find_base_jar(argv))
    english = load_lang(base.read(LANG))
    items = read_text(os.path.join(ROOT, "text", "ru.txt"))
    strings = list(english)
    missing = [i for i in range(len(english)) if i not in items]
    for i, text in items.items():
        if i >= len(strings):
            raise ValueError("номер строки вне диапазона: %d" % i)
        strings[i] = text
    if missing:
        print("без перевода (останется английский): %d" % len(missing))

    glyphs = read_glyphs(os.path.join(ROOT, "font", "small_cyr.txt"), 8)
    problems = check(strings, english, ALLOWED_LATIN | set(glyphs))
    if problems:
        print("проблем в тексте: %d" % problems)

    replaced = {
        "az.class": patch(base.read("az.class")),
        LANG: save_lang(strings),
        "META-INF/MANIFEST.MF": manifest(base.read("META-INF/MANIFEST.MF")),
    }
    for name in ("small", "big"):
        mf = build_font(base.read("fonts/%s.mf" % name),
                        os.path.join(ROOT, "font", "%s_cyr.txt" % name))[0]
        replaced["fonts/%s.mf" % name] = mf
    images = os.path.join(ROOT, "images")
    for file_name in os.listdir(images):
        with open(os.path.join(images, file_name), "rb") as f:
            replaced["fr-FR/" + file_name] = f.read()

    os.makedirs(os.path.dirname(OUT_JAR), exist_ok=True)
    tmp = OUT_JAR + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for info in base.infolist():
            if info.filename.endswith("Thumbs.db"):
                continue
            if info.is_dir():
                continue
            # даты из оригинала, чтобы одинаковый вход давал одинаковый JAR
            entry = zipfile.ZipInfo(info.filename, info.date_time)
            entry.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(entry, replaced.get(info.filename, base.read(info.filename)))
    try:
        os.replace(tmp, OUT_JAR)
    except PermissionError:
        print("JAR занят: закройте эмулятор и запустите сборку снова")
        return 1
    print("готово: %s (%d байт)" % (OUT_JAR, os.path.getsize(OUT_JAR)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
