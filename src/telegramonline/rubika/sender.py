"""گذاشتن آگهی‌های روبیکا در گروه روبیکا با ربات‌ها — هم‌ارز bot_forwarder.py تلگرام.

هر آگهیِ تازه با سرتیتر «📨 فورواردشده از <اسم کانال>» و لینک کانال، با
sendMessage در گروه مقصد گذاشته می‌شود. چند ربات از یک صف مشترک می‌خوانند تا
ظرفیت بالا برود؛ رباتی که اجازه ندارد (ادمین گروه نیست) فقط خودش کنار می‌رود.

⚠️ در روبیکا ربات فقط وقتی می‌تواند در گروه پیام بگذارد که «ادمین» آن گروه
باشد (تست‌شده: عضو عادی ← INVALID_ACCESS).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

API = "https://botapi.rubika.ir/v3"
SEND_INTERVAL_SECONDS = 3.0
MAX_QUEUE_SIZE = 5000
MAX_TEXT_LEN = 3900

_queue: asyncio.Queue | None = None
_tasks: list[asyncio.Task] = []
_chat = ""


def load_tokens(path: str | Path) -> list[str]:
    """هر خط یک توکن ربات روبیکا. خط خالی/# نادیده؛ «نام=توکن» هم قبول است."""
    p = Path(path)
    if not p.exists():
        return []
    tokens: list[str] = []
    for raw in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            line = line.split("=", 1)[1].strip()
        line = line.split()[0] if line else ""
        if len(line) >= 20 and line not in tokens:
            tokens.append(line)
    return tokens


def build_message(title: str, link: str, body: str) -> str:
    body = (body or "").strip()[: MAX_TEXT_LEN - 300]
    head = f"📨 فورواردشده از {title}"
    if link:
        head += f"\n🔗 {link}"
    return f"{head}\n\n{body}"


async def _worker(index: int, token: str, queue: asyncio.Queue) -> None:
    tag = f"ربات روبیکا {index}"
    async with httpx.AsyncClient(timeout=30) as http:
        while True:
            text = await queue.get()
            for _ in range(3):
                try:
                    resp = await http.post(f"{API}/{token}/sendMessage", json={"chat_id": _chat, "text": text})
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001
                    print(f"⚠️ {tag}: {type(exc).__name__}: {exc}", flush=True)
                    await asyncio.sleep(3)
                    continue
                status = str(data.get("status") or "")
                if status == "OK":
                    break
                if status in ("TOO_REQUESTS", "TOO_REQUEST"):
                    print(f"⏳ {tag} محدودیت ارسال گرفت؛ ۳۰ ثانیه صبر.", flush=True)
                    await asyncio.sleep(30)
                    continue
                if status == "INVALID_ACCESS":
                    print(f"⚠️ {tag} در گروه {_chat} اجازه‌ی ارسال ندارد (ادمین نیست) و کنار رفت.", flush=True)
                    queue.put_nowait(text)
                    return
                print(f"⚠️ ارسال {tag} ناموفق بود: {status} {data.get('dev_message') or ''}", flush=True)
                break
            await asyncio.sleep(SEND_INTERVAL_SECONDS)


def start(tokens: list[str], chat_id: str) -> bool:
    """کارگرها را روشن می‌کند. اگر توکن یا گروه نباشد، ارسال خاموش می‌ماند."""
    global _queue, _chat
    if not tokens or not chat_id:
        return False
    _chat = chat_id
    _queue = asyncio.Queue()
    for i, token in enumerate(tokens, start=1):
        _tasks.append(asyncio.create_task(_worker(i, token, _queue)))
    print(f"🤖 {len(tokens)} ربات روبیکا برای ارسال در {chat_id} فعال شد.", flush=True)
    return True


def enqueue(text: str) -> None:
    if _queue is None or not text:
        return
    if _queue.qsize() >= MAX_QUEUE_SIZE:
        try:
            _queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    _queue.put_nowait(text)
