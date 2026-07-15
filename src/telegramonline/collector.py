from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, UserAlreadyParticipantError, UserNotParticipantError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.types import PeerChannel

from .config import Settings
from .api.events import broadcast_new_ad, broadcast_price_alert, broadcast_price_update
from .api.price_tracker import check_price_change
from .net import parse_proxy_from_env
from .parser import parse_message_group
from .storage import (
    _compute_day_key,
    add_channel,
    check_price_alerts,
    connect,
    delete_ads_by_channel_username,
    delete_ads_for_channel,
    get_channel_by_username,
    increment_source_group_discovered,
    list_active_joined_channels,
    list_active_joined_source_groups,
    list_channels,
    list_channels_pending_leave,
    list_source_groups_pending_leave,
    list_unjoined_channels,
    list_unjoined_source_groups,
    mark_channel_joined,
    mark_source_group_joined,
    purge_old_ads,
    remove_channel,
    remove_source_group,
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


async def _entity_username(client: TelegramClient, peer) -> tuple[str | None, str | None]:
    if peer is None:
        return None, None
    try:
        entity = await client.get_entity(peer)
    except Exception:  # noqa: BLE001
        return None, None
    return getattr(entity, "username", None), getattr(entity, "title", None)


async def forwarded_channel_origin(client: TelegramClient, message) -> tuple[str | None, str | None]:
    fwd = getattr(message, "fwd_from", None)
    if fwd is None:
        return None, None
    for peer in (getattr(fwd, "from_id", None), getattr(fwd, "saved_from_peer", None)):
        if isinstance(peer, PeerChannel):
            username, title = await _entity_username(client, peer)
            if username:
                return username, title
    return None, None


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
                saved = save_ads(conn, parsed, channel_id=channel_id, channel_username=channel_username)
                inserted += len(saved)
                parsed.clear()
        saved = save_ads(conn, parsed, channel_id=channel_id, channel_username=channel_username)
        inserted += len(saved)
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


async def sync_source_groups(client: TelegramClient, conn) -> set[str]:
    for group in list_unjoined_source_groups(conn):
        username = group["username"]
        print(f"source group discovered: {username}; joining...", flush=True)
        joined = await join_channel(client, username)
        if not joined:
            print(f"source group join failed: {username}", flush=True)
            continue
        title = group["title"]
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", None) or title
        except Exception:  # noqa: BLE001
            pass
        mark_source_group_joined(conn, group["id"], title=title)
        print(f"source group is active: {username}", flush=True)

    for group in list_source_groups_pending_leave(conn):
        username = group["username"]
        left = await leave_channel(client, username)
        if left:
            remove_source_group(conn, group["id"])
            print(f"source group removed: {username}", flush=True)
        else:
            print(f"source group leave failed: {username}", flush=True)

    return {g["username"] for g in list_active_joined_source_groups(conn)}


async def channel_sync_loop(client: TelegramClient, conn, known: set[str]) -> None:
    while True:
        await asyncio.sleep(CHANNEL_SYNC_INTERVAL_SECONDS)
        try:
            updated = await sync_channels(client, conn)
            known.clear()
            known.update(updated)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ خطا در بررسی کانال‌های جدید: {exc}", flush=True)


async def source_group_sync_loop(client: TelegramClient, conn, known_groups: set[str]) -> None:
    while True:
        await asyncio.sleep(CHANNEL_SYNC_INTERVAL_SECONDS)
        try:
            updated = await sync_source_groups(client, conn)
            known_groups.clear()
            known_groups.update(updated)
        except Exception as exc:  # noqa: BLE001
            print(f"source group sync error: {exc}", flush=True)


async def discover_forwarded_channel_from_group(
    client: TelegramClient,
    conn,
    known_channels: set[str],
    group_username: str,
    message,
) -> None:
    origin_username, origin_title = await forwarded_channel_origin(client, message)
    if not origin_username or origin_username in known_channels:
        return

    existing = get_channel_by_username(conn, origin_username)
    if existing is None:
        channel_id = add_channel(conn, origin_username, title=origin_title)
        if channel_id is None:
            return
        increment_source_group_discovered(conn, group_username)
        print(f"forwarded channel discovered from {group_username}: {origin_username}", flush=True)
    else:
        channel_id = existing["id"]

    joined = await join_channel(client, origin_username)
    if not joined:
        return
    mark_channel_joined(conn, channel_id, title=origin_title)
    known_channels.add(origin_username)
    inserted = await backfill_today(client, conn, channel_id, origin_username)
    print(f"forwarded channel activated: {origin_username}, inserted_today={inserted}", flush=True)


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
    known_groups: set[str] = await sync_source_groups(client, conn)
    print(f"📡 در حال گوش‌دادن به {len(known)} کانال: {', '.join(sorted(known)) or '—'}", flush=True)

    @client.on(events.NewMessage)
    async def handler(event) -> None:
        chat = await event.get_chat()
        username = getattr(chat, "username", None)
        if username and username in known_groups:
            await discover_forwarded_channel_from_group(
                client,
                conn,
                known,
                username,
                event.message,
            )
            return
        if not username or username not in known:
            return
        if not event.message.message:
            return
        channel = get_channel_by_username(conn, username)
        if channel is None or not channel["active"]:
            return
        ads = parse_message_group(str(event.message.id), event.message.message, event.message.date, source="live")
        saved_ads = save_ads(conn, ads, channel_id=channel["id"], channel_username=username)

        triggered_alerts = check_price_alerts(
            conn,
            saved_ads,
        )

        for ad in saved_ads:
            await broadcast_new_ad(
                {
                    "id": ad["id"],
                    "vehicle_key": ad["vehicle_key"],
                    "vehicle_name": ad["vehicle_name"],
                    "price_million": ad["price_million"],
                    "year": ad["year"],
                    "color": ad["color"],
                    "phone": ad["phone"],
                }
            )

        for alert_ad in triggered_alerts:
            await broadcast_price_alert(
                {
                    "vehicle_key": alert_ad["vehicle_key"],
                    "vehicle_name": alert_ad["vehicle_name"],
                    "price_million": alert_ad["price_million"],
                }
            )


        for ad in saved_ads:

            if (
                ad["vehicle_key"]
                and ad["price_million"]
            ):

                price_event = check_price_change(
                    ad["vehicle_key"],
                    ad["price_million"],
                )

                if price_event:
                    await broadcast_price_update(
                        price_event
                    )

        for ad in ads:
            if ad.status == "sale" and ad.vehicle_name and ad.price_million:
                print(f"[{username}] {ad.vehicle_name}: {ad.price_million} million | confidence={ad.confidence}")

    asyncio.create_task(channel_sync_loop(client, conn, known))
    asyncio.create_task(source_group_sync_loop(client, conn, known_groups))
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
