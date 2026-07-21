from __future__ import annotations

"""بک‌فیل یک‌باره‌ی آگهی‌های قیمت‌دار + خاصِ دیروز به سایت اصلی (CarX).

اجرا (از ریشه‌ی پروژه‌ی telegramonline):
    $env:PYTHONPATH="src"
    py -m telegramonline.push_yesterday_to_carx

قبلش باید توی .env این دوتا رو ست کرده باشی:
    CARX_API_URL=http://localhost:5138/api
    CARX_IMPORT_API_KEY=همون-کلید-appsettings.json-بک‌اند
"""

from .carx_bridge import collect_yesterday_rows, push_ads_sync
from .config import Settings
from .storage import connect


def main() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)

    rows = collect_yesterday_rows(conn)
    print(f"{len(rows)} آگهی (قیمت‌دار + خاص) از دیروز پیدا شد.")

    if not rows:
        return

    # برای جلوگیری از یه درخواست خیلی بزرگ، دسته‌دسته (هر بار ۱۰۰ تا) بفرست
    batch_size = 100
    total_inserted = total_updated = total_skipped = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        result = push_ads_sync(batch)
        if result is None:
            print("❌ ارسال متوقف شد (تنظیمات CARX_API_URL/CARX_IMPORT_API_KEY را چک کن).")
            return

        total_inserted += result.get("inserted", 0)
        total_updated += result.get("updated", 0)
        total_skipped += result.get("skipped", 0)
        for err in result.get("errors", []):
            print(f"  ⚠️ {err}")

    print(
        f"✅ تمام شد. {total_inserted} آگهی جدید، {total_updated} به‌روزرسانی‌شده، "
        f"{total_skipped} رد شده."
    )


if __name__ == "__main__":
    main()
