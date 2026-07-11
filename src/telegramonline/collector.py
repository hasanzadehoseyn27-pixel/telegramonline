from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events

from .config import Settings
from .net import parse_proxy_from_env, resolve_chat_id
from .parser import parse_message_group
from .storage import connect, save_ads


async def backfill(client: TelegramClient, group, db_path: str, days: int) -> int:
    """کل تاریخچه گروه تا `days` روز قبل را با شماره پیام واقعی می‌خواند."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    conn = connect(db_path)
    parsed = []
    total_seen = 0
    async for message in client.iter_messages(group):
        total_seen += 1
        if not message.message:
            continue
        message_date = message.date
        if message_date and message_date.tzinfo is None:
            message_date = message_date.replace(tzinfo=timezone.utc)
        if message_date and message_date < cutoff:
            break
        parsed.extend(parse_message_group(str(message.id), message.message, message_date, source="live"))
        if len(parsed) >= 500:
            save_ads(conn, parsed)
            parsed.clear()
        if total_seen % 2000 == 0:
            print(f"... {total_seen} پیام بررسی شد", flush=True)
    inserted = save_ads(conn, parsed)
    conn.close()
    return inserted


async def live_collect(days: int | None = None) -> None:
    settings = Settings.from_env()
    if not settings.group:
        raise RuntimeError("TELEGRAM_GROUP is empty. Add group username or id to .env.")

    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    if proxy:
        print("Using Telegram proxy from TELEGRAM_PROXY.", flush=True)
    group_chat_id = resolve_chat_id(settings.group)
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy)
    await client.start()

    if days:
        print(f"⏳ در حال دریافت تاریخچه {days} روز اخیر با شماره پیام واقعی...")
        inserted = await backfill(client, group_chat_id, str(settings.database_path), days)
        print(f"✅ Backfill inserted {inserted} new rows.")

    @client.on(events.NewMessage(chats=group_chat_id))
    async def handler(event) -> None:
        if not event.message.message:
            return
        ads = parse_message_group(str(event.message.id), event.message.message, event.message.date, source="live")
        save_ads(conn, ads)
        for ad in ads:
            if ad.status == "sale" and ad.vehicle_name and ad.price_million:
                print(f"{ad.vehicle_name}: {ad.price_million} million | confidence={ad.confidence}")

    print("telegramonline collector is running.")
    await client.run_until_disconnected()


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Telegram group ads with Telethon user session.")
    parser.add_argument("--backfill-days", type=int, help="Read recent group history before live collecting.")
    args = parser.parse_args()
    asyncio.run(live_collect(args.backfill_days))


if __name__ == "__main__":
    main()