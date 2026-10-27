"""پیدا کردن و بلاک کردن کانال‌های غیرخودرویی روبیکا (خبری، سیاسی، سرگرمی، ...).

    $env:PYTHONPATH="src"

    # ۱) فهرست مشکوک‌ها: کانال‌هایی که در ۳۰ پیام آخرشان کمتر از ۲ آگهی خودرو دارند
    venv\\Scripts\\python -m telegramonline.rubika.block --suggest

    # ۲) بلاک همه‌ی مشکوک‌های مرحله‌ی ۱ (از فایل data/rubika_suspects.txt)
    venv\\Scripts\\python -m telegramonline.rubika.block --file data/rubika_suspects.txt

    # یا بلاک تکی/چندتایی با یوزرنیم
    venv\\Scripts\\python -m telegramonline.rubika.block tejaratnewsofficial qom_fouri

    # فهرست بلاک‌شده‌ها / آزاد کردن
    venv\\Scripts\\python -m telegramonline.rubika.block --list
    venv\\Scripts\\python -m telegramonline.rubika.block --unblock qom_fouri

بلاک یعنی: در blocked_channels ثبت می‌شود (پیمایش گروه‌ها دیگر اضافه‌اش نمی‌کند)،
کانال غیرفعال می‌شود (جمع‌کننده در چرخه‌ی بعدی از آن خارج می‌شود و ردیفش را پاک
می‌کند) و آگهی‌هایش از دیتابیس روبیکا پاک می‌شود.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sqlite3
import sys
from pathlib import Path

from ..config import load_dotenv
from ..parser import parse_message_group
from ..storage import block_channel, connect, delete_ads_for_channel, get_channel_by_username, unblock_channel
from .client import RubikaAccount, RubikaFlood, is_guid
from .collector import MIN_CAR_ADS_TO_DISCOVER, is_car_ad

SUSPECTS_FILE = Path("data/rubika_suspects.txt")


async def suggest(conn: sqlite3.Connection, account: RubikaAccount, sample: int = 30) -> list[str]:
    rows = conn.execute("SELECT * FROM channels WHERE active = 1 ORDER BY title").fetchall()
    peers = {r["username"]: r["guid"] for r in conn.execute("SELECT username, guid FROM rubika_peers")}
    print(f"🔍 بررسی {len(rows)} کانال (۳۰ پیام آخر هرکدام)...", flush=True)
    suspects: list[tuple[str, str, int]] = []
    for n, ch in enumerate(rows, start=1):
        username = ch["username"]
        guid = peers.get(username) or (username if is_guid(username) else "")
        for attempt in range(4):
            try:
                if not guid:
                    guid = await account.get_peer_id(username)
                msgs = await account.latest(guid, sample)
                break
            except RubikaFlood as exc:
                print(f"⏳ محدودیت روبیکا؛ {exc.seconds} ثانیه صبر...", flush=True)
                await asyncio.sleep(exc.seconds)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ {username}: {exc}", flush=True)
                msgs = None
                break
        else:
            msgs = None
        if msgs is None:
            continue
        car = 0
        for m in msgs:
            if m.sticker is not None or not (m.text or "").strip():
                continue
            if any(is_car_ad(ad) for ad in parse_message_group(str(m.id), m.text, m.date, source="check")):
                car += 1
        mark = "🚫" if car < MIN_CAR_ADS_TO_DISCOVER else "✅"
        print(f"  {mark} {n:>3}. {car:>2}/{len(msgs):<2} آگهی خودرو | {ch['title'] or '-'} ({username})", flush=True)
        if car < MIN_CAR_ADS_TO_DISCOVER:
            suspects.append((username, ch["title"] or "", car))
        await asyncio.sleep(1.0)
    SUSPECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUSPECTS_FILE.write_text(
        "# کانال‌های مشکوک (غیرخودرویی). هر خط را که نمی‌خواهی بلاک شود پاک کن یا با # شروع کن.\n"
        + "".join(f"{u}    # {t} — {c} آگهی خودرو\n" for u, t, c in suspects),
        encoding="utf-8",
    )
    print(f"\n🚫 {len(suspects)} کانال مشکوک پیدا شد و در {SUSPECTS_FILE} نوشته شد.", flush=True)
    return [u for u, _, _ in suspects]


def block(conn: sqlite3.Connection, usernames: list[str], reason: str = "admin: غیرخودرویی") -> None:
    done = 0
    for raw in usernames:
        username = raw.strip().lstrip("@")
        if not username:
            continue
        block_channel(conn, username, reason)
        ch = get_channel_by_username(conn, username)
        if ch is not None:
            deleted = delete_ads_for_channel(conn, ch["id"])
            conn.execute("UPDATE channels SET active = 0 WHERE id = ?", (ch["id"],))
            conn.commit()
            print(f"  🚫 {username} ({ch['title'] or '-'}) بلاک شد؛ {deleted} آگهی پاک شد.", flush=True)
        else:
            print(f"  🚫 {username} بلاک شد (در لیست پایش نبود).", flush=True)
        done += 1
    print(f"✅ {done} کانال بلاک شد. جمع‌کننده در چرخه‌ی بعدی (حداکثر ۳۰ ثانیه) از آن‌ها خارج می‌شود.", flush=True)


def read_file(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line.split()[0])
    return out


def list_blocked(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT username, reason, blocked_at FROM blocked_channels ORDER BY blocked_at DESC").fetchall()
    print(f"🚫 {len(rows)} کانال بلاک‌شده:", flush=True)
    for r in rows:
        print(f"  {r['username']}  — {r['reason'] or '-'} ({r['blocked_at']})", flush=True)


async def _main(args) -> None:
    load_dotenv()
    conn = connect(Path(os.getenv("RUBIKA_DATABASE_PATH", "data/rubikaonline.sqlite3")))
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS rubika_peers (username TEXT PRIMARY KEY, guid TEXT, kind TEXT NOT NULL DEFAULT 'channel', "
        "last_id INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);"
    )
    if args.list:
        list_blocked(conn)
        return
    if args.unblock:
        for u in args.unblock:
            unblock_channel(conn, u)
            print(f"✅ {u} از بلاک خارج شد (برای پایش دوباره، دوباره اضافه‌اش کن).", flush=True)
        return
    if args.suggest:
        account = RubikaAccount(Path(os.getenv("RUBIKA_SESSION", "data/rubika")))
        await account.connect()
        try:
            await suggest(conn, account)
        finally:
            await account.disconnect()
        return
    names = list(args.usernames)
    if args.file:
        names += read_file(Path(args.file))
    if not names:
        print("یوزرنیمی داده نشد. --suggest یا --file یا یوزرنیم‌ها را بده.", flush=True)
        return
    block(conn, names)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("rubpy").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("usernames", nargs="*")
    parser.add_argument("--suggest", action="store_true")
    parser.add_argument("--file")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--unblock", nargs="+")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
