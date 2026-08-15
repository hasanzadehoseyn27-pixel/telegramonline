"""همه‌ی کانال‌هایی که این اکانت از قبل توشون عضوه رو پیدا و به دیتابیس
تلگرام‌آنلاین اضافه می‌کند (بدون نیاز به join جدید، چون از قبل عضوه).

⚠️ قبل از اجرا حتماً collector.py رو متوقف کن (Ctrl+C)، چون هردو از یه
session تلگرام استفاده می‌کنن.

اجرا:
    $env:PYTHONPATH="src"
    py import_existing_memberships.py
"""

import asyncio

from telethon import TelegramClient
from telethon.tl.types import Channel

from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env
from telegramonline.storage import add_channel, connect


async def main() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()

    client = TelegramClient(
        "telegramonline_user",
        settings.api_id,
        settings.api_hash,
        proxy=proxy,
        connection_retries=None,
    )
    await client.start()

    added = 0
    skipped_group = 0
    skipped_no_username = 0
    skipped_duplicate = 0

    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if not isinstance(entity, Channel):
            continue  # کاربر تکی/چت خصوصی نیست

        is_group = getattr(entity, "megagroup", False)
        if is_group:
            skipped_group += 1
            print(f"⏭️ رد شد (گروهه، نه کانال): {dialog.name}")
            continue

        username = entity.username
        if not username:
            skipped_no_username += 1
            print(f"⏭️ رد شد (یوزرنیم عمومی نداره): {dialog.name}")
            continue

        result = add_channel(conn, username, title=dialog.name)
        if result is not None:
            added += 1
            print(f"✅ اضافه شد: @{username} ({dialog.name})")
        else:
            skipped_duplicate += 1

    print()
    print(f"جمع‌بندی: {added} کانال جدید اضافه شد.")
    print(f"  {skipped_group} تا گروه بودن (رد شدن، طبق سیاست کانال‌محور بودن).")
    print(f"  {skipped_no_username} تا یوزرنیم عمومی نداشتن (رد شدن).")
    print(f"  {skipped_duplicate} تا از قبل تو دیتابیس بودن.")
    print("چرخه‌ی sync_channels (تو ترمینال Collector) این‌ها رو فوراً join‌شده تشخیص می‌ده (چون از قبل عضویم).")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
