# -*- coding: utf-8 -*-
"""لیست سفید مدل‌های خودروی صفر که فقط اگه یه پیام باهاشون match بشه، یه
vehicle_key واقعی (برای «کمترین قیمت‌ها» و جدا شدن از «متفرقه») می‌گیره.

⚠️ این لیست کاملاً جداست از vehicle_key داخلیِ خودِ telegramonline (که برای
فیچرهای خودِ سایت telegramonline مثل SpecialAds/Watched Vehicles استفاده
می‌شه و دست‌نخورده می‌مونه). این فقط برای بریج به CarX (کیوان‌خودرو) استفاده
می‌شه.

هر آیتم: (کلید_کانونیک، [[گروه۱_معادل‌ها], [گروه۲_معادل‌ها], ...])
باید حداقل یکی از کلمات هر گروه، تو متن پیام باشه (AND بین گروه‌ها،
OR داخل خود گروه).

⚠️ چون این لیست دستی و بر اساس نمونه‌های واقعی تنظیم نشده، احتمالاً بعد از
دیدن آگهی‌های واقعی نیاز به تنظیم دقیق‌تر داره — این یه نسخه‌ی اولیه‌ست.
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
    # عبارت‌های منفی («بدون رینگ»، «بی سانروف») نباید باعث بشن کلمه‌ی بعدشون
    # به‌اشتباه به‌عنوان «وجود دارد» تشخیص داده بشه.
    text = re.sub(r"\b(بدون|بی)\s+\S+", " ", text)
    return text


# فرمت هر آیتم: (کلید, [[معادل‌های گروه۱], [معادل‌های گروه۲], ...])
_WHITELIST: list[tuple[str, list[list[str]]]] = [
    ("207_pana_ertegha_plus_gear_rim", [["207", "پانا"], ["ارتقا", "ارتقاء"], ["پلاس"], ["دنده"], ["رینگ"]]),
    ("207_pana_ertegha_plus_gear_ghalpagh", [["207", "پانا"], ["ارتقا", "ارتقاء"], ["پلاس"], ["دنده"], ["قالپاق"]]),
    ("samand_soren_plus_xu7p_electric", [["سمند"], ["سورن"], ["پلاس"], ["xu7p"], ["برقی"]]),
    ("samand_soren_plus_xu7p_wired", [["سمند"], ["سورن"], ["پلاس"], ["xu7p"], ["سیمی"]]),
    ("samand_soren_dogane_big_wired", [["سمند"], ["سورن"], ["دوگانه"], ["بزرگ"], ["سیمی"]]),
    ("samand_soren_dogane_big_electric", [["سمند"], ["سورن"], ["دوگانه"], ["بزرگ"], ["برقی"]]),
    ("samand_soren_dogane_small_wired", [["سمند"], ["سورن"], ["دوگانه"], ["کوچک", "کوچیک"], ["سیمی"]]),
    ("samand_soren_dogane_small_electric", [["سمند"], ["سورن"], ["دوگانه"], ["کوچک", "کوچیک"], ["برقی"]]),
    ("207_metal_roof_hydraulic", [["207"], ["سقف"], ["فلز"], ["هیدرولیک"]]),
    ("207_metal_roof_hydraulic_rear_disc", [["207"], ["سقف"], ["فلز"], ["هیدرولیک"], ["دیسک"]]),
    ("207_metal_roof_electric_full", [["207"], ["سقف"], ["فلز"], ["برقی"], ["فول"]]),
    ("207_metal_roof_automatic", [["207"], ["سقف"], ["فلز"], ["اتومات"]]),
    ("207_pana_ertegha_plus_automatic", [["207", "پانا"], ["ارتقا", "ارتقاء"], ["پلاس"], ["اتومات"]]),
    ("saina_s", [["ساینا"], ["اس", "s"]]),
    ("saina_s_dogane", [["ساینا"], ["اس", "s"], ["دوگانه"]]),
    ("quick_s", [["کوییک", "کوئیک"], ["اس", "s"]]),
    ("quick_rs", [["کوییک", "کوئیک"], ["rs", "آر اس"]]),
    ("quick_gxr_rim", [["کوییک", "کوئیک"], ["gxr"], ["رینگ"]]),
    ("quick_gxr_ghalpagh", [["کوییک", "کوئیک"], ["gxr"], ["قالپاق"]]),
    ("quick_gxrl", [["کوییک", "کوئیک"], ["gxrl"]]),
    ("quick_gx", [["کوییک", "کوئیک"], ["gx", "جی ایکس"]]),
    ("shahin_g_sunroof", [["شاهین"], ["دنده"], ["سانروف"]]),
    ("shahin_gear_no_sunroof", [["شاهین"], ["دنده"]]),
    ("shahin_automatic_cvt", [["شاهین"], ["اتومات"], ["cvt"]]),
    ("shahin_automatic_plus_tu5", [["شاهین"], ["اتومات"], ["پلاس"], ["tu5"]]),
    ("tara_gear_v1", [["تارا"], ["دنده"], ["v1"]]),
    ("tara_automatic_v4_tu5", [["تارا"], ["اتومات"], ["v4"], ["tu5"]]),
    ("tara_automatic_v4_ef7", [["تارا"], ["اتومات"], ["v4"], ["ef7"]]),
    ("207_tu3", [["207"], ["tu3"]]),
    ("respect_2_prime_new_bumper", [["ریسپکت", "رسپکت"], ["پرایم"], ["سپر"], ["جدید"]]),
    ("respect_2_prime_old_bumper", [["ریسپکت", "رسپکت"], ["پرایم"], ["سپر"], ["قدیم"]]),
    ("atlas_s_sunroof", [["اطلس"], ["اس", "s"], ["سانروف"]]),
    ("atlas_s_no_sunroof", [["اطلس"], ["اس", "s"]]),
    ("atlas_automatic", [["اطلس"], ["اتومات"]]),
    ("sahand_s", [["سهند"], ["اس", "s"]]),
    ("sahand_automatic", [["سهند"], ["اتوماتیک", "اتومات"]]),
    ("shahin_auto", [["شاهین"], ["اتو"]]),
    ("shahin_auto_plus", [["شاهین"], ["اتو"], ["پلاس"]]),
    ("pars_nova", [["پارس"], ["نوا"]]),
    ("citroen_c3", [["سیتروئن"], ["c3"]]),
    ("changan_cs55_montage", [["چانگان"], ["cs55"], ["مونتاژ"]]),
    ("changan_cs55_import", [["چانگان"], ["cs55"], ["واردات", "وارداتی"]]),
    ("changan_cs35_montage", [["چانگان"], ["cs35"], ["مونتاژ"]]),
    ("changan_cs35_import", [["چانگان"], ["cs35"], ["واردات", "وارداتی"]]),
    ("rira", [["ریرا"]]),
    ("haima_s5", [["هایما"], ["s5"]]),
    ("haima_s7", [["هایما"], ["s7"]]),
    ("haima_s8", [["هایما"], ["s8"]]),
    ("haima_7x", [["هایما"], ["7x"]]),
    ("eagle", [["ایگل"]]),
    ("jac_j4", [["جک"], ["j4"]]),
    ("jac_j7", [["جک"], ["j7"]]),
    ("jac_x5", [["جک"], ["x5"]]),
    ("jac_t9", [["جک"], ["t9"]]),
    ("beik", [["بک"]]),
    ("jac_sr3", [["جک"], ["sr3"]]),
    ("jac_sr6", [["جک"], ["sr6"]]),
    ("fidelity_elite_5", [["فید", "فیدلیتی"], ["الیت"], ["5", "پنج"]]),
    ("fidelity_elite_7", [["فید", "فیدلیتی"], ["الیت"], ["7", "هفت"]]),
    ("fidelity_prestige_white", [["فید", "فیدلیتی"], ["پرستیژ"], ["سفید"]]),
    ("fidelity_prestige_black", [["فید", "فیدلیتی"], ["پرستیژ"], ["مشکی", "مشک"]]),
    ("shoval", [["شوال"]]),
    ("dignity_prime", [["دیگنیتی"], ["پرایم"]]),
    ("dignity_prestige", [["دیگنیتی"], ["پرستیژ"]]),
    ("von_inroads", [["ون"], ["اینرودز"]]),
    ("x33", [["ایکس33", "x33", "ایکس۳۳"]]),
    ("x77", [["ایکس77", "x77", "ایکس۷۷"]]),
    ("arrizo6_gt", [["آریزو", "اریزو"], ["6", "۶"], ["gt"]]),
    ("arrizo8", [["آریزو", "اریزو"], ["8", "۸"]]),
    ("tiggo7", [["تیگو"], ["7", "۷"]]),
    ("tiggo8_promax", [["تیگو"], ["8", "۸"], ["پرومکس"]]),
    ("fx", [["اف ایکس", "fx"]]),
    ("x55", [["ایکس55", "x55", "ایکس۵۵"]]),
    ("beijing_u5", [["بیجینگ"], ["u5"]]),
    ("farda_511", [["فردا"], ["511"]]),
    ("farda_sx5", [["فردا"], ["sx5"]]),
    ("farda_t5", [["فردا"], ["t5"]]),
    ("changan_unity", [["چانگان"], ["یونیتی"]]),
    ("lamari_ima", [["لاماری"], ["ایما"]]),
    ("lamari_eco", [["لاماری"], ["اکو"]]),
    ("lucano_l7", [["لوکانو"], ["l7"]]),
    ("lucano_l8", [["لوکانو"], ["l8"]]),
    ("mazda3", [["مزدا"], ["3", "۳"]]),
    ("luna_electric", [["لونا"], ["برقی"]]),
    ("optima_k5", [["اپتیما"], ["k5"]]),
    ("camry_2l_china", [["کمری"], ["2", "۲"], ["چین"]]),
    ("honda_hrv", [["هوندا"], ["hrv"]]),
    ("freelander", [["فراتلندر"]]),
    ("sonata_hermes", [["سوناتا"], ["هرمس"]]),
    ("corolla_cross", [["کرولا"], ["کراس"]]),
    ("byd_song_plus", [["بی وای دی", "byd"], ["سانگ"], ["پلاس"]]),
    ("toyota_chr", [["تویوتا"], ["chr"]]),
    ("levin_1800", [["لوین"], ["1800", "۱۸۰۰"]]),
    ("terac", [["تیراک"]]),
    ("honda_ens1", [["هوندا"], ["ens1"]]),
    ("rav4_1diff", [["راوفور", "رافور"], ["تک دف"]]),
    ("rav4_2diff", [["راوفور", "رافور"], ["دو دف", "2دف", "۲دف"]]),
    ("nissan_altima", [["نیسان"], ["التیما"]]),
    ("qashqai", [["قشقایی"]]),
    ("mercedes_a180", [["بنز"], ["a180"]]),
    ("camry_china_tita", [["کمری"], ["چین"], ["تیتا", "تیتانیوم"]]),
    ("camry_japan", [["کمری"], ["ژاپن"]]),
    ("elantra", [["النترا"]]),
    ("pride_151_gx", [["پراید"], ["151", "۱۵۱"], ["gx"]]),
    ("arisan", [["آریسان", "اریسان"]]),
    ("nissan_dogane_ex", [["نیسان"], ["دوگانه"], ["ex"]]),
    ("nissan_tak_ex", [["نیسان"], ["تک"], ["ex"]]),
]


def match_zero_whitelist(vehicle_name: str | None, trim: str | None, raw_text: str | None) -> str | None:
    """اگه متن پیام با یکی از مدل‌های «صفر»ِ لیست سفید match بشه، کلید
    کانونیکش رو برمی‌گردونه؛ وگرنه None (یعنی باید برای CarX «متفرقه»
    حساب بشه، حتی اگه parser داخلی خودِ telegramonline یه vehicle_key
    عمومی برایش پیدا کرده باشه)."""

    combined = " ".join(x for x in [vehicle_name, trim, raw_text] if x)
    if not combined.strip():
        return None

    normalized = _normalize(combined)

    for key, groups in _WHITELIST:
        matched_all = True
        for group in groups:
            if not any(_normalize(alt) in normalized for alt in group):
                matched_all = False
                break
        if matched_all:
            return key

    return None
