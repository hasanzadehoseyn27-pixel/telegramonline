from __future__ import annotations

"""تشخیص سریع: آیا collector واقعاً آگهی جدید ذخیره می‌کند یا متوقف شده؟

اجرا:
    $env:PYTHONPATH="src"
    py -m telegramonline.diagnose_freshness
"""

from datetime import datetime, timezone

from telegramonline.config import Settings
from telegramonline.storage import connect


def main() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)

    rows = conn.execute(
        """
        SELECT id, channel_username, vehicle_key, message_date, created_at
        FROM ads
        ORDER BY id DESC
        LIMIT 5
        """
    ).fetchall()

    if not rows:
        print("هیچ آگهی‌ای توی دیتابیس نیست!")
        return

    now = datetime.now(timezone.utc)
    print("۵ آگهی آخری که در کل دیتابیس ذخیره شده (صرف‌نظر از امروز/دیروز):\n")
    for row in rows:
        created = row["created_at"]
        print(f"  id={row['id']:<8} کانال=@{row['channel_username']:<25} مدل={row['vehicle_key'] or 'نامشخص':<20} ذخیره‌شده در={created}")

    # فاصله‌ی زمانی آخرین آگهی تا الان
    last_created_raw = rows[0]["created_at"]
    try:
        last_created = datetime.fromisoformat(last_created_raw.replace(" ", "T")).replace(tzinfo=timezone.utc)
        delta = now - last_created
        minutes_ago = int(delta.total_seconds() / 60)
        print(f"\n⏱ آخرین آگهی حدود {minutes_ago} دقیقه پیش ذخیره شده.")
        if minutes_ago > 15:
            print("⚠️  بیشتر از ۱۵ دقیقه از آخرین آگهی گذشته — این یعنی احتمالاً collector واقعاً چیزی دریافت نمی‌کند.")
        else:
            print("✅ اخیراً آگهی جدید ذخیره شده؛ collector زنده و در حال کار است.")
    except Exception as exc:  # noqa: BLE001
        print(f"(نتوانستم created_at را پارس کنم: {exc})")

    total = conn.execute("SELECT COUNT(*) c FROM ads").fetchone()["c"]
    print(f"\nتعداد کل ردیف‌های ads در کل دیتابیس (همه‌ی روزها): {total}")


if __name__ == "__main__":
    main()
