from __future__ import annotations

"""استخراج تمام نام‌های خودرویی که یک کانال/گروه مشخص تا الان پست کرده،
از روی داده‌های همین دیتابیس محلی (چیزی که collector قبلاً جمع کرده) —
نیازی به اتصال زنده‌ی جدید به تلگرام نیست.

اجرا (از ریشه‌ی پروژه):

    $env:PYTHONPATH="src"
    py -m telegramonline.export_vehicle_names BAZARBOZORGEKHODROIRAN

خروجی: data/vehicle_names_<username>.txt — هر خط یکی از خط‌های واقعی که
پارسر به‌عنوان «نام خودرو» احتمالی در نظر گرفته (چه شناخته‌شده چه نامشخص)،
همراه با تعداد تکرار و یک نمونه قیمت، تا بشه دید کدوم مدل‌ها هنوز الگو
ندارن یا الگوشون اسم عمومی/اشتباه برمی‌گردونه.

نکته: این فقط پیام‌های «امروز و دیروز» را می‌بیند (چون فقط همین دو روز در
دیتابیس نگه داشته می‌شود). برای یک بازه‌ی طولانی‌تر (مثلاً یک هفته)، باید
از discover_vehicles.py با اتصال زنده به تلگرام استفاده کرد.
"""

import argparse
import sys
from collections import Counter

from telegramonline.config import Settings
from telegramonline.storage import _clean_username, connect


def export(username: str) -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    clean = _clean_username(username)

    rows = conn.execute(
        """
        SELECT raw_text, vehicle_key, vehicle_name, price_million
        FROM ads
        WHERE channel_username = ?
        ORDER BY id
        """,
        (clean,),
    ).fetchall()

    if not rows:
        print(f"هیچ آگهی‌ای از «{clean}» در دیتابیس محلی پیدا نشد. مطمئن شو که این کانال/گروه join شده و مدتی از آن جمع‌آوری شده.")
        return

    # اسم واقعی خودرو معمولاً یکی از خط‌های اول متنه؛ چون فرمت پیام‌ها فرق
    # می‌کنه، ساده‌ترین و بی‌خطاترین کار اینه که چند خط اول هر آگهی رو
    # به‌عنوان «کاندید نام» نشون بدیم، در کنار چیزی که پارسر الان تشخیص داده.
    name_counter: Counter[str] = Counter()
    unknown_samples: list[str] = []
    known_but_maybe_wrong: dict[str, Counter[str]] = {}

    for row in rows:
        lines = [ln.strip() for ln in row["raw_text"].splitlines() if ln.strip()]
        first_lines = " | ".join(lines[:3]) if lines else "(متن خالی)"

        if row["vehicle_key"] is None:
            unknown_samples.append(first_lines)
        else:
            name_counter[row["vehicle_key"]] += 1
            known_but_maybe_wrong.setdefault(row["vehicle_key"], Counter())[first_lines] += 1

    out_path = settings.database_path.parent / f"vehicle_names_{clean}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"=== خلاصه‌ی «{clean}» — {len(rows)} آگهی کل ===\n\n")

        f.write(f"--- {len(unknown_samples)} آگهی بدون vehicle_key (نامشخص) ---\n")
        f.write("این‌ها قطعاً نیاز به الگوی جدید دارند:\n\n")
        for sample, count in Counter(unknown_samples).most_common():
            f.write(f"  [{count}x] {sample}\n")

        f.write(f"\n\n--- {len(name_counter)} مدل شناخته‌شده (vehicle_key) ---\n")
        f.write("برای هر کدوم، متن‌های واقعی که به این کلید مپ شدن رو ببین؛\n")
        f.write("اگه دیدی چند تا متن خیلی متفاوت به یه کلید عمومی مپ شدن،\n")
        f.write("یعنی احتمالاً باید الگوی دقیق‌تری براش اضافه بشه.\n\n")
        for key, count in name_counter.most_common():
            f.write(f"\n[{key}] — {count} آگهی\n")
            for sample, sample_count in known_but_maybe_wrong[key].most_common(10):
                f.write(f"    [{sample_count}x] {sample}\n")

    print(f"✅ نوشته شد: {out_path}")
    print(f"   {len(rows)} آگهی کل | {len(unknown_samples)} بدون مدل شناخته‌شده | {len(name_counter)} مدل شناخته‌شده")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="یوزرنیم کانال/گروه (با یا بدون @ یا لینک کامل)")
    args = parser.parse_args()
    export(args.username)


if __name__ == "__main__":
    main()
