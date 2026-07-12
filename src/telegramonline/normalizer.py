from __future__ import annotations

import re

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ASCII_DIGITS = "0123456789"

# حروف لاتینی که فروشنده‌ها گاهی به فارسی تلفظ‌شان را می‌نویسند، فقط وقتی
# بلافاصله قبل از یک عدد کد مدل بیاید (مثل «تی۹» یا «تی 9» به‌جای T9).
# محدود به حروفی که در کدهای رایج خودرو دیده می‌شود تا اشتباهی با کلمات
# معمولی فارسی قاطی نشود.
PERSIAN_LETTER_NAME_TO_LATIN = {
    "تی": "t",
    "دی": "d",
    "سی": "c",
    "جی": "g",
    "ایکس": "x",
    "ال": "l",
    "پی": "p",
    "بی": "b",
    "زد": "z",
}
_LETTER_CODE_RE = re.compile(
    "(" + "|".join(sorted(PERSIAN_LETTER_NAME_TO_LATIN, key=len, reverse=True)) + r")\s*(\d{1,3})\b"
)


def _replace_letter_code(match: re.Match[str]) -> str:
    return PERSIAN_LETTER_NAME_TO_LATIN[match.group(1)] + match.group(2)


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
    text = _LETTER_CODE_RE.sub(_replace_letter_code, text)
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