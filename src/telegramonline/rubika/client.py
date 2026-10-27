"""اتصال اکانت روبیکا (rubpy) — همان آداپتوری که ربات فوروارد روبیکا
(ریپوی forwards، bestrobot/rubika.py) استفاده می‌کند، به‌اضافه‌ی چند متد برای
جمع‌کننده: عضو شدن در کانال/گروه، اطلاعات کانال، و آپدیت چت‌ها.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace



log = logging.getLogger(__name__)

RUBIKA_BOT_API = "https://botapi.rubika.ir/v3"
# بزرگ‌تر از هر شناسه‌ی پیام روبیکا (حدود 1.95e18) و کوچک‌تر از سقف int64
_TOP_MESSAGE_ID = "9000000000000000000"
_GUID_RE = re.compile(r"^[cgub]0[A-Za-z0-9]{20,}$")
_FORWARD_CHUNK = 50


def is_guid(value: str) -> bool:
    return bool(_GUID_RE.match(value.strip()))


def load_rubika_tokens(path: Path) -> list[str]:
    """هر خط یک توکن ربات روبیکا (بدون «:»). خط خالی و # نادیده گرفته می‌شود.
    فرمت «نام=توکن» و «توکن  # توضیح» هم قبول است."""
    if not path.exists():
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            line = line.split("=", 1)[1].strip()
        if not line:
            continue
        line = line.split()[0]
        if len(line) < 20 or line in seen:
            continue
        seen.add(line)
        tokens.append(line)
    return tokens


# ======================================================================
#                              اکانت روبیکا
# ======================================================================


@dataclass
class RubikaMessage:
    """شبیه پیام Telethon، فقط فیلدهایی که موتور لازم دارد."""

    id: int
    date: datetime | None
    text: str
    sticker: object | None
    has_strike: bool
    raw: dict

    @property
    def entities(self) -> list:
        return []


def parse_message(raw: dict) -> RubikaMessage | None:
    try:
        mid = int(raw.get("message_id"))
    except (TypeError, ValueError):
        return None
    date = None
    try:
        ts = int(raw.get("time") or 0)
        if ts:
            date = datetime.fromtimestamp(ts, tz=timezone.utc)
    except (TypeError, ValueError):
        date = None
    mtype = str(raw.get("type") or "")
    sticker = raw.get("sticker")
    if sticker is None and mtype == "Sticker":
        sticker = True
    # پیام‌های سیستمی (ساخت کانال، پین و ...) قابل فوروارد نیستند؛ مثل استیکر رد می‌شوند
    if sticker is None and (mtype == "Event" or raw.get("event_data")):
        sticker = "event"
    parts = ((raw.get("metadata") or {}).get("meta_data_parts")) or []
    has_strike = any(str(p.get("type") or "").lower() == "strike" for p in parts if isinstance(p, dict))
    return RubikaMessage(
        id=mid,
        date=date,
        text=str(raw.get("text") or ""),
        sticker=sticker,
        has_strike=has_strike,
        raw=raw,
    )


class RubikaFlood(Exception):
    """روبیکا گفته درخواست زیاد است (TOO_REQUESTS)؛ چند ثانیه صبر لازم است."""

    def __init__(self, seconds: int = 60) -> None:
        super().__init__(f"TOO_REQUESTS — {seconds}s")
        self.seconds = seconds


def _flood_error(seconds: int = 60):
    return RubikaFlood(seconds)


_FloodWait = RubikaFlood


def _find(obj, keys: list[str]):
    """اولین مقدارِ یکی از کلیدها، در هر عمقی از dict/list."""
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]
        values = obj.values()
    elif isinstance(obj, list):
        values = obj
    else:
        return None
    for value in values:
        if isinstance(value, (dict, list)):
            found = _find(value, keys)
            if found not in (None, ""):
                return found
    return None


class RubikaAccount:
    """اکانت روبیکا با همان متدهایی که موتور و پنل از TelegramClient صدا می‌زنند."""

    def __init__(self, session_path: Path) -> None:
        from rubpy import Client

        self.session_path = session_path
        self.client = Client(name=str(session_path))
        self.guid: str = ""
        self._peer_cache: dict[str, str] = {}
        self._title_cache: dict[str, str] = {}
        # آخرین شناسه‌ی پیام هر چت، از getChats/getChatsUpdates (بدون getChannelInfo)
        self._last_ids: dict[str, int] = {}
        # فاصله‌ی حداقل بین درخواست‌ها تا روبیکا TOO_REQUESTS ندهد
        self.min_gap = float(os.getenv("RUBIKA_MIN_GAP_SECONDS", "0.8") or 0.8)
        self._next_call = 0.0
        self._call_lock = asyncio.Lock()
        # متدی که تازه محدودیت گرفته تا مدتی اصلاً فرستاده نمی‌شود (ارسال دوباره
        # فقط محدودیت را طولانی‌تر می‌کند)
        self._cooldown: dict[str, float] = {}

    # ------------------------------------------------------------ lifecycle

    async def connect(self) -> None:
        """بدون هیچ سؤالی (برای PM2): اگر سشن نباشد خطا می‌دهد."""
        from Crypto.PublicKey import RSA
        from Crypto.Signature import pkcs1_15
        from rubpy import exceptions
        from rubpy.crypto import Crypto

        c = self.client
        await c.connect()
        if not c.auth or not c.private_key:
            raise RuntimeError("سشن روبیکا آماده نیست. اول اجرا کن: python -m bestrobot login")
        c.decode_auth = Crypto.decode_auth(c.auth)
        c.import_key = pkcs1_15.new(RSA.import_key(c.private_key.encode()))
        try:
            me = await c.builder("getUserInfo", input={}, dict=True)
        except exceptions.NotRegistered as exc:
            raise RuntimeError("سشن روبیکا باطل شده. دوباره اجرا کن: python -m bestrobot login") from exc
        self.guid = str(_find(me, ["user_guid"]) or c.guid or "")
        c.guid = self.guid

    async def disconnect(self) -> None:
        try:
            await self.client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    async def _call(self, method: str, data: dict) -> dict:
        from rubpy import exceptions

        until = self._cooldown.get(method, 0.0)
        if until > time.monotonic():
            raise _flood_error(max(5, int(until - time.monotonic())))
        async with self._call_lock:
            wait = self._next_call - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._next_call = time.monotonic() + self.min_gap
        try:
            result = await self.client.builder(method, input=data, dict=True)
        except exceptions.TooRequests as exc:
            detail = str(getattr(exc, "message", "") or exc)
            if "TOO_REQUEST" not in detail.upper():
                # rubpy خطاهای دیگر (مثل INVALID_AUTH برای ورودی نامعتبر) را هم با
                # همین کلاس می‌دهد؛ آن‌ها محدودیت نیستند و نباید ۶۰ ثانیه منتظر بمانیم
                raise RuntimeError(f"{method}: {detail}") from exc
            log.warning("روبیکا برای %s محدودیت داد (TOO_REQUESTS).", method)
            self._cooldown[method] = time.monotonic() + 60
            raise _flood_error(60) from exc
        return result or {}

    async def get_me(self):
        info = await self._call("getUserInfo", {})
        user = info.get("user") or {}
        guid = str(user.get("user_guid") or self.guid)
        self.guid = guid
        return SimpleNamespace(
            id=guid,
            username=user.get("username") or "",
            first_name=user.get("first_name") or "",
            last_name=user.get("last_name") or "",
        )

    # ---------------------------------------------------------------- peers

    async def get_peer_id(self, peer: str) -> str:
        """@username / username / https://rubika.ir/username /
        https://rubika.ir/joing/HASH / joinc/HASH / guid ← guid"""
        raw = str(peer).strip()
        if not raw:
            raise ValueError("آدرس خالی است")
        if is_guid(raw):
            return raw
        cached = self._peer_cache.get(raw)
        if cached:
            return cached

        guid = ""
        title = ""
        link = re.search(r"rubika\.ir/(joing|joinc)/([A-Za-z0-9]+)", raw, re.IGNORECASE)
        if link:
            kind, hash_link = link.group(1).lower(), link.group(2)
            if kind == "joing":
                res = await self._call("groupPreviewByJoinLink", {"hash_link": hash_link})
                guid = str(_find(res, ["group_guid"]) or "")
                title = str(_find(res, ["group_title"]) or "")
            else:
                res = await self._call("channelPreviewByJoinLink", {"hash_link": hash_link})
                guid = str(_find(res, ["channel_guid"]) or "")
                title = str(_find(res, ["channel_title"]) or "")
            if not guid:
                raise ValueError(f"لینک {raw} معتبر نیست یا منقضی شده")
        else:
            username = raw
            m = re.search(r"rubika\.ir/([A-Za-z0-9_]+)", raw, re.IGNORECASE)
            if m:
                username = m.group(1)
            username = username.lstrip("@").strip("/")
            res = await self._call("getObjectByUsername", {"username": username})
            if res.get("exist") is False:
                # همان متن خطای Telethon تا موتور مبدا را خودکار خاموش کند
                raise ValueError(f'No user has "{username}" as username')
            guid = str(_find(res, ["channel_guid", "group_guid", "bot_guid", "user_guid", "object_guid"]) or "")
            title = str(_find(res, ["channel_title", "group_title", "bot_title", "first_name"]) or "")
            if not guid:
                raise ValueError(f'No user has "{username}" as username')
        self._peer_cache[raw] = guid
        if title:
            self._title_cache[guid] = title
        return guid

    async def get_entity(self, peer: str):
        guid = await self.get_peer_id(peer)
        title = self._title_cache.get(guid, "")
        if not title:
            try:
                info = await self._info(guid)
                title = str(_find(info, ["channel_title", "group_title", "bot_title", "title", "first_name"]) or "")
            except Exception:  # noqa: BLE001
                title = ""
        return SimpleNamespace(id=guid, title=title or None, first_name="", last_name="")

    async def _info(self, guid: str) -> dict:
        if guid.startswith("c0"):
            return await self._call("getChannelInfo", {"channel_guid": guid})
        if guid.startswith("g0"):
            return await self._call("getGroupInfo", {"group_guid": guid})
        if guid.startswith("b0"):
            return await self._call("getBotInfo", {"bot_guid": guid})
        return await self._call("getUserInfo", {"user_guid": guid})

    # ------------------------------------------------------------- messages

    async def _page(self, guid: str, sort: str, anchor: str, limit: int) -> tuple[list[dict], dict]:
        data = {"object_guid": guid, "sort": sort, "limit": str(limit)}
        if sort == "FromMin":
            data["min_id"] = anchor
        else:
            data["max_id"] = anchor
        res = await self._call("getMessages", data)
        msgs = res.get("messages")
        if msgs is None:
            msgs = _find(res, ["messages"]) or []
        return [m for m in msgs if isinstance(m, dict)], res

    async def _top_anchor(self, guid: str) -> str:
        """max_id برای گرفتن جدیدترین پیام‌ها.

        اول عدد خیلی بزرگ (_TOP_MESSAGE_ID) امتحان می‌شود که هیچ درخواست اضافه‌ای
        نمی‌خواهد. قبلاً برای هر کانال در هر دور یک getChannelInfo زده می‌شد و با
        ده‌ها کانال، روبیکا مدام TOO_REQUESTS می‌داد (و عضویت/کشف کانال‌ها هم
        پشت همین محدودیت گیر می‌کرد). فقط اگر سرور عدد بزرگ را قبول نکند، به
        روش قدیمی (آخرین پیام چت + ۱) برمی‌گردیم.
        """
        if getattr(self, "_top_ok", None) is not False:
            return _TOP_MESSAGE_ID
        cached = self._last_ids.get(guid)
        if cached:
            return str(int(cached) + 1)
        try:
            info = await self._info(guid)
            last = _find(info, ["last_message_id"])
            if last:
                return str(int(last) + 1)
        except Exception:  # noqa: BLE001
            pass
        return _TOP_MESSAGE_ID

    async def _first_page(self, guid: str, anchor: str, limit: int) -> tuple[list[dict], dict]:
        """مثل _page با FromMax؛ اگر سرور عدد بزرگ را رد کرد، یک بار با روش قدیمی."""
        if anchor != _TOP_MESSAGE_ID:
            return await self._page(guid, "FromMax", anchor, limit)
        try:
            result = await self._page(guid, "FromMax", anchor, limit)
            if result[0] or getattr(self, "_top_ok", None):
                self._top_ok = True
                return result
            # خالی برگشت و هنوز نمی‌دانیم سرور عدد بزرگ را درست می‌فهمد یا نه:
            # یک بار با آخرین پیام چت مقایسه می‌کنیم
            self._top_ok = False
            fallback = await self._page(guid, "FromMax", await self._top_anchor(guid), limit)
            if fallback[0]:
                log.warning("روبیکا با max_id بزرگ پیامی نداد؛ روش آخرین پیام چت استفاده می‌شود.")
                return fallback
            self._top_ok = None  # کانال واقعاً خالی بود؛ دفعه‌ی بعد دوباره عدد بزرگ
            return result
        except RubikaFlood:
            raise
        except Exception as exc:  # noqa: BLE001
            if getattr(self, "_top_ok", None):
                raise
            log.warning("روبیکا max_id بزرگ را قبول نکرد (%s)؛ روش آخرین پیام چت استفاده می‌شود.", exc)
            self._top_ok = False
            return await self._page(guid, "FromMax", await self._top_anchor(guid), limit)

    async def _latest_desc(self, guid: str, limit: int) -> list[RubikaMessage]:
        """جدیدترین پیام‌ها، از جدید به قدیم."""
        out: list[RubikaMessage] = []
        anchor = await self._top_anchor(guid)
        seen: set[int] = set()
        for _ in range(20):
            batch, _res = await self._first_page(guid, anchor, min(50, max(2, limit - len(out) + 1)))
            msgs = [m for m in (parse_message(b) for b in batch) if m and m.id not in seen]
            if not msgs:
                break
            msgs.sort(key=lambda m: m.id, reverse=True)
            for m in msgs:
                seen.add(m.id)
                out.append(m)
                if len(out) >= limit:
                    return out
            # همان کمترین شناسه (نه یکی کمتر)؛ چه سرور max_id را شامل کند چه نه، چیزی جا نمی‌ماند
            anchor = str(msgs[-1].id)
        return out

    async def _newer_than(self, guid: str, min_id: int) -> list[RubikaMessage]:
        """پیام‌های جدیدتر از min_id، از قدیم به جدید.

        با getMessagesInterval (پیام‌های اطراف min_id) — یک درخواست برای هر دور، بدون
        getChannelInfo. اگر سرور این روش را قبول نکرد، به روش قدیمی برمی‌گردیم.
        """
        if getattr(self, "_interval_ok", None) is not False:
            try:
                return await self._newer_by_interval(guid, int(min_id))
            except _FloodWait:
                raise
            except Exception as exc:  # noqa: BLE001
                if getattr(self, "_interval_ok", None):
                    raise
                log.warning("getMessagesInterval کار نکرد (%s)؛ روش قدیمی استفاده می‌شود.", exc)
                self._interval_ok = False
        return await self._newer_by_paging(guid, int(min_id))

    async def _newer_by_interval(self, guid: str, min_id: int) -> list[RubikaMessage]:
        out: dict[int, RubikaMessage] = {}
        middle = min_id
        for _ in range(20):
            res = await self._call(
                "getMessagesInterval", {"object_guid": guid, "middle_message_id": str(middle)}
            )
            batch = res.get("messages")
            if batch is None:
                batch = _find(res, ["messages"]) or []
            msgs = [m for m in (parse_message(b) for b in batch if isinstance(b, dict)) if m]
            newer = [m for m in msgs if m.id > min_id and m.id not in out]
            for m in newer:
                out[m.id] = m
            self._interval_ok = True
            if not newer or not res.get("new_has_continue"):
                break
            middle = max(m.id for m in newer)
        return [out[k] for k in sorted(out)]

    async def _newer_by_paging(self, guid: str, min_id: int) -> list[RubikaMessage]:
        """روش قدیمی: از جدیدترین پیام به عقب ورق می‌زنیم تا به min_id برسیم."""
        out: dict[int, RubikaMessage] = {}
        anchor = await self._top_anchor(guid)
        for _ in range(10):
            batch, _res = await self._first_page(guid, anchor, 50)
            msgs = [m for m in (parse_message(b) for b in batch) if m]
            if not msgs:
                break
            reached = False
            for m in msgs:
                if m.id > min_id:
                    out[m.id] = m
                else:
                    reached = True
            lowest = min(m.id for m in msgs)
            if reached or lowest <= min_id:
                break
            anchor = str(lowest)
        return [out[k] for k in sorted(out)]

    async def iter_messages(self, peer: str, limit: int | None = None, min_id: int | None = None, reverse: bool = False):
        guid = await self.get_peer_id(peer)
        if min_id is not None:
            msgs = await self._newer_than(guid, int(min_id))
            if not reverse:
                msgs = list(reversed(msgs))
            if limit:
                msgs = msgs[:limit]
        else:
            msgs = await self._latest_desc(guid, int(limit or 100))
            if reverse:
                msgs = list(reversed(msgs))
        for m in msgs:
            yield m

    async def get_messages(self, peer: str, limit: int = 1) -> list[RubikaMessage]:
        guid = await self.get_peer_id(peer)
        return await self._latest_desc(guid, int(limit))

    async def forward_messages(self, entity: str, messages, from_peer: str):
        """مثل Telethon: برای هر پیام یک مقدار (None یعنی فوروارد نشد)."""
        ids = messages if isinstance(messages, list) else [messages]
        to_guid = await self.get_peer_id(str(entity))
        from_guid = await self.get_peer_id(str(from_peer))
        results: list = []
        for start in range(0, len(ids), _FORWARD_CHUNK):
            chunk = [str(int(i)) for i in ids[start : start + _FORWARD_CHUNK]]
            await self._call(
                "forwardMessages",
                {
                    "from_object_guid": from_guid,
                    "to_object_guid": to_guid,
                    "message_ids": chunk,
                    "rnd": int(time.time() * 1000) % 10_000_000 + 1,
                },
            )
            results.extend([True] * len(chunk))
        return results if isinstance(messages, list) else results[0]

    async def send_message(self, peer: str, text: str):
        guid = await self.get_peer_id(str(peer))
        return await self._call(
            "sendMessage",
            {"object_guid": guid, "text": text, "rnd": int(time.time() * 1000) % 10_000_000 + 1},
        )


    # ------------------------------------------------------------ collector

    async def get_chats_updates(self, state: int | None) -> tuple[list[dict], int | None]:
        """چت‌هایی که از state به بعد پیام تازه دارند + state جدید."""
        data = {"state": int(state if state is not None else time.time() - 150)}
        res = await self._call("getChatsUpdates", data)
        chats = [c for c in (res.get("chats") or []) if isinstance(c, dict)]
        self._remember_chats(chats)
        new_state = res.get("new_state")
        try:
            new_state = int(new_state) if new_state is not None else None
        except (TypeError, ValueError):
            new_state = None
        return chats, new_state

    def _remember_chats(self, chats: list[dict]) -> None:
        for chat in chats:
            guid = str(chat.get("object_guid") or (chat.get("abs_object") or {}).get("object_guid") or "")
            last = chat.get("last_message_id") or (chat.get("last_message") or {}).get("message_id")
            try:
                last = int(last)
            except (TypeError, ValueError):
                continue
            if guid and last > self._last_ids.get(guid, 0):
                self._last_ids[guid] = last

    async def prime_last_ids(self, pages: int = 40) -> int:
        """آخرین پیام همه‌ی چت‌ها با چند getChats (به‌جای یک getChannelInfo برای هر کانال)."""
        start_id = None
        for _ in range(pages):
            res = await self._call("getChats", {"start_id": start_id} if start_id else {})
            self._remember_chats([c for c in (res.get("chats") or []) if isinstance(c, dict)])
            start_id = res.get("next_start_id")
            if not res.get("has_continue") or not start_id:
                break
        return len(self._last_ids)

    async def channel_info(self, guid: str) -> dict:
        """{guid, username, title} برای کانال/گروه."""
        info = await self._info(guid)
        last = _find(info, ["last_message_id"])
        try:
            if last and int(last) > self._last_ids.get(guid, 0):
                self._last_ids[guid] = int(last)
        except (TypeError, ValueError):
            pass
        return {
            "guid": guid,
            "username": str(_find(info, ["username"]) or ""),
            "title": str(_find(info, ["channel_title", "group_title", "title"]) or ""),
            "about": str(_find(info, ["description"]) or ""),
        }

    async def join_channel(self, guid: str) -> None:
        await self._call("joinChannelAction", {"channel_guid": guid, "action": "Join"})

    async def leave_channel(self, guid: str) -> None:
        await self._call("joinChannelAction", {"channel_guid": guid, "action": "Remove"})

    async def join_group_link(self, link: str) -> str:
        hash_link = link.rstrip("/").split("/")[-1]
        res = await self._call("joinGroup", {"hash_link": hash_link})
        return str(_find(res, ["group_guid"]) or "")

    async def new_messages(self, guid: str, min_id: int) -> list[RubikaMessage]:
        """پیام‌های جدیدتر از min_id، از قدیم به جدید."""
        return await self._newer_than(guid, int(min_id))

    async def latest(self, guid: str, limit: int) -> list[RubikaMessage]:
        """جدیدترین پیام‌ها، از جدید به قدیم."""
        return await self._latest_desc(guid, int(limit))
