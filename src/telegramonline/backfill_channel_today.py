from __future__ import annotations

"""بک‌فیل پیام‌های امروز یک کانال/گروه خاص (وقتی به هر دلیلی از قبل رد شده
بودن، مثلاً همین گروه‌هایی که قبلاً پیام‌های خودشون ذخیره نمی‌شد).

⚠️ قبل از اجرا، collector.py را متوقف کن (Ctrl+C)، چون فایل session
تلگرام هم‌زمان توسط دو پروسه قابل استفاده نیست. بعد از اتمام، دوباره
collector رو روشن کن.

اجرا:
    $env:PYTHONPATH="src"
    py -m telegramonline.backfill_channel_today BAZARBOZORGEKHODROIRAN
"""

import argparse
import asyncio

from telethon import TelegramClient

from telegramonline.collector import backfill_today
from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env
from telegramonline.storage import _clean_username, connect, get_channel_by_username


async def run(username: str) -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    clean = _clean_username(username)

    channel = get_channel_by_username(conn, clean)
    if channel is None:
        print(f"«{clean}» توی جدول channels ثبت نشده — اول باید از سایت اضافه‌اش کنی.")
        return
    if not channel["joined"]:
        print(f"«{clean}» هنوز join نشده — بک‌فیل نمی‌تونه کار کند.")
        return

    proxy = parse_proxy_from_env()
    client = TelegramClient(
        "telegramonline_user",
        settings.api_id,
        settings.api_hash,
        proxy=proxy,
    )
    await client.start()

    print(f"در حال خواندن پیام‌های امروز «{clean}» ...", flush=True)
    inserted = await backfill_today(client, conn, channel["id"], clean)
    print(f"✅ {inserted} آگهی جدید/جاافتاده از «{clean}» اضافه شد.")

    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="یوزرنیم کانال/گروه (با یا بدون @)")
    args = parser.parse_args()
    asyncio.run(run(args.username))


if __name__ == "__main__":
    main()
