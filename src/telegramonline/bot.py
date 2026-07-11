from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from itertools import count

import jdatetime
from telethon import Button, TelegramClient, events

from .config import Settings
from .net import parse_proxy_from_env, resolve_chat_id
from .parser import parse_message_group
from .query import format_price
from .storage import (
    add_user_vehicle,
    connect,
    count_search_results,
    get_user_vehicle,
    list_user_vehicles,
    remove_user_vehicle,
    save_ads,
    search_priced_ads,
    search_today_ads,
    search_unpriced_ads,
    stats,
)

# یوزرنیم عمومی گروه — برای ساخت لینک مستقیم به هر پیام (t.me/<username>/<id>).
# این لینک فقط برای آگهی‌هایی درست کار می‌کند که source == 'live' باشد، چون
# شماره پیام آگهی‌های ایمپورت‌شده از فایل export، شماره واقعی تلگرام نیست.
GROUP_USERNAME = "BAZARBOZORGEKHODROIRAN"

PAGE_SIZE = 10

WELCOME = """
🚗 telegramonline آماده است.

▫️ اسم هر ماشینی را تایپ کن تا همین الان جست‌وجو شود.
▫️ یا از «➕ افزودن ماشین» به لیست خودت اضافه کن تا همیشه با یک دکمه جست‌وجو شود.

نتیجه‌ها در سه تب می‌آیند:
💰 ۱۰ ارزان‌ترین با قیمت
❓ بدون قیمت (همه، با صفحه‌بندی)
📅 همه آگهی‌های امروز (همه، با صفحه‌بندی)
""".strip()

# کوئری‌های جست‌وجوی آزاد (متنی که کاربر تایپ کرده) — callback تلگرام فقط ۶۴ بایت
# جا دارد، پس متن فارسی را اینجا نگه می‌داریم و به دکمه فقط یک توکن کوتاه می‌دهیم.
_query_cache: dict[int, str] = {}
_query_token = count(1)

# کاربرانی که روی «افزودن ماشین» زده‌اند و منتظر تایپ اسم هستیم.
_pending_add: set[int] = set()


def _cache_query(text: str) -> int:
    token = next(_query_token)
    _query_cache[token] = text
    if len(_query_cache) > 500:
        for key in sorted(_query_cache)[: len(_query_cache) - 500]:
            _query_cache.pop(key, None)
    return token


def message_link(row) -> str | None:
    if row["source"] == "live":
        return f"https://t.me/{GROUP_USERNAME}/{row['source_message_id']}"
    return None


def main_buttons() -> list[list[Button]]:
    return [
        [Button.inline("🚘 لیست ماشین‌های من", b"myveh")],
        [Button.inline("➕ افزودن ماشین", b"addveh"), Button.inline("🗑 حذف ماشین", b"delmenu")],
        [Button.inline("📊 آمار دیتابیس", b"stats"), Button.inline("🏠 صفحه اصلی", b"home")],
    ]


def my_vehicles_buttons(conn) -> list[list[Button]]:
    vehicles = list_user_vehicles(conn)
    rows: list[list[Button]] = []
    for i in range(0, len(vehicles), 2):
        rows.append(
            [Button.inline(f"🚗 {v['name']}", f"veh:{v['id']}".encode()) for v in vehicles[i : i + 2]]
        )
    rows.append([Button.inline("➕ افزودن ماشین", b"addveh"), Button.inline("🏠 صفحه اصلی", b"home")])
    return rows


def delete_menu_buttons(conn) -> list[list[Button]]:
    vehicles = list_user_vehicles(conn)
    rows: list[list[Button]] = []
    for i in range(0, len(vehicles), 2):
        rows.append(
            [Button.inline(f"🗑 {v['name']}", f"del:{v['id']}".encode()) for v in vehicles[i : i + 2]]
        )
    rows.append([Button.inline("🏠 صفحه اصلی", b"home")])
    return rows


def tabs_row(kind: str, ref: int, counts: dict[str, int]) -> list[Button]:
    return [
        Button.inline(f"💰 با قیمت ({counts['priced']})", f"p:{kind}:{ref}:0".encode()),
        Button.inline(f"❓ بدون قیمت ({counts['unpriced']})", f"np:{kind}:{ref}:0".encode()),
        Button.inline(f"📅 امروز ({counts['today']})", f"td:{kind}:{ref}:0".encode()),
    ]


def control_buttons(kind: str, ref: int, counts: dict[str, int], active: str | None = None, offset: int = 0) -> list[list[Button]]:
    rows = [tabs_row(kind, ref, counts)]
    prefix_by_active = {"priced": "p", "unpriced": "np", "today": "td"}
    total_by_active = {"priced": counts["priced"], "unpriced": counts["unpriced"], "today": counts["today"]}
    if active in prefix_by_active:
        prefix = prefix_by_active[active]
        total = total_by_active[active]
        nav = []
        if offset > 0:
            nav.append(Button.inline("⬅️ قبلی", f"{prefix}:{kind}:{ref}:{max(0, offset - PAGE_SIZE)}".encode()))
        if offset + PAGE_SIZE < total:
            nav.append(Button.inline("بعدی ➡️", f"{prefix}:{kind}:{ref}:{offset + PAGE_SIZE}".encode()))
        if nav:
            rows.append(nav)
    if kind == "q":
        rows.append([Button.inline("➕ افزودن به لیست من", f"add:{kind}:{ref}".encode())])
    rows.append([Button.inline("🚘 لیست ماشین‌ها", b"myveh"), Button.inline("🏠 صفحه اصلی", b"home")])
    return rows


TEHRAN_OFFSET = timedelta(hours=3, minutes=30)


def format_posted_at(message_date_iso: str | None) -> str | None:
    """تاریخ/ساعت ارسال پیام را به شمسی و به‌وقت تهران فرمت می‌کند."""
    if not message_date_iso:
        return None
    try:
        dt = datetime.fromisoformat(message_date_iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(timezone.utc) + TEHRAN_OFFSET
    jd = jdatetime.datetime.fromgregorian(datetime=local_dt)
    return f"{jd.year}/{jd.month:02d}/{jd.day:02d} - {jd.hour:02d}:{jd.minute:02d}"


BADGE_PATTERNS = [
    (re.compile(r"خوش\s*قیمت"), "✨ خوش‌قیمت"),
    (re.compile(r"زیر\s*قیمت|کف\s*قیمت"), "🔻 زیر قیمت"),
    (re.compile(r"فوری"), "⚡ فوری"),
    (re.compile(r"بدون\s*رنگ|بی\s*رنگ|بیرنگ"), "🛡 بدون رنگ"),
]


def format_mileage(value: int | None) -> str | None:
    if not value:
        return None
    if value < 1000:
        # فروشنده‌ها معمولاً «۵۰ تا کار» می‌نویسند یعنی ۵۰ هزار کیلومتر
        return f"{value} هزار کیلومتر"
    if value % 1000 == 0:
        return f"{value // 1000} هزار کیلومتر"
    return f"{value:,} کیلومتر".replace(",", "/")


def detect_badges(normalized_text: str) -> list[str]:
    """برچسب‌های جذاب از متن آگهی: خوش‌قیمت، فوری، زیر قیمت و..."""
    return [badge for pattern, badge in BADGE_PATTERNS if pattern.search(normalized_text)]


def format_ad_text(row, with_price: bool, index: int) -> str:
    fields = []
    if with_price:
        fields.append(f"💰 {format_price(row['price_million'])}")
    if row["year"]:
        month_part = f" برج {row['month']}" if row["month"] else ""
        fields.append(f"📅 مدل {row['year']}{month_part}")
    if row["color"]:
        fields.append(f"🎨 {row['color']}")
    mileage = format_mileage(row["mileage_km"])
    if mileage:
        fields.append(f"🛣 کارکرد {mileage}")
    if row["trim"]:
        fields.append(f"⚙️ {row['trim']}")
    if row["phone"]:
        fields.append(f"📞 {row['phone']}")
    line1 = f"{index}. " + (" | ".join(fields) if fields else "بدون جزئیات بیشتر")
    extra_lines = []
    badges = detect_badges(row["normalized_text"])
    if badges:
        extra_lines.append(" ".join(badges))
    posted = format_posted_at(row["message_date"])
    if posted:
        extra_lines.append(f"🕓 ارسال: {posted}")
    link = message_link(row)
    if link:
        extra_lines.append(f"🔗 {link}")
    text = line1
    if extra_lines:
        text += "\n" + "\n".join(extra_lines)
    return text


def split_messages(text: str, max_len: int = 3600) -> list[str]:
    parts: list[str] = []
    current = ""
    for chunk in text.split("\n\n" + "-" * 20 + "\n\n"):
        candidate = chunk if not current else current + "\n\n" + "-" * 20 + "\n\n" + chunk
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = chunk
    if current:
        parts.append(current)
    return parts


def format_ad_list(rows, with_price: bool, title: str, start_index: int = 1) -> str:
    if not rows:
        return f"{title}\nچیزی پیدا نشد."
    blocks = [format_ad_text(row, with_price, start_index + i) for i, row in enumerate(rows)]
    return title + "\n\n" + ("\n\n" + "-" * 20 + "\n\n").join(blocks)


async def send_priced_tab(event, conn, kind: str, ref: int, name: str, offset: int = 0) -> None:
    counts = count_search_results(conn, name)
    rows = search_priced_ads(conn, name, limit=PAGE_SIZE, offset=offset)
    text = format_ad_list(rows, with_price=True, title=f"💰 «{name}» — ارزان به گران، از مورد {offset + 1}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="priced", offset=offset))


async def send_unpriced_tab(event, conn, kind: str, ref: int, name: str, offset: int) -> None:
    counts = count_search_results(conn, name)
    rows = search_unpriced_ads(conn, name, limit=PAGE_SIZE, offset=offset)
    text = format_ad_list(rows, with_price=False, title=f"❓ بدون قیمت «{name}» — از مورد {offset + 1}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="unpriced", offset=offset))


async def send_today_tab(event, conn, kind: str, ref: int, name: str, offset: int) -> None:
    counts = count_search_results(conn, name)
    rows = search_today_ads(conn, name, limit=PAGE_SIZE, offset=offset)
    note = "" if rows or counts["today"] else " (این تب فقط پیام‌های زنده از الان به بعد را نشان می‌دهد)"
    text = format_ad_list(rows, with_price=True, title=f"📅 آگهی‌های امروز «{name}» — از مورد {offset + 1}{note}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="today", offset=offset))


async def run_bot() -> None:
    settings = Settings.from_env()
    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Add your BotFather token to .env first.")

    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    if proxy:
        print("Using Telegram proxy from TELEGRAM_PROXY.", flush=True)
    client = TelegramClient("telegramonline_bot", settings.api_id, settings.api_hash, proxy=proxy)
    # متن آگهی‌ها از کاربرهای گروه می‌آید و کاملاً غیرقابل‌پیش‌بینی است؛ اگر
    # تصادفاً شبیه نشانه‌های مارک‌داون (*, _, `) باشد، تفسیر خودکار مارک‌داون
    # تلتون کنار ایموجی‌ها باعث خطای EntityBoundsInvalidError می‌شود. چون به
    # بولد/ایتالیک نیاز نداریم (لینک‌ها بدون مارک‌داون هم در تلگرام کلیک‌پذیرند)،
    # این تفسیر را کاملاً خاموش می‌کنیم.
    client.parse_mode = None

    # --- جمع‌آوری زنده پیام‌های گروه (چون بات عضو/ادمین گروه است) ---
    if settings.group:
        group_chat_id = resolve_chat_id(settings.group)

        @client.on(events.NewMessage(chats=group_chat_id))
        async def group_listener(event) -> None:
            if not event.message.message:
                return
            ads = parse_message_group(
                str(event.message.id),
                event.message.message,
                event.message.date,
                source="live",
            )
            save_ads(conn, ads)

    # --- دستورات خصوصی ---
    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start(event) -> None:
        _pending_add.discard(event.sender_id)
        await event.respond(WELCOME, buttons=main_buttons())

    @client.on(events.NewMessage)
    async def text_handler(event) -> None:
        if not event.is_private:
            return
        text = (event.raw_text or "").strip()
        if not text or text.startswith("/"):
            return
        if event.sender_id in _pending_add:
            _pending_add.discard(event.sender_id)
            if add_user_vehicle(conn, text):
                await event.respond(f"✅ «{text}» به لیست ماشین‌هایت اضافه شد.", buttons=my_vehicles_buttons(conn))
            else:
                await event.respond(f"⚠️ «{text}» قبلاً در لیست هست یا نام معتبر نیست.", buttons=my_vehicles_buttons(conn))
            return
        token = _cache_query(text)
        await send_priced_tab(event, conn, "q", token, text)

    @client.on(events.CallbackQuery)
    async def callback(event) -> None:
        data = event.data.decode("utf-8")
        parts = data.split(":")
        head = parts[0]

        if head == "home":
            _pending_add.discard(event.sender_id)
            await event.edit(WELCOME, buttons=main_buttons())
            return
        if head == "stats":
            s = stats(conn)
            text = (
                "📊 آمار دیتابیس\n\n"
                f"کل پیام‌ها: {s['total']}\n"
                f"آگهی فروش: {s['sale']}\n"
                f"با قیمت: {s['with_price']}\n"
                f"بدون قیمت: {s['without_price']}\n"
                f"جمع‌شده زنده از گروه: {s['live_collected']}\n"
                f"خریدار: {s['buyer']}\n"
                f"تبلیغ/نامعتبر: {s['spam']}\n"
                f"ماشین‌های ذخیره‌شده: {s['saved_vehicles']}"
            )
            await event.edit(text, buttons=main_buttons())
            return
        if head == "myveh":
            vehicles = list_user_vehicles(conn)
            if not vehicles:
                await event.edit("لیست ماشین‌هایت خالی است.\nبا «➕ افزودن ماشین» اسم ماشین را اضافه کن.", buttons=main_buttons())
                return
            await event.edit(f"🚘 ماشین‌های تو ({len(vehicles)} مورد):", buttons=my_vehicles_buttons(conn))
            return
        if head == "addveh":
            _pending_add.add(event.sender_id)
            await event.edit("✍️ اسم ماشین را بفرست (مثلاً: پراید یا کوییک).", buttons=[[Button.inline("انصراف", b"home")]])
            return
        if head == "delmenu":
            vehicles = list_user_vehicles(conn)
            if not vehicles:
                await event.edit("لیست خالی است؛ چیزی برای حذف نیست.", buttons=main_buttons())
                return
            await event.edit("روی هر ماشین بزنی حذف می‌شود:", buttons=delete_menu_buttons(conn))
            return
        if head == "del":
            vehicle_id = int(parts[1])
            vehicle = get_user_vehicle(conn, vehicle_id)
            removed = remove_user_vehicle(conn, vehicle_id)
            name = vehicle["name"] if vehicle else "?"
            note = f"🗑 «{name}» حذف شد." if removed else "این مورد قبلاً حذف شده."
            vehicles = list_user_vehicles(conn)
            await event.edit(note, buttons=delete_menu_buttons(conn) if vehicles else main_buttons())
            return

        if head == "veh":
            vehicle_id = int(parts[1])
            vehicle = get_user_vehicle(conn, vehicle_id)
            if not vehicle:
                await event.answer("این ماشین از لیست حذف شده.", alert=True)
                return
            await event.answer()
            await send_priced_tab(event, conn, "v", vehicle_id, vehicle["name"])
            return

        # از این‌جا به بعد: head یکی از p / np / td / add است، با ساختار kind:ref[:offset]
        kind = parts[1]
        ref = int(parts[2])
        offset = int(parts[3]) if len(parts) > 3 else 0

        if kind == "v":
            vehicle = get_user_vehicle(conn, ref)
            if not vehicle:
                await event.answer("این ماشین از لیست حذف شده.", alert=True)
                return
            name = vehicle["name"]
        else:  # kind == "q"
            name = _query_cache.get(ref)
            if not name:
                await event.answer("این جست‌وجو منقضی شده؛ اسم ماشین را دوباره بفرست.", alert=True)
                return

        await event.answer()
        if head == "add":
            if add_user_vehicle(conn, name):
                await event.respond(f"«{name}» به لیست اضافه شد ✅", buttons=main_buttons())
            else:
                await event.answer("قبلاً در لیست هست.", alert=True)
        elif head == "p":
            await send_priced_tab(event, conn, kind, ref, name, offset)
        elif head == "np":
            await send_unpriced_tab(event, conn, kind, ref, name, offset)
        elif head == "td":
            await send_today_tab(event, conn, kind, ref, name, offset)

    await client.start(bot_token=settings.bot_token)
    print("telegramonline bot is running.")
    await client.run_until_disconnected()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()