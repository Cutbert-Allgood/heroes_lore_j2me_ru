# -*- coding: utf-8 -*-
"""Текстовый файл перевода.

Формат text/ru.txt (UTF-8):
    #EN Dull two hands sword         <- оригинал для справки, игнорируется
    0<TAB>Затупленный двуручный меч  <- номер строки, TAB, перевод

В тексте: \\n - перевод строки, ; - тоже перевод строки (так устроена игра),
| и $ в начале и [Имя] - разметка диалога, менять только сам текст.
"""

REPLACE = {
    "—": "-", "–": "-", "…": "...", "“": '"', "”": '"',
    "‘": "'", "’": "'", " ": " ", "№": "N", "\t": " ",
}


def escape(text):
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def unescape(text):
    out = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            out.append("\n" if nxt == "n" else nxt)
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def normalize(text):
    for old, new in REPLACE.items():
        text = text.replace(old, new)
    return text


def read_text(path):
    items = {}
    with open(path, encoding="utf-8-sig") as f:
        for number, line in enumerate(f, 1):
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            head, sep, body = line.partition("\t")
            if not sep or not head.isdigit():
                raise ValueError("%s:%d: ожидается 'номер<TAB>текст': %r" % (path, number, line[:60]))
            items[int(head)] = normalize(unescape(body))
    return items


def write_text(path, english, russian):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Heroes Lore: перевод. Строка: номер, TAB, текст. Кодировка UTF-8.\n")
        f.write("# Строки #EN - оригинал для справки. Собрать игру: python tools/build.py\n\n")
        for i, (en, ru) in enumerate(zip(english, russian)):
            if en or ru:
                f.write("#EN %s\n" % escape(en))
            f.write("%d\t%s\n" % (i, escape(ru)))
