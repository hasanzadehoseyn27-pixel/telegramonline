"""join و بک‌فیل فوری یه کانال خاص، بدون صف‌انتظار ۱۵ دقیقه‌ای.

اجرا (وقتی collector.py خاموشه، چون سشن مشترکه):
    $env:PYTHONPATH="src"
    py manual_join_channel.py gorohekhodroe
"""

import asyncio
import sys

from telethon import TelegramClient

from telegramonline.collector import backfill_today, join_channel
from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env
from telegramonline.storage import connect, get_channel_by_username, mark_channel_joined


async def main(username: str) -> None:
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

    channel = get_channel_by_username(conn, username)
    if channel is None:
        print(f"«{username}» تو دیتابیس پیدا نشد.")
        return

    print(f"در حال join شدن به «{username}»...")
    joined = await join_channel(client, username, allow_group=False)
    if joined == "group":
        print(f"🚫 «{username}» یه گروهه، نه کانال — برنامه کانال‌محوره، اضافه نشد.")
        return
    if not joined:
        print(f"❌ join نشد.")
        return

    title = channel["title"]
    try:
        entity = await client.get_entity(username)
        title = getattr(entity, "title", None) or title
    except Exception:  # noqa: BLE001
        pass
    mark_channel_joined(conn, channel["id"], title=title)

    print("✅ join شد. در حال بک‌فیل امروز...")
    inserted = await backfill_today(client, conn, channel["id"], username)
    print(f"✅ تمام شد. {inserted} پیام امروز اضافه شد.")

    await client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("استفاده: py manual_join_channel.py <username>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
