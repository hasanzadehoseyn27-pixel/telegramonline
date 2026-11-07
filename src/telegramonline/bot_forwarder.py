"""ارسال کپیِ آگهی‌ها به گروه‌های تلگرام با یک یا چند ربات (Bot API).

چرا ربات؟ فوروارد خودکار با اکانت‌های شخصی توسط ضد اسپم تلگرام محدود می‌شد.
اکانت‌های جمع‌آوری فقط می‌خوانند؛ نوشتن در گروه‌ها با ربات انجام می‌شود.

هر گروه مقصد یک صف مشترک دارد و به تعداد توکن‌ها «کارگر» (هر کارگر = یک ربات).
هر ربات مستقل از بقیه با فاصله‌ی خودش می‌فرسته، پس ظرفیت تقریباً = تعداد ربات‌ها ×
حدود ۱۸ پیام در دقیقه. ربات خراب/غیرعضو فقط خودش کنار می‌ره و بقیه ادامه می‌دن.
"""
from __future__ import annotations

import asyncio
from typing import Sequence

import httpx

SEND_INTERVAL_SECONDS = 3.2   # ~18 پیام در دقیقه برای هر ربات در هر گروه
MAX_QUEUE_SIZE = 5000         # اگه صف پر شد، قدیمی‌ترین‌ها دور ریخته می‌شن
MAX_TEXT_LEN = 4000           # سقف تلگرام ۴۰۹۶ کاراکتره

_queues: dict[str, asyncio.Queue] = {}
_tasks: list[asyncio.Task] = []
# بعد از ارسال موفق صدا زده می‌شود: (key, شناسه‌ی ربات, شناسه‌ی پیام در گروه)
# تا بعداً با ویرایش/حذف پست در کانال، همان پیام گروه ویرایش/حذف شود.
_on_sent = None


def set_sent_callback(fn) -> None:
    global _on_sent
    _on_sent = fn


def _normalize_chat(chat: str) -> str:
    chat = chat.strip()
    if chat.startswith("https://t.me/"):
        chat = chat[len("https://t.me/"):]
    if chat and not chat.startswith("@") and not chat.lstrip("-").isdigit():
        chat = "@" + chat
    return chat


def _short(token: str) -> str:
    return token.split(":", 1)[0]


async def _worker(token: str, chat: str, queue: asyncio.Queue) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    tag = f"ربات {_short(token)}"
    async with httpx.AsyncClient(timeout=30) as http:
        while True:
            item = await queue.get()
            text, key = item if isinstance(item, tuple) else (item, None)
            sent = False
            for _ in range(3):
                try:
                    resp = await http.post(
                        url,
                        json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"⚠️ {tag} → {chat}: {type(exc).__name__}: {exc}", flush=True)
                    await asyncio.sleep(3)
                    continue
                if resp.status_code == 200:
                    sent = True
                    if key is not None and _on_sent is not None:
                        try:
                            mid = int(resp.json()["result"]["message_id"])
                            _on_sent(key, _short(token), mid)
                        except Exception as exc:  # noqa: BLE001
                            print(f"⚠️ ثبت شناسه‌ی پیام گروه نشد: {exc}", flush=True)
                    break
                try:
                    data = resp.json()
                except Exception:  # noqa: BLE001
                    data = {}
                desc = data.get("description", resp.text[:200])
                if resp.status_code == 429:
                    retry = int(data.get("parameters", {}).get("retry_after", 5))
                    print(f"⏳ {tag} برای {chat} باید {retry} ثانیه صبر کند.", flush=True)
                    await asyncio.sleep(retry + 1)
                    continue
                if resp.status_code in (401, 403) or (resp.status_code == 400 and "chat not found" in desc.lower()):
                    # این ربات نمی‌تونه توی این گروه بنویسه (توکن باطل / عضو نیست / کیک شده):
                    # پیام رو برای ربات‌های دیگه برمی‌گردونیم و همین کارگر کنار می‌ره.
                    print(f"⚠️ {tag} کنار رفت ({resp.status_code}): {desc}", flush=True)
                    queue.put_nowait((text, key))
                    return
                print(f"⚠️ ارسال {tag} به {chat} ناموفق بود ({resp.status_code}): {desc}", flush=True)
                break
            if not sent:
                pass  # پیام بد/غیرقابل ارسال دور ریخته می‌شه تا صف گیر نکنه
            await asyncio.sleep(SEND_INTERVAL_SECONDS)


def build_message(title: str, source_url: str, body: str) -> str:
    """پیام HTML: بالا «Forwarded from <اسم کانال>» (لینک به پیام اصلی) و زیرش متن آگهی."""
    import html

    body = html.escape(body.strip())[: MAX_TEXT_LEN - 300]
    head = f'📨 <a href="{html.escape(source_url, quote=True)}">Forwarded from {html.escape(title)}</a>'
    return f"{head}\n\n{body}"


def enqueue(tokens: str | Sequence[str], chat: str, text: str, key=None) -> None:
    """پیام (HTML) را در صف گروه می‌گذارد (غیر مسدودکننده). اگه توکن/گروه خالی باشه کاری نمی‌کنه."""
    if isinstance(tokens, str):
        tokens = [tokens]
    tokens = [t for t in tokens if t]
    if not tokens or not chat or not text:
        return
    chat = _normalize_chat(chat)
    queue = _queues.get(chat)
    if queue is None:
        queue = asyncio.Queue()
        _queues[chat] = queue
        for token in tokens:
            _tasks.append(asyncio.create_task(_worker(token, chat, queue)))
        print(f"🤖 {len(tokens)} ربات برای ارسال به {chat} فعال شد.", flush=True)
    if queue.qsize() >= MAX_QUEUE_SIZE:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait((text, key))


def _token_for(tokens: str | Sequence[str], bot_id: str) -> str | None:
    if isinstance(tokens, str):
        tokens = [tokens]
    return next((t for t in tokens if t and _short(t) == str(bot_id)), None)


async def _call(token: str, method: str, payload: dict) -> tuple[bool, str]:
    async with httpx.AsyncClient(timeout=30) as http:
        for _ in range(3):
            try:
                resp = await http.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)
            except Exception as exc:  # noqa: BLE001
                await asyncio.sleep(3)
                last = f"{type(exc).__name__}: {exc}"
                continue
            try:
                data = resp.json()
            except Exception:  # noqa: BLE001
                data = {}
            if resp.status_code == 200:
                return True, ""
            if resp.status_code == 429:
                await asyncio.sleep(int(data.get("parameters", {}).get("retry_after", 5)) + 1)
                last = "429"
                continue
            return False, data.get("description", resp.text[:200])
    return False, last


async def _edit_or_delete(tokens, chat: str, bot_id: str, message_id: int, text: str | None) -> None:
    token = _token_for(tokens, bot_id)
    if token is None:
        return
    chat = _normalize_chat(chat)
    if text is None:
        ok, err = await _call(token, "deleteMessage", {"chat_id": chat, "message_id": message_id})
        what = "حذف"
    else:
        ok, err = await _call(
            token,
            "editMessageText",
            {"chat_id": chat, "message_id": message_id, "text": text, "parse_mode": "HTML",
             "disable_web_page_preview": True},
        )
        what = "ویرایش"
        if not ok and "not modified" in err.lower():
            ok = True
    if not ok:
        print(f"⚠️ {what} پیام {message_id} در {chat} نشد: {err}", flush=True)


def edit(tokens, chat: str, bot_id: str, message_id: int, text: str) -> None:
    """پیامی را که قبلاً ربات در گروه گذاشته با متن تازه ویرایش می‌کند (غیر مسدودکننده)."""
    _tasks.append(asyncio.create_task(_edit_or_delete(tokens, chat, bot_id, message_id, text)))


def delete(tokens, chat: str, bot_id: str, message_id: int) -> None:
    """پیامی را که قبلاً ربات در گروه گذاشته پاک می‌کند (غیر مسدودکننده)."""
    _tasks.append(asyncio.create_task(_edit_or_delete(tokens, chat, bot_id, message_id, None)))
