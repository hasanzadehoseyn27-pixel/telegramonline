# -*- coding: utf-8 -*-
"""لیست سفید مدل‌های خودروی صفر که فقط اگه یه پیام باهاشون match بشه، یه
vehicle_key واقعی (برای «کمترین قیمت‌ها» و جدا شدن از «متفرقه») می‌گیره.

⚠️ این لیست عمداً از صفر شروع شده (به‌درخواست کارفرما، ۳۱ آگوست ۲۰۲۶) —
قراره مدل‌ها یکی‌یکی و با دقت زیاد، با قوانین دقیقی که کارفرما خودش می‌ده،
دوباره اضافه بشن. فعلاً فقط ۳ مدل تارا هست.

⚠️ این لیست کاملاً جداست از vehicle_key داخلیِ خودِ telegramonline (که برای
فیچرهای خودِ سایت telegramonline استفاده می‌شه و دست‌نخورده می‌مونه). این
فقط برای بریج به CarX (کیوان‌خودرو) استفاده می‌شه.

هر آیتم: (کلید_کانونیک، [[گروه۱_معادل‌ها], [گروه۲_معادل‌ها], ...], [کلمات_ممنوع])
باید حداقل یکی از کلمات هر گروه، تو متن پیام باشه (AND بین گروه‌ها،
OR داخل خود گروه). چندتا ردیف می‌تونن کلید یکسان داشته باشن — یعنی هرکدوم
یه الگوی مستقل و جایگزین برای تشخیص همون مدلن (OR بین کل ردیف‌ها).

⚠️ ترتیب مهمه: مدل‌های خاص‌تر باید قبل از مدل‌های عمومی‌ترِ همون خانواده
بیان، چون اولین match برنده‌ست.
"""

from __future__ import annotations

import re

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ASCII_DIGITS = "0123456789"
_DIGIT_MAP = str.maketrans(_PERSIAN_DIGITS, _ASCII_DIGITS)


def _normalize(text: str) -> str:
    text = text or ""
    text = text.translate(_DIGIT_MAP)
    text = text.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b(بدون|بی)\s+\S+", " ", text)
    return text


_WHITELIST: list[tuple[str, list[list[str]], list[str]]] = [
    # ── تارا V4 EF7 توربو (باید قبل از V4 اتومات چک بشه، چون همپوشانی داره) ──
    ("tara_automatic_v4_ef7", [["تارا"], ["توربو"]], []),
    ("tara_automatic_v4_ef7", [["تارا"], ["ef7", "ای اف سون", "ای اف7", "افسون", "ای اف هفت"]], []),

    # ── تارا V4 اتومات TU5 ──
    ("tara_automatic_v4_tu5", [["v4"]], []),
    ("tara_automatic_v4_tu5", [["تارا"], ["اتومات"]], []),
    ("tara_automatic_v4_tu5", [["تارا"], ["وی"], ["4", "چهار"]], []),

    # ── تارا V1 دنده ──
    ("tara_gear_v1", [["v1"]], []),
    ("tara_gear_v1", [["تارا"], ["دنده"]], []),
    ("tara_gear_v1", [["تارا"], ["وی"], ["1", "یک"]], []),
]


def match_zero_whitelist(vehicle_name: str | None, trim: str | None, raw_text: str | None = None) -> str | None:
    """اگه اسم/تریمِ از قبل تشخیص‌داده‌شده با یکی از مدل‌های «صفر»ِ لیست
    سفید match بشه، کلید کانونیکش رو برمی‌گردونه؛ وگرنه None.
    """

    combined = " ".join(x for x in [vehicle_name, trim] if x)
    if not combined.strip():
        return None

    normalized = _normalize(combined)

    for key, groups, exclude in _WHITELIST:
        if exclude and any(
            re.search(r"\b" + re.escape(_normalize(ex)) + r"\b", normalized)
            for ex in exclude
        ):
            continue
        matched_all = True
        for group in groups:
            if not any(
                re.search(r"\b" + re.escape(_normalize(alt)) + r"\b", normalized)
                for alt in group
            ):
                matched_all = False
                break
        if matched_all:
            return key

    return None
