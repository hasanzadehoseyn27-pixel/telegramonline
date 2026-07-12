from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, UserAlreadyParticipantError, UserNotParticipantError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest

from .config import Settings
from .net import parse_proxy_from_env
from .parser import parse_message_group
from .storage import (
    _compute_day_key,
    add_channel,
    connect,
    delete_ads_by_channel_username,
    delete_ads_for_channel,
    get_channel_by_username,
    list_active_joined_channels,
    list_channels,
    list_channels_pending_leave,
    list_unjoined_channels,
    mark_channel_joined,
    purge_old_ads,
    remove_channel,
    save_ads,
)

CHANNEL_SYNC_INTERVAL_SECONDS = 30


async def join_channel(client: TelegramClient, username: str) -> bool:
    """اکانت شخصی را عضو کانال عمومی می‌کند (لازم برای دریافت پیام‌های زنده)."""
    try:
        entity = await client.get_entity(username)
        await client(JoinChannelRequest(entity))
        return True
    except UserAlreadyParticipantError:
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ نتوانستم عضو کانال {username} شوم: {exc}", flush=True)
        return False


async def leave_channel(client: TelegramClient, username: str) -> bool:
    """اکانت شخصی را از عضویت کانال خارج می‌کند (وقتی کاربر کانال را حذف می‌کند)."""
    try:
        entity = await client.get_entity(username)
        await client(LeaveChannelRequest(entity))
        return True
    except (UserNotParticipantError, ChannelPrivateError):
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ نتوانستم از کانال {username} خارج شوم: {exc}", flush=True)
        return False


async def backfill_today(
    client: TelegramClient,
    conn,
    channel_id: int,
    channel_username: str,
) -> int:
    """فقط پیام‌های همان روز (به‌وقت تهران) کانال را با شماره پیام واقعی می‌خواند."""
    today = _compute_day_key(datetime.now(timezone.utc))
    parsed = []
    total_seen = 0
    inserted = 0
    try:
        async for message in client.iter_messages(channel_username):
            total_seen += 1
            if not message.message:
                continue
            message_date = message.date
            if message_date and message_date.tzinfo is None:
                message_date = message_date.replace(tzinfo=timezone.utc)
            if message_date and _compute_day_key(message_date) != today:
                break
            parsed.extend(
                parse_message_group(str(message.id), message.message, message_date, source="live")
            )
            if len(parsed) >= 300:
                inserted += save_ads(conn, parsed, channel_id=channel_id, channel_username=channel_username)
                parsed.clear()
        inserted += save_ads(conn, parsed, channel_id=channel_id, channel_username=channel_username)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ خطا در بک‌فیل کانال {channel_username}: {exc}", flush=True)
    return inserted


async def add_and_activate_channel(client: TelegramClient, conn, username: str, title: str | None = None) -> dict:
    """کانال جدید را ثبت، عضو می‌شود، و پیام‌های همان روز را می‌خواند.

    این تابع را هم CLI و هم (در آینده) بات صدا می‌زند؛ چون فقط دیتابیس را
    تغییر می‌دهد، حلقه‌ی زنده‌ی collector.py خودش این کانال را در کمتر از
    ۳۰ ثانیه شناسایی و شروع به گوش‌دادن می‌کند (نیازی به ری‌استارت نیست).
    """
    channel_id = add_channel(conn, username, title=title)
    if channel_id is None:
        return {"status": "duplicate", "username": username}
    joined = await join_channel(client, username)
    if joined:
        real_title = title
        try:
            entity = await client.get_entity(username)
            real_title = getattr(entity, "title", None) or title
        except Exception:  # noqa: BLE001
            pass
        mark_channel_joined(conn, channel_id, title=real_title)
    inserted = await backfill_today(client, conn, channel_id, username) if joined else 0
    return {"status": "ok", "channel_id": channel_id, "joined": joined, "inserted_today": inserted}


async def sync_channels(client: TelegramClient, conn) -> set[str]:
    """کانال‌های ثبت‌شده‌ی هنوز-عضونشده را عضو و بک‌فیل امروز می‌کند.

    وضعیت «عضو شده یا نه» مستقیم از ستون channels.joined خوانده می‌شود (نه یک
    مجموعه‌ی موقت در حافظه)، تا هر رابط دیگری (بات، بعداً سایت) هم که یک ردیف
    کانال جدید در دیتابیس بگذارد، همین حلقه در دور بعدی آن را پیدا و فعال کند.
    """
    for channel in list_unjoined_channels(conn):
        username = channel["username"]
        print(f"🆕 کانال جدید شناسایی شد: {username} — در حال عضویت و بک‌فیل امروز...", flush=True)
        joined = await join_channel(client, username)
        if not joined:
            print(f"❌ کانال {username} عضو نشد؛ در دور بعد دوباره تلاش می‌شود.", flush=True)
            continue
        title = channel["title"]
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", None) or title
        except Exception:  # noqa: BLE001
            pass
        mark_channel_joined(conn, channel["id"], title=title)
        inserted = await backfill_today(client, conn, channel["id"], username)
        print(f"✅ کانال {username} فعال شد ({inserted} پیام امروز).", flush=True)

    for channel in list_channels_pending_leave(conn):
        username = channel["username"]
        print(f"🚪 در حال خروج از کانال {username}...", flush=True)
        left = await leave_channel(client, username)
        if left:
            deleted_ads = delete_ads_for_channel(conn, channel["id"])
            remove_channel(conn, channel["id"])
            print(f"✅ از کانال {username} خارج شد؛ کانال و {deleted_ads} آگهی‌اش کامل حذف شدند.", flush=True)
        else:
            print(f"⚠️ خروج از {username} ناموفق بود؛ در دور بعد دوباره تلاش می‌شود.", flush=True)

    return {c["username"] for c in list_active_joined_channels(conn)}


async def channel_sync_loop(client: TelegramClient, conn, known: set[str]) -> None:
    while True:
        await asyncio.sleep(CHANNEL_SYNC_INTERVAL_SECONDS)
        try:
            updated = await sync_channels(client, conn)
            known.clear()
            known.update(updated)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ خطا در بررسی کانال‌های جدید: {exc}", flush=True)


TEHRAN_OFFSET = timedelta(hours=3, minutes=30)


def _seconds_until_next_tehran_midnight() -> float:
    now_utc = datetime.now(timezone.utc)
    now_tehran = now_utc + TEHRAN_OFFSET
    next_midnight_tehran = (now_tehran + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    next_midnight_utc = next_midnight_tehran - TEHRAN_OFFSET
    return max(1.0, (next_midnight_utc - now_utc).total_seconds())


async def midnight_purge_loop(conn) -> None:
    """هر شب کمی بعد از ۰۰:۰۰ به‌وقت تهران، فقط امروز+دیروز را نگه می‌دارد."""
    while True:
        wait_seconds = _seconds_until_next_tehran_midnight()
        print(f"🕛 پاک‌سازی بعدی حدود {wait_seconds / 3600:.1f} ساعت دیگر (نیمه‌شب تهران).", flush=True)
        await asyncio.sleep(wait_seconds)
        try:
            deleted = purge_old_ads(conn)
            print(f"🧹 پاک‌سازی شبانه انجام شد؛ {deleted} ردیف قدیمی حذف شد.", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ خطا در پاک‌سازی شبانه: {exc}", flush=True)


async def live_collect() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    if proxy:
        print("Using Telegram proxy from TELEGRAM_PROXY.", flush=True)
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy)
    await client.start()

    # اگر collector مدتی خاموش بوده و از نیمه‌شب گذشته، همین الان هم یک‌بار پاک‌سازی کن.
    deleted_on_start = purge_old_ads(conn)
    if deleted_on_start:
        print(f"🧹 پاک‌سازی ابتدای اجرا: {deleted_on_start} ردیف قدیمی حذف شد.", flush=True)

    known: set[str] = await sync_channels(client, conn)
    print(f"📡 در حال گوش‌دادن به {len(known)} کانال: {', '.join(sorted(known)) or '—'}", flush=True)

    @client.on(events.NewMessage)
    async def handler(event) -> None:
        chat = await event.get_chat()
        username = getattr(chat, "username", None)
        if not username or username not in known:
            return
        if not event.message.message:
            return
        channel = get_channel_by_username(conn, username)
        if channel is None or not channel["active"]:
            return
        ads = parse_message_group(str(event.message.id), event.message.message, event.message.date, source="live")
        save_ads(conn, ads, channel_id=channel["id"], channel_username=username)
        for ad in ads:
            if ad.status == "sale" and ad.vehicle_name and ad.price_million:
                print(f"[{username}] {ad.vehicle_name}: {ad.price_million} million | confidence={ad.confidence}")

    asyncio.create_task(channel_sync_loop(client, conn, known))
    asyncio.create_task(midnight_purge_loop(conn))
    print("telegramonline collector is running.")
    await client.run_until_disconnected()


async def add_channel_cli(username: str) -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy)
    await client.start()
    result = await add_and_activate_channel(client, conn, username)
    print(result)
    await client.disconnect()


def purge_channel_ads_cli(username: str) -> None:
    """پاک‌سازی دستی آگهی‌های یک یوزرنیم — برای کانال‌هایی که قبل از این اصلاح حذف شدند."""
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    deleted = delete_ads_by_channel_username(conn, username)
    print(f"🗑 {deleted} آگهی از «{username}» پاک شد.")


def purge_now_cli() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    deleted = purge_old_ads(conn)
    print(f"🧹 {deleted} ردیف قدیمی‌تر از دیروز حذف شد.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Telegram channel ads with a Telethon user session.")
    parser.add_argument("--add-channel", help="Add and activate a public channel by username, then exit.")
    parser.add_argument("--purge-channel-ads", help="Delete all stored ads for a channel username, then exit.")
    parser.add_argument("--purge-now", action="store_true", help="Delete everything older than yesterday, then exit.")
    args = parser.parse_args()
    if args.add_channel:
        asyncio.run(add_channel_cli(args.add_channel))
    elif args.purge_channel_ads:
        purge_channel_ads_cli(args.purge_channel_ads)
    elif args.purge_now:
        purge_now_cli()
    else:
        asyncio.run(live_collect())


if __name__ == "__main__":
    main()