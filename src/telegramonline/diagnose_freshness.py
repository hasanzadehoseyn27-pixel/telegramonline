from __future__ import annotations

"""تشخیص سریع: آیا collector واقعاً آگهی جدید ذخیره می‌کند یا متوقف شده؟

اجرا:
    $env:PYTHONPATH="src"
    py -m telegramonline.diagnose_freshness
    py -m telegramonline.diagnose_freshness BAZARBOZORGEKHODROIRAN   # فقط یک کانال
"""

import sys
from datetime import datetime, timezone

from telegramonline.config import Settings
from telegramonline.storage import _clean_username, connect


def main() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)

    channel_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if channel_filter:
        clean = _clean_username(channel_filter)
        row = conn.execute(
            "SELECT active, joined, username, title FROM channels WHERE username = ?",
            (clean,),
        ).fetchone()
        if row is None:
            print(f"«{clean}» اصلاً توی جدول channels ما ثبت نشده (نه به‌عنوان کانال).")
            print("اگه این یه گروهه (نه کانال)، احتمالاً به‌عنوان «گروه منبع» ثبت شده، نه کانال — و پیام‌های خودش مستقیماً ذخیره نمی‌شن، فقط برای کشف کانال‌های فورواردشده استفاده می‌شه.")
        else:
            print(f"«{clean}» → active={bool(row['active'])} | joined={bool(row['joined'])} | title={row['title']}")
            if not row["joined"]:
                print("⚠️  این کانال هنوز join نشده — پس پیام‌هاش اصلاً دریافت نمی‌شن.")
            if not row["active"]:
                print("⚠️  این کانال غیرفعال شده (احتمالاً به‌خاطر شکست join مکرر).")
        rows = conn.execute(
            """
            SELECT id, channel_username, vehicle_key, message_date, created_at
            FROM ads
            WHERE channel_username = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (clean,),
        ).fetchall()
        print(f"\n۵ آگهی آخر از «{clean}» (در کل تاریخچه):\n")
    else:
        rows = conn.execute(
            """
            SELECT id, channel_username, vehicle_key, message_date, created_at
            FROM ads
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()
        print("۵ آگهی آخری که در کل دیتابیس ذخیره شده (صرف‌نظر از امروز/دیروز):\n")

    if not rows:
        print("هیچ آگهی‌ای پیدا نشد!")
        return

    now = datetime.now(timezone.utc)
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
        if not channel_filter and minutes_ago > 15:
            print("⚠️  بیشتر از ۱۵ دقیقه از آخرین آگهی گذشته — این یعنی احتمالاً collector واقعاً چیزی دریافت نمی‌کند.")
        elif not channel_filter:
            print("✅ اخیراً آگهی جدید ذخیره شده؛ collector زنده و در حال کار است.")
    except Exception as exc:  # noqa: BLE001
        print(f"(نتوانستم created_at را پارس کنم: {exc})")

    if not channel_filter:
        total = conn.execute("SELECT COUNT(*) c FROM ads").fetchone()["c"]
        print(f"\nتعداد کل ردیف‌های ads در کل دیتابیس (همه‌ی روزها): {total}")


if __name__ == "__main__":
    main()
