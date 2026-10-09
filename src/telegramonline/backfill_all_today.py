from __future__ import annotations

"""بک‌فیل کامل امروز: همه‌ی پیام‌های امروزِ کانال‌ها را دوباره می‌خواند، آگهی‌های
جاافتاده را ذخیره می‌کند و (برخلاف rebackfill) همان‌ها را به سایت (CarX) و گروه
مقصد (با ربات‌ها) هم می‌فرستد. آگهی‌هایی که از قبل ذخیره شده‌اند دوباره نمی‌روند.

⚠️ قبل از اجرا collector را متوقف کن (فایل session را دو پروسه هم‌زمان نمی‌توانند
استفاده کنند) و بعد از پایان دوباره روشنش کن.

اجرا (از ریشه‌ی پروژه، با venv):
    $env:PYTHONPATH="src"
    python -m telegramonline.backfill_all_today arasmehri          # فقط یک/چند کانال (تست)
    python -m telegramonline.backfill_all_today                    # همه‌ی کانال‌ها
    python -m telegramonline.backfill_all_today --no-group         # بدون ارسال به گروه
    python -m telegramonline.backfill_all_today --no-site          # بدون ارسال به سایت
"""

import argparse
import asyncio

from telethon import TelegramClient

from .bot_forwarder import _queues, build_message, enqueue
from .carx_bridge import ad_row_to_dto, push_ads_async
from .collector import backfill_today
from .config import Settings
from .net import parse_proxy_from_env
from .storage import _clean_username, connect, get_channel_by_username, list_active_joined_channels

SENDABLE = ("sale", "buyer", "call_price")


async def run(usernames: list[str], send_site: bool, send_group: bool) -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)

    if usernames:
        channels = []
        for u in usernames:
            ch = get_channel_by_username(conn, _clean_username(u))
            if ch is None:
                print(f"«{u}» در جدول channels نیست.")
                continue
            channels.append(ch)
    else:
        channels = list_active_joined_channels(conn)

    proxy = parse_proxy_from_env()
    client = TelegramClient(
        "telegramonline_user",
        settings.api_id,
        settings.api_hash,
        proxy=proxy,
        connection_retries=None,
        retry_delay=2,
        auto_reconnect=True,
    )
    await client.start()

    print(f"در حال خواندن امروزِ {len(channels)} کانال ...", flush=True)
    all_new: list[tuple[str, str, object]] = []  # (username, title, row)
    for i, ch in enumerate(channels, 1):
        username = ch["username"]
        collected: list = []
        try:
            inserted = await backfill_today(client, conn, ch["id"], username, collected=collected)
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠️ {username}: {exc}", flush=True)
            continue
        if inserted:
            print(f"  [{i}/{len(channels)}] {username}: {inserted} آگهی جاافتاده", flush=True)
        title = (ch["title"] or "").strip() or f"@{username}"
        for row in collected:
            all_new.append((username, title, row))
        await asyncio.sleep(0.3)

    await client.disconnect()

    sendable = [t for t in all_new if t[2]["status"] in SENDABLE]
    # قدیمی‌ترین اول، تا در گروه به ترتیب زمان بیایند
    sendable.sort(key=lambda t: t[2]["message_date"] or "")
    print(f"✅ خواندن تمام شد: {len(all_new)} آگهی جدید ذخیره شد، {len(sendable)} تای آن قابل ارسال است.", flush=True)

    if send_site and sendable:
        titles = {u: t for u, t, _ in sendable}
        dtos = [ad_row_to_dto(row, channel_titles=titles) for _, _, row in sendable]
        for i in range(0, len(dtos), 100):
            await push_ads_async(dtos[i : i + 100])
        print(f"🌐 {len(dtos)} آگهی به سایت فرستاده شد.", flush=True)

    if send_group and sendable and settings.forward_bot_tokens and settings.forward_target_group:
        target = settings.forward_target_group.lstrip("@").lower()
        n = 0
        for username, title, row in sendable:
            if username.lower() == target:
                continue
            # متن اصلی پیام (با خط‌های جدا) از raw_text ردیف
            url = f"https://t.me/{username}/{row['source_message_id']}"
            enqueue(settings.forward_bot_tokens, settings.forward_target_group, build_message(title, url, row["raw_text"]))
            n += 1
        print(f"🤖 {n} پیام در صف ربات‌ها گذاشته شد؛ صبر می‌کنم تا همه فرستاده شود ...", flush=True)
        # صف خالی شدن + یک مکث برای آخرین پیام‌ها
        while any(q.qsize() > 0 for q in _queues.values()):
            await asyncio.sleep(5)
        await asyncio.sleep(10)
        print("✅ ارسال به گروه تمام شد.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("usernames", nargs="*", help="اگر خالی باشد همه‌ی کانال‌ها")
    parser.add_argument("--no-group", action="store_true")
    parser.add_argument("--no-site", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.usernames, not args.no_site, not args.no_group))


if __name__ == "__main__":
    main()
