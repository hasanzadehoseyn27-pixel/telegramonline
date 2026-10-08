"""ارسال کپیِ آگهی‌ها به گروه‌های تلگرام با یک ربات (Bot API).

چرا ربات؟ فوروارد خودکار با اکانت‌های شخصی (۰۹۱۹ / ۰۹۳۵) توسط ضد اسپم تلگرام
محدود می‌شد. اکانت‌های جمع‌آوری فقط می‌خوانند؛ نوشتن در گروه‌ها با ربات انجام
می‌شود. هر گروه صف مخصوص خودش را دارد و پیام‌ها با فاصله فرستاده می‌شوند تا به
سقف ارسال ربات (حدود ۲۰ پیام در دقیقه برای هر گروه) نخوریم.
"""
from __future__ import annotations

import asyncio

import httpx

SEND_INTERVAL_SECONDS = 3.2   # ~18 پیام در دقیقه برای هر گروه
MAX_QUEUE_SIZE = 500          # اگه صف پر شد، قدیمی‌ترین‌ها دور ریخته می‌شن
MAX_TEXT_LEN = 4000           # سقف تلگرام ۴۰۹۶ کاراکتره (برش متن قبل از ساخت HTML توسط فراخوان انجام می‌شه)

_queues: dict[str, asyncio.Queue] = {}
_tasks: dict[str, asyncio.Task] = {}


def _normalize_chat(chat: str) -> str:
    chat = chat.strip()
    if chat.startswith("https://t.me/"):
        chat = chat[len("https://t.me/"):]
    if chat and not chat.startswith("@") and not chat.lstrip("-").isdigit():
        chat = "@" + chat
    return chat


async def _worker(token: str, chat: str, queue: asyncio.Queue) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=30) as http:
        while True:
            text = await queue.get()
            for attempt in range(3):
                try:
                    resp = await http.post(
                        url,
                        json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                    )
                    if resp.status_code == 429:
                        retry = int(resp.json().get("parameters", {}).get("retry_after", 5))
                        print(f"⏳ ربات برای {chat} باید {retry} ثانیه صبر کند.", flush=True)
                        await asyncio.sleep(retry + 1)
                        continue
                    if resp.status_code != 200:
                        desc = resp.json().get("description", resp.text[:200]) if resp.content else resp.status_code
                        print(f"⚠️ ارسال ربات به {chat} ناموفق بود ({resp.status_code}): {desc}", flush=True)
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"⚠️ ارسال ربات به {chat} خطا داد: {type(exc).__name__}: {exc}", flush=True)
                    await asyncio.sleep(3)
            await asyncio.sleep(SEND_INTERVAL_SECONDS)


def build_message(title: str, source_url: str, body: str) -> str:
    """پیام HTML: بالا «Forwarded from <اسم کانال>» (لینک به پیام اصلی) و زیرش متن آگهی."""
    import html

    body = html.escape(body.strip())[: MAX_TEXT_LEN - 300]
    head = f'📨 <a href="{html.escape(source_url, quote=True)}">Forwarded from {html.escape(title)}</a>'
    return f"{head}\n\n{body}"


def enqueue(token: str, chat: str, text: str) -> None:
    """پیام (HTML) را در صف گروه می‌گذارد (غیر مسدودکننده). اگه توکن/گروه خالی باشه کاری نمی‌کنه."""
    if not token or not chat or not text:
        return
    chat = _normalize_chat(chat)
    queue = _queues.get(chat)
    if queue is None:
        queue = asyncio.Queue()
        _queues[chat] = queue
        _tasks[chat] = asyncio.create_task(_worker(token, chat, queue))
    if queue.qsize() >= MAX_QUEUE_SIZE:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait(text)
