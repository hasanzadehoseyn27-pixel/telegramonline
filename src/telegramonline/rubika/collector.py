"""جمع‌کننده‌ی روبیکا — هم‌ارز collector.py تلگرام، کاملاً جدا از آن.

کار:
  ۱) اکانت روبیکا کانال‌های ثبت‌شده را می‌خواند (عضو هم می‌شود).
  ۲) هر پیام تازه با همان پارسر تلگرام به آگهی تبدیل و در دیتابیس جدای
     روبیکا ذخیره می‌شود.
  ۳) آگهی‌ها به سایت فرستاده می‌شوند (با platform=rubika؛ فقط وقتی
     RUBIKA_PUSH_TO_SITE=1 باشد — تا بک‌اند آماده نشده، خاموش).
  ۴) کپی هر آگهی با ربات‌های روبیکا در گروه RUBIKA_FORWARD_GROUP گذاشته می‌شود.
  ۵) «پیمایش گروه‌ها»: در گروه‌های منبع، هر کانالی که پیامش فوروارد شود
     خودکار پیدا، ثبت و عضو می‌شود.

اجرا (از ریشه‌ی پروژه):
    $env:PYTHONPATH="src"
    py -m telegramonline.rubika.collector

تنظیمات .env:
    RUBIKA_SESSION=data/rubika              # فایل سشن rubpy (بدون .rp)
    RUBIKA_DATABASE_PATH=data/rubikaonline.sqlite3
    RUBIKA_CHANNELS=auto_pedram_alipoor,Khodro_Nezami_00,miss_havaleTehran
    RUBIKA_SOURCE_GROUPS=                   # لینک گروه‌های پیمایش (با کاما)
    RUBIKA_FORWARD_GROUP=g0...              # guid گروه مقصد (یا لینک joing)
    RUBIKA_BOT_TOKENS_FILE=rubika_bot_tokens.txt
    RUBIKA_PUSH_TO_SITE=0
    RUBIKA_POLL_SECONDS=5
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..carx_bridge import ad_row_to_dto, push_ads_async
from ..config import load_dotenv
from ..parser import parse_message_group
from ..storage import (
    add_channel,
    add_source_group,
    connect,
    get_channel_by_username,
    increment_source_group_discovered,
    is_channel_blocked,
    mark_channel_joined,
    mark_source_group_joined,
    purge_old_ads,
)
from . import sender
from .client import RubikaAccount, RubikaFlood, RubikaMessage, is_guid

TEHRAN = timezone(timedelta(hours=3, minutes=30))
DISCOVERY_JOIN_GAP_SECONDS = 30
SWEEP_SECONDS = 60

STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS rubika_peers (
    username TEXT PRIMARY KEY,
    guid TEXT,
    kind TEXT NOT NULL DEFAULT 'channel',
    last_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _csv(name: str) -> list[str]:
    return [p.strip() for p in os.getenv(name, "").replace(";", ",").split(",") if p.strip()]


def _bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _today() -> str:
    return datetime.now(TEHRAN).date().isoformat()


def _local_day(msg: RubikaMessage) -> str:
    if msg.date is None:
        return _today()
    return msg.date.astimezone(TEHRAN).date().isoformat()


def channel_link(username: str) -> str:
    if not username or is_guid(username):
        return ""
    return f"https://rubika.ir/{username}"


class RubikaCollector:
    def __init__(self) -> None:
        load_dotenv()
        self.db_path = Path(os.getenv("RUBIKA_DATABASE_PATH", "data/rubikaonline.sqlite3"))
        self.session = Path(os.getenv("RUBIKA_SESSION", "data/rubika"))
        self.poll_seconds = float(os.getenv("RUBIKA_POLL_SECONDS", "5") or 5)
        self.push_to_site = _bool("RUBIKA_PUSH_TO_SITE")
        self.forward_group = os.getenv("RUBIKA_FORWARD_GROUP", "").strip()
        self.tokens = sender.load_tokens(os.getenv("RUBIKA_BOT_TOKENS_FILE", "rubika_bot_tokens.txt"))
        self.conn: sqlite3.Connection = connect(self.db_path)
        self.conn.executescript(STATE_SCHEMA)
        self.account = RubikaAccount(self.session)
        # guid → (kind, username)
        self.watch: dict[str, tuple[str, str]] = {}
        self.forward_group_guid = ""
        self.state: int | None = None
        self._last_discovery_join = 0.0

    # ---------------------------------------------------------------- state

    def _peer(self, username: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM rubika_peers WHERE username = ?", (username,)).fetchone()

    def _set_peer(self, username: str, guid: str, kind: str, last_id: int | None = None) -> None:
        row = self._peer(username)
        if row is None:
            self.conn.execute(
                "INSERT INTO rubika_peers (username, guid, kind, last_id) VALUES (?, ?, ?, ?)",
                (username, guid, kind, int(last_id or 0)),
            )
        else:
            self.conn.execute(
                "UPDATE rubika_peers SET guid = ?, kind = ?, last_id = COALESCE(?, last_id), updated_at = CURRENT_TIMESTAMP WHERE username = ?",
                (guid, kind, last_id, username),
            )
        self.conn.commit()

    def _set_last(self, username: str, last_id: int) -> None:
        self.conn.execute(
            "UPDATE rubika_peers SET last_id = MAX(last_id, ?), updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (int(last_id), username),
        )
        self.conn.commit()

    # ---------------------------------------------------------------- start

    async def start(self) -> None:
        await self.account.connect()
        me = await self.account.get_me()
        print(f"📱 اکانت روبیکا وصل شد: {me.first_name or me.username} ({me.id})", flush=True)

        for username in _csv("RUBIKA_CHANNELS"):
            if get_channel_by_username(self.conn, username) is None:
                add_channel(self.conn, username)
        for link in _csv("RUBIKA_SOURCE_GROUPS"):
            add_source_group(self.conn, link)

        if self.forward_group:
            try:
                self.forward_group_guid = (
                    self.forward_group if is_guid(self.forward_group) else await self.account.get_peer_id(self.forward_group)
                )
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ گروه مقصد روبیکا پیدا نشد ({exc}) — ارسال در گروه خاموش است.", flush=True)
        if self.forward_group_guid and self.tokens:
            sender.start(self.tokens, self.forward_group_guid)
        else:
            print("ℹ️ ارسال در گروه روبیکا خاموش است (RUBIKA_FORWARD_GROUP یا توکن ربات‌ها تنظیم نشده).", flush=True)
        if not self.push_to_site:
            print("ℹ️ ارسال به سایت خاموش است (RUBIKA_PUSH_TO_SITE=0).", flush=True)
        elif not (os.getenv("CARX_API_URL", "").strip() and os.getenv("CARX_IMPORT_API_KEY", "").strip()):
            print("⚠️ RUBIKA_PUSH_TO_SITE=1 است ولی CARX_API_URL / CARX_IMPORT_API_KEY تنظیم نشده — آگهی‌ها به سایت نمی‌روند.", flush=True)
        else:
            print(f"🌐 ارسال آگهی‌های روبیکا به سایت روشن است: {os.getenv('CARX_API_URL', '').strip()}", flush=True)

        deleted = purge_old_ads(self.conn)
        if deleted:
            print(f"🧹 پاک‌سازی ابتدای اجرا: {deleted} ردیف قدیمی حذف شد.", flush=True)
        await self.sync()
        try:
            _, self.state = await self.account.get_chats_updates(None)
        except Exception:  # noqa: BLE001
            self.state = None

    # ----------------------------------------------------------------- sync

    async def sync(self) -> None:
        """کانال‌ها/گروه‌های تازه را عضو می‌شود و فهرست پایش را به‌روز می‌کند."""
        watch: dict[str, tuple[str, str]] = {}

        rows = self.conn.execute("SELECT * FROM channels WHERE active = 1 ORDER BY added_at").fetchall()
        for ch in rows:
            username = ch["username"]
            try:
                peer = self._peer(username)
                guid = peer["guid"] if peer and peer["guid"] else await self.account.get_peer_id(username)
                if not ch["joined"]:
                    try:
                        await self.account.join_channel(guid)
                    except RubikaFlood:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        # اگر از قبل عضو بوده هم ممکن است خطا بدهد؛ خواندن پیام‌ها را امتحان می‌کنیم
                        print(f"ℹ️ عضویت در {username}: {exc}", flush=True)
                    title = None
                    try:
                        title = (await self.account.channel_info(guid)).get("title") or None
                    except Exception:  # noqa: BLE001
                        pass
                    mark_channel_joined(self.conn, ch["id"], title=title)
                    self._set_peer(username, guid, "channel")
                    inserted = await self.backfill_today(username, guid)
                    print(f"✅ کانال روبیکا فعال شد: {username} ({title or '-'}) — آگهی امروز: {inserted}", flush=True)
                elif peer is None or not peer["guid"]:
                    self._set_peer(username, guid, "channel")
                    await self.backfill_today(username, guid)
                watch[guid] = ("channel", username)
            except RubikaFlood as exc:
                print(f"⏳ روبیکا محدودیت داد؛ ادامه‌ی همگام‌سازی {exc.seconds} ثانیه بعد.", flush=True)
                break
            except ValueError as exc:
                print(f"⚠️ کانال {username} پیدا نشد: {exc}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ خطا در فعال‌سازی کانال {username}: {exc}", flush=True)

        groups = self.conn.execute("SELECT * FROM source_groups WHERE active = 1 ORDER BY added_at").fetchall()
        for grp in groups:
            link = grp["username"]
            try:
                peer = self._peer(link)
                guid = peer["guid"] if peer and peer["guid"] else ""
                if not guid:
                    if "/joing/" in link.lower():
                        try:
                            guid = await self.account.join_group_link(link)
                        except Exception as exc:  # noqa: BLE001
                            print(f"ℹ️ عضویت در گروه {link}: {exc}", flush=True)
                        if not guid:
                            guid = await self.account.get_peer_id(link)
                    else:
                        guid = await self.account.get_peer_id(link)
                    latest = await self.account.latest(guid, 1)
                    self._set_peer(link, guid, "group", latest[0].id if latest else 0)
                if not grp["joined"]:
                    title = None
                    try:
                        title = (await self.account.channel_info(guid)).get("title") or None
                    except Exception:  # noqa: BLE001
                        pass
                    mark_source_group_joined(self.conn, grp["id"], title=title)
                    print(f"✅ گروه پیمایش روبیکا فعال شد: {link} ({title or '-'})", flush=True)
                if guid != self.forward_group_guid:
                    watch[guid] = ("group", link)
            except RubikaFlood as exc:
                print(f"⏳ روبیکا محدودیت داد؛ ادامه‌ی همگام‌سازی {exc.seconds} ثانیه بعد.", flush=True)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ خطا در فعال‌سازی گروه {link}: {exc}", flush=True)

        # کانال‌هایی که از پنل حذف شده‌اند: خروج و پاک‌کردن
        for ch in self.conn.execute("SELECT * FROM channels WHERE active = 0 AND joined = 1").fetchall():
            peer = self._peer(ch["username"])
            if peer and peer["guid"]:
                try:
                    await self.account.leave_channel(peer["guid"])
                except Exception:  # noqa: BLE001
                    pass
            self.conn.execute("DELETE FROM channels WHERE id = ?", (ch["id"],))
            self.conn.execute("DELETE FROM rubika_peers WHERE username = ?", (ch["username"],))
            self.conn.commit()
            print(f"🗑 کانال روبیکا حذف شد: {ch['username']}", flush=True)

        # گروه‌های پیمایشی که از پنل حذف شده‌اند
        for grp in self.conn.execute("SELECT * FROM source_groups WHERE active = 0").fetchall():
            self.conn.execute("DELETE FROM source_groups WHERE id = ?", (grp["id"],))
            self.conn.execute("DELETE FROM rubika_peers WHERE username = ?", (grp["username"],))
            self.conn.commit()
            print(f"🗑 گروه پیمایش روبیکا حذف شد: {grp['username']}", flush=True)

        self.watch = watch

    async def backfill_today(self, username: str, guid: str) -> int:
        """آگهی‌های امروز کانال (حداکثر ۲۰۰ پیام آخر) — مثل backfill_today تلگرام."""
        msgs = await self.account.latest(guid, 200)
        today = _today()
        todays = [m for m in msgs if _local_day(m) == today]
        highest = max((m.id for m in msgs), default=0)
        count = 0
        for msg in sorted(todays, key=lambda m: m.id):
            count += await self.handle_channel_message(username, msg, live=False)
        self._set_last(username, highest)
        return count

    # ----------------------------------------------------------------- live

    async def poll_once(self, full: bool = False) -> None:
        targets: set[str] = set()
        if full or self.state is None:
            targets = set(self.watch)
        else:
            chats, new_state = await self.account.get_chats_updates(self.state)
            if new_state:
                self.state = new_state
            for chat in chats:
                guid = str(chat.get("object_guid") or "")
                if guid in self.watch:
                    targets.add(guid)
        for guid in targets:
            kind, username = self.watch[guid]
            peer = self._peer(username)
            last_id = int(peer["last_id"]) if peer else 0
            try:
                msgs = await self.account.new_messages(guid, last_id) if last_id else await self.account.latest(guid, 1)
            except RubikaFlood:
                raise
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ خواندن {username} نشد: {exc}", flush=True)
                continue
            if not last_id:
                if msgs:
                    self._set_last(username, msgs[0].id)
                continue
            for msg in msgs:
                try:
                    if kind == "group":
                        await self.discover_from_group(username, msg)
                    else:
                        await self.handle_channel_message(username, msg, live=True)
                except RubikaFlood:
                    raise
                except Exception:  # noqa: BLE001
                    print(f"❌ خطا در پردازش پیام {msg.id} از {username}:", flush=True)
                    traceback.print_exc()
                self._set_last(username, msg.id)

    async def handle_channel_message(self, username: str, msg: RubikaMessage, live: bool) -> int:
        if msg.sticker is not None or not (msg.text or "").strip():
            return 0
        if _local_day(msg) != _today():
            return 0
        channel = get_channel_by_username(self.conn, username)
        if channel is None or not channel["active"]:
            return 0
        ads = parse_message_group(str(msg.id), msg.text, msg.date, source="live" if live else "backfill")
        saved = save_rubika_ads(self.conn, ads, channel["id"], username)
        relevant = [a for a in saved if a["status"] in ("sale", "buyer", "call_price")]
        if live:
            preview = " ".join((msg.text or "").split())[:50]
            if not saved:
                print(f"📩 [{username}] پیام {msg.id}: تکراری بود (همین متن امروز قبلاً آمده) — رد شد | {preview}", flush=True)
            elif not relevant:
                print(f"📩 [{username}] پیام {msg.id}: آگهی خودرو تشخیص داده نشد — رد شد | {preview}", flush=True)
            else:
                print(f"📩 [{username}] پیام {msg.id}: {len(relevant)} آگهی ← گروه روبیکا | {preview}", flush=True)
        if not relevant:
            return 0
        title = (channel["title"] or "").strip() or username
        if self.push_to_site:
            dtos = []
            for row in relevant:
                dto = ad_row_to_dto(row, channel_titles={username: title})
                dto["telegramSourceId"] = "rb:" + dto["telegramSourceId"]
                dto["platform"] = "rubika"
                dto["channelLink"] = channel_link(username)
                dtos.append(dto)
            await push_ads_async(dtos)
        if live:
            sender.enqueue(sender.build_message(title, channel_link(username), msg.text))
        return len(relevant)

    async def discover_from_group(self, group_link: str, msg: RubikaMessage) -> None:
        fwd = msg.raw.get("forwarded_from") or {}
        if str(fwd.get("type_from") or "") != "Channel":
            return
        guid = str(fwd.get("object_guid") or "")
        if not guid or guid in self.watch:
            return
        info = await self.account.channel_info(guid)
        username = info.get("username") or guid
        if is_channel_blocked(self.conn, username) or get_channel_by_username(self.conn, username) is not None:
            return
        channel_id = add_channel(self.conn, username, title=info.get("title") or None)
        if channel_id is None:
            return
        self._set_peer(username, guid, "channel")
        increment_source_group_discovered(self.conn, group_link)
        print(f"🔎 کانال روبیکای تازه از گروه پیمایش پیدا شد: {username} ({info.get('title') or '-'})", flush=True)
        # عضویت سریع با فاصله؛ بقیه در sync بعدی
        if time.monotonic() - self._last_discovery_join >= DISCOVERY_JOIN_GAP_SECONDS:
            self._last_discovery_join = time.monotonic()
            await self.sync()

    # ----------------------------------------------------------------- run

    async def run(self) -> None:
        await self.start()
        print(f"📡 روبیکا: در حال پایش {len(self.watch)} کانال/گروه.", flush=True)
        last_sync = last_sweep = time.monotonic()
        last_purge_day = _today()
        while True:
            try:
                now = time.monotonic()
                full = now - last_sweep >= SWEEP_SECONDS
                await self.poll_once(full=full)
                if full:
                    last_sweep = now
                if now - last_sync >= 30:
                    await self.sync()
                    last_sync = now
                if _today() != last_purge_day:
                    last_purge_day = _today()
                    deleted = purge_old_ads(self.conn)
                    print(f"🧹 پاک‌سازی شبانه‌ی روبیکا: {deleted} ردیف.", flush=True)
            except RubikaFlood as exc:
                print(f"⏳ روبیکا محدودیت داد؛ {exc.seconds} ثانیه صبر.", flush=True)
                await asyncio.sleep(exc.seconds)
            except Exception:  # noqa: BLE001
                print("❌ خطای غیرمنتظره در جمع‌کننده‌ی روبیکا:", flush=True)
                traceback.print_exc()
                await asyncio.sleep(5)
            await asyncio.sleep(self.poll_seconds)


def save_rubika_ads(conn: sqlite3.Connection, ads, channel_id: int, username: str):
    from ..storage import save_ads

    return save_ads(conn, ads, channel_id=channel_id, channel_username=username)


async def run_forever() -> None:
    backoff = 5
    while True:
        try:
            await RubikaCollector().run()
        except Exception as exc:  # noqa: BLE001
            print(f"❌ جمع‌کننده‌ی روبیکا متوقف شد: {exc}؛ {backoff} ثانیه دیگر دوباره.", flush=True)
            traceback.print_exc()
        await asyncio.sleep(backoff)


def main() -> None:
    import logging
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("rubpy").setLevel(logging.WARNING)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
