from __future__ import annotations

"""دوباره‌پردازش آگهی‌های موجود با آخرین نسخه‌ی پارسر.

وقتی پارسر (parser.py) اصلاح یا تکمیل می‌شود، آگهی‌هایی که *قبلاً* ذخیره
شده‌اند خودکار به‌روز نمی‌شوند — چون پردازش فقط روی پیام‌های تازه‌ی ورودی
انجام می‌شود. این اسکریپت raw_text هر آگهیِ ذخیره‌شده را با پارسر فعلی
دوباره پردازش می‌کند و ستون‌های vehicle_key/vehicle_name/trim/price_million/
year/month/color/mileage_km/phone/status/delivery/confidence را در همان
ردیف به‌روز می‌کند (id و source_message_id و raw_text دست‌نخورده می‌مانند).

اجرا (از ریشه‌ی پروژه):

    $env:PYTHONPATH="src"
    py -m telegramonline.reparse_today

پیش‌فرض فقط آگهی‌های «امروز» را دوباره پردازش می‌کند. برای همه‌ی آگهی‌های
موجود (امروز + دیروز، چون فقط همین دو روز نگه داشته می‌شوند):

    py -m telegramonline.reparse_today --all
"""

import argparse

from telegramonline.config import Settings
from telegramonline.parser import parse_message
from telegramonline.storage import connect, today_day_key, yesterday_day_key


def reparse(db_path: str, only_today: bool = True) -> None:
    conn = connect(db_path)
    if only_today:
        rows = conn.execute(
            "SELECT id, raw_text, message_date FROM ads WHERE day_key = ?",
            (today_day_key(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, raw_text, message_date FROM ads WHERE day_key IN (?, ?)",
            (today_day_key(), yesterday_day_key()),
        ).fetchall()

    updated = 0
    fixed_unknown = 0
    for row in rows:
        ad = parse_message(str(row["id"]), row["raw_text"], row["message_date"])
        was_unknown = True  # نمی‌دونیم قبلش چی بوده، فقط بعدش رو چک می‌کنیم
        conn.execute(
            """
            UPDATE ads SET
                vehicle_key = ?,
                vehicle_name = ?,
                trim = ?,
                price_million = ?,
                year = ?,
                month = ?,
                color = ?,
                mileage_km = ?,
                phone = ?,
                status = ?,
                delivery = ?,
                confidence = ?
            WHERE id = ?
            """,
            (
                ad.vehicle_key,
                ad.vehicle_name,
                ad.trim,
                ad.price_million,
                ad.year,
                ad.month,
                ad.color,
                ad.mileage_km,
                ad.phone,
                ad.status,
                ad.delivery,
                ad.confidence,
                row["id"],
            ),
        )
        updated += 1
        if ad.vehicle_key:
            fixed_unknown += 1
    conn.commit()
    print(f"✅ {updated} آگهی دوباره پردازش شد؛ {fixed_unknown} تای آن‌ها الان vehicle_key دارند.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="امروز + دیروز (به‌جای فقط امروز)")
    args = parser.parse_args()
    settings = Settings.from_env()
    reparse(str(settings.database_path), only_today=not args.all)


if __name__ == "__main__":
    main()
