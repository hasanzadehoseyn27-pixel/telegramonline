"""پیدا کردن و غیرفعال‌کردن هر «کانالِ» ثبت‌شده‌ای که در واقع یه گروه/سوپرگروهه
(نه کانال broadcast) — چون برنامه الان کانال‌محوره.

⚠️ قبل از اجرا حتماً collector.py رو متوقف کن (Ctrl+C)، چون هردو از یه
session تلگرام استفاده می‌کنن و نمی‌تونن هم‌زمان روشن باشن.

اجرا:
    $env:PYTHONPATH="src"
    py find_and_remove_groups.py
"""

import asyncio

from telethon import TelegramClient

from telegramonline.collector import leave_channel
from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env
from telegramonline.storage import connect, deactivate_channel, list_active_joined_channels


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

    channels = list_active_joined_channels(conn)
    print(f"در حال بررسی {len(channels)} کانال فعال...")

    found_groups = []
    for ch in channels:
        username = ch["username"]
        try:
            entity = await client.get_entity(username)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ نتوانستم اطلاعات «{username}» را بگیرم: {exc}")
            continue

        is_group = getattr(entity, "megagroup", False) or type(entity).__name__ == "Chat"
        if is_group:
            found_groups.append((ch, username))
            print(f"🚫 گروهه، نه کانال: {username} ({ch['title'] or '-'})")

    if not found_groups:
        print("\n✅ هیچ گروهی پیدا نشد — همه‌چیز از قبل کانال‌محوره.")
        await client.disconnect()
        return

    print(f"\n{len(found_groups)} گروه پیدا شد. در حال ترک و غیرفعال‌سازی...")
    for ch, username in found_groups:
        try:
            await leave_channel(client, username)
        except Exception:  # noqa: BLE001
            pass
        deactivate_channel(conn, ch["id"])
        print(f"✅ {username} غیرفعال شد.")

    print(f"\nتمام شد. {len(found_groups)} گروه غیرفعال شد.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
