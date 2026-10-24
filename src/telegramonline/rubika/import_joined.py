"""همه‌ی کانال‌هایی که اکانت روبیکای جمع‌کننده عضوشان است را به لیست پایش
اضافه می‌کند، و آمار آگهی‌های امروز هر کانال را نشان می‌دهد.

    $env:PYTHONPATH="src"
    venv\\Scripts\\python -m telegramonline.rubika.import_joined          # افزودن همه + آمار
    venv\\Scripts\\python -m telegramonline.rubika.import_joined --stats  # فقط آمار
    venv\\Scripts\\python -m telegramonline.rubika.import_joined --groups # فهرست گروه‌ها

کانال‌ها «عضو شده» ثبت می‌شوند؛ جمع‌کننده (rubika-collector) بعد از ری‌استارت
آگهی‌های امروزشان را جمع می‌کند (و به سایت می‌فرستد) و از آن به بعد زنده پایش می‌کند.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import load_dotenv
from ..storage import add_channel, connect, get_channel_by_username, is_channel_blocked, mark_channel_joined
from .client import RubikaAccount, RubikaFlood, _find

TEHRAN = timezone(timedelta(hours=3, minutes=30))


async def joined_chats(account: RubikaAccount, prefix: str, kinds: tuple[str, ...]) -> list[dict]:
    """[{guid, title}] همه‌ی چت‌های اکانت با این نوع (صفحه به صفحه)."""
    out: dict[str, dict] = {}
    start_id = None
    for _ in range(200):
        res = await account._call("getChats", {"start_id": start_id} if start_id else {})
        for chat in res.get("chats") or []:
            abs_obj = chat.get("abs_object") or {}
            guid = str(chat.get("object_guid") or abs_obj.get("object_guid") or "")
            kind = str(abs_obj.get("type") or "")
            if guid.startswith(prefix) and (kind in ("",) + kinds):
                out[guid] = {"guid": guid, "title": str(abs_obj.get("title") or "")}
        start_id = res.get("next_start_id")
        if not res.get("has_continue") or not start_id:
            break
    return list(out.values())


async def joined_channels(account: RubikaAccount) -> list[dict]:
    return await joined_chats(account, "c0", ("Channel",))


async def list_groups(account: RubikaAccount) -> None:
    groups = await joined_chats(account, "g0", ("Group",))
    print(f"👥 اکانت در {len(groups)} گروه روبیکا عضو است:", flush=True)
    for i, g in enumerate(sorted(groups, key=lambda x: x["title"]), start=1):
        print(f"  {i:>3}. {g['title'] or '-'} ({g['guid']})", flush=True)


async def import_all(conn: sqlite3.Connection, account: RubikaAccount) -> None:
    chans = await joined_channels(account)
    print(f"📋 اکانت در {len(chans)} کانال روبیکا عضو است.", flush=True)
    added = existing = blocked = 0
    for n, ch in enumerate(chans, start=1):
        guid = ch["guid"]
        title = ch["title"]
        username = ""
        for attempt in range(3):
            try:
                info = await account.channel_info(guid)
                username = info.get("username") or ""
                title = info.get("title") or title
                break
            except RubikaFlood as exc:
                print(f"⏳ محدودیت روبیکا؛ {exc.seconds} ثانیه صبر...", flush=True)
                await asyncio.sleep(exc.seconds)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ اطلاعات {title or guid} گرفته نشد: {exc}", flush=True)
                break
        key = username or guid  # کانال بدون یوزرنیم با guid ثبت می‌شود
        if is_channel_blocked(conn, key):
            blocked += 1
            continue
        if get_channel_by_username(conn, key) is not None:
            existing += 1
            continue
        channel_id = add_channel(conn, key, title=title or None)
        if channel_id is not None:
            mark_channel_joined(conn, channel_id, title=title or None)
            added += 1
            print(f"  ➕ {n}. {title or '-'} ({key})", flush=True)
        await asyncio.sleep(0.4)
    print(f"✅ {added} کانال تازه اضافه شد؛ {existing} تا از قبل بود؛ {blocked} تا مسدود بود.", flush=True)


def print_stats(conn: sqlite3.Connection) -> None:
    today = datetime.now(TEHRAN).date().isoformat()
    rows = conn.execute(
        """
        SELECT c.username, c.title,
               COUNT(a.id) AS ads,
               SUM(CASE WHEN a.status IN ('sale','buyer','call_price') THEN 1 ELSE 0 END) AS relevant
        FROM channels c
        LEFT JOIN ads a ON a.channel_id = c.id AND a.day_key = ?
        WHERE c.active = 1
        GROUP BY c.id
        ORDER BY relevant DESC, ads DESC, c.title
        """,
        (today,),
    ).fetchall()
    total = sum(int(r["relevant"] or 0) for r in rows)
    with_ads = sum(1 for r in rows if (r["relevant"] or 0) > 0)
    print(f"\n📊 آمار امروز ({today}): {len(rows)} کانال، {with_ads} کانال آگهی داشته، مجموع {total} آگهی", flush=True)
    for i, r in enumerate(rows, start=1):
        print(f"  {i:>3}. {int(r['relevant'] or 0):>4} آگهی | {r['title'] or '-'} ({r['username']})", flush=True)


async def _main(stats_only: bool, groups_only: bool = False) -> None:
    load_dotenv()
    if groups_only:
        account = RubikaAccount(Path(os.getenv("RUBIKA_SESSION", "data/rubika")))
        await account.connect()
        try:
            await list_groups(account)
        finally:
            await account.disconnect()
        return
    conn = connect(Path(os.getenv("RUBIKA_DATABASE_PATH", "data/rubikaonline.sqlite3")))
    if not stats_only:
        account = RubikaAccount(Path(os.getenv("RUBIKA_SESSION", "data/rubika")))
        await account.connect()
        try:
            await import_all(conn, account)
        finally:
            await account.disconnect()
    print_stats(conn)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("rubpy").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", action="store_true", help="فقط آمار آگهی‌های امروز هر کانال")
    parser.add_argument("--groups", action="store_true", help="فقط فهرست گروه‌هایی که اکانت عضوشان است")
    args = parser.parse_args()
    asyncio.run(_main(args.stats, args.groups))


if __name__ == "__main__":
    main()
