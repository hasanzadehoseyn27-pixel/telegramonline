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
    ("tara_automatic_v4_tu5", [["تارا"], ["v4"]], []),
    ("tara_automatic_v4_tu5", [["تارا"], ["اتومات"]], []),
    ("tara_automatic_v4_tu5", [["تارا"], ["وی"], ["4", "چهار"]], []),

    # ── تارا V1 دنده ──
    ("tara_gear_v1", [["تارا"], ["v1"]], []),
    ("tara_gear_v1", [["تارا"], ["دنده"]], []),
    ("tara_gear_v1", [["تارا"], ["وی"], ["1", "یک"]], []),

    # ── رانا پانا (بالاترین اولویت — اگه پانا داشت، همینه) ──
    ("rana_pana", [["رانا"], ["پانا", "پاناروما", "پانوراما"]], []),

    # ── رانا کاسه (فقط اگه پانا نداشت) ──
    ("rana_kase", [["رانا"], ["کاسه"]], ["پانا", "پاناروما", "پانوراما"]),

    # ── رانا دیسک (فقط اگه پانا نداشت) ──
    ("rana_disk", [["رانا"], ["دیسک"]], ["پانا", "پاناروما", "پانوراما"]),

    # ── رانا معمولی (catch-all — هر رانای دیگه‌ای که پانا/کاسه/دیسک نداشت) ──
    ("rana_normal", [["رانا"], ["معمولی", "1390", "1391", "1392", "1393", "1394", "1395", "1396", "1397", "1398", "1399"]], ["پانا", "پاناروما", "پانوراما", "کاسه", "دیسک"]),

    # ── سورن XU7P سیمی/برقی ──
    ("soren_xu7p_wired", [["سورن"], ["xu7p"], ["سیمی"]], ["برقی"]),
    ("soren_xu7p_electric", [["سورن"], ["xu7p"], ["برقی"]], ["سیمی"]),

    # ── سورن TU5 ──
    ("soren_tu5", [["سورن"], ["tu5"]], []),

    # ── سورن دوگانه (۴ نوع مخزن/سوخت‌رسانی) ──
    ("soren_dogane_big_wired", [["سورن"], ["دوگانه"], ["بزرگ"], ["سیمی"]], []),
    ("soren_dogane_big_electric", [["سورن"], ["دوگانه"], ["بزرگ"], ["برقی"]], []),
    ("soren_dogane_small_wired", [["سورن"], ["دوگانه"], ["کوچک", "کوچیک"], ["سیمی"]], []),
    ("soren_dogane_small_electric", [["سورن"], ["دوگانه"], ["کوچک", "کوچیک"], ["برقی"]], []),
]


def match_zero_whitelist(vehicle_name: str | None, trim: str | None, raw_text: str | None = None) -> str | None:
    """اگه اسم/تریم/متنِ خامِ پیام با یکی از مدل‌های «صفر»ِ لیست سفید match
    بشه، کلید کانونیکش رو برمی‌گردونه؛ وگرنه None.

    ⚠️ raw_text رو هم چک می‌کنیم — چون خیلی از فروشنده‌ها کلمه‌ی تشخیص‌دهنده
    (مثل «کاسه»/«دیسک») رو تو خط جدا می‌نویسن، نه تو همون بخش کوتاهی که
    پارسر به‌عنوان «اسم خودرو» جدا می‌کنه. با توجه به اینکه لیست‌سفید الان
    خیلی کوچیکه (فقط تارا + رانا)، ریسک تداخل کاذب هم پایینه.
    """

    # پیام‌های خیلی طولانی معمولاً لیست‌قیمتِ ده‌ها ماشین مختلفن — چک کردن
    # raw_text توشون خطرناکه (مثلاً «پانا» می‌تونه برای یه ماشین دیگه باشه،
    # نه «رانا»یی که تو همون پیام اومده). فقط پیام‌های کوتاه (یه آگهی تکی)
    # از raw_text استفاده می‌کنن.
    safe_raw_text = raw_text if raw_text and len(raw_text) <= 400 else None
    combined = " ".join(x for x in [vehicle_name, trim, safe_raw_text] if x)
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
