from __future__ import annotations

import re

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"

TRANSLATION_TABLE = str.maketrans(
    {
        **{p: a for p, a in zip(PERSIAN_DIGITS, ASCII_DIGITS)},
        **{p: a for p, a in zip(ARABIC_DIGITS, ASCII_DIGITS)},
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "\u200c": " ",
        "\u200f": "",
        "\u200e": "",
        "\xa0": " ",
        "٬": ",",
        "٫": ".",
        "،": ",",
        "\\": "/",
    }
)


def normalize_text(text: str) -> str:
    text = text.translate(TRANSLATION_TABLE)
    text = re.sub(r"\s*([./,])\s*", r"\1", text)
    text = re.sub(r"(?<!\d)([1-9])\s+(\d{3})\s+000\s+000(?!\d)", r"\1/\2/000", text)
    text = re.sub(r"(?<!\d)([1-9])\s+(\d{3})(?!\d)", r"\1/\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(text)).strip()


def strip_number_separators(value: str) -> str:
    return re.sub(r"[^\d]", "", value)


def parse_number_token(token: str) -> int | None:
    token = normalize_text(token)
    digits = strip_number_separators(token)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None
