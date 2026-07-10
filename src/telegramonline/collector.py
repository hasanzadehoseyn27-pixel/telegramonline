from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events

from .config import Settings
from .net import parse_proxy_from_env
from .parser import parse_message
from .storage import connect, save_ads


async def backfill(client: TelegramClient, group: str, db_path: str, days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    conn = connect(db_path)
    parsed = []
    async for message in client.iter_messages(group):
        if not message.message:
            continue
        message_date = message.date
        if message_date and message_date.tzinfo is None:
            message_date = message_date.replace(tzinfo=timezone.utc)
        if message_date and message_date < cutoff:
            break
        parsed.append(parse_message(str(message.id), message.message, message_date))
        if len(parsed) >= 500:
            save_ads(conn, parsed)
            parsed.clear()
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
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy)
    await client.start()

    if days:
        inserted = await backfill(client, settings.group, str(settings.database_path), days)
        print(f"Backfill inserted {inserted} new rows.")

    @client.on(events.NewMessage(chats=settings.group))
    async def handler(event) -> None:
        if not event.message.message:
            return
        ad = parse_message(str(event.message.id), event.message.message, event.message.date)
        save_ads(conn, [ad])
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
