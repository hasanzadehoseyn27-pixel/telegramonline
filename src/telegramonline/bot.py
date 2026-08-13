from __future__ import annotations

import asyncio
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from itertools import count

import jdatetime
from openpyxl import Workbook
from telethon import Button, TelegramClient, events
from telethon.errors import MessageNotModifiedError

from .config import Settings
from .net import parse_proxy_from_env
from .query import format_price
from .zero_whitelist import match_zero_whitelist
from .storage import (
    add_channel,
    add_user_vehicle,
    cheapest_per_vehicle_report,
    connect,
    count_search_results,
    deactivate_channel,
    get_channel_by_username,
    get_user_vehicle,
    list_channels,
    list_user_vehicles,
    remove_user_vehicle,
    search_buyer_ads,
    search_priced_ads,
    search_today_ads,
    search_unpriced_ads,
    stats,
    today_day_key,
    yesterday_day_key,
)

# توجه: قبلاً اینجا یک یوزرنیم ثابت برای همه‌ی لینک‌ها بود، ولی چون از الان
# چند کانال هم‌زمان پیمایش می‌شود، هر آگهی باید به یوزرنیم واقعیِ کانال خودش
# لینک شود (که در ستون channel_username هر ردیف ذخیره شده است).
PAGE_SIZE = 10

WELCOME = """
🚗 telegramonline آماده است.

▫️ از «💰 کمترین قیمت‌ها» لیست همه‌ی مدل‌های شناخته‌شده رو با ارزون‌ترین قیمت امروزشون ببین.
▫️ یا اسم هر ماشینی رو تایپ کن — اگه تو خانواده‌ی «کمترین قیمت‌ها» باشه نشونت می‌دم.
""".strip()

# کوئری‌های جست‌وجوی آزاد (متنی که کاربر تایپ کرده) — callback تلگرام فقط ۶۴ بایت
# جا دارد، پس متن فارسی را اینجا نگه می‌داریم و به دکمه فقط یک توکن کوتاه می‌دهیم.
_query_cache: dict[int, str] = {}
_query_token = count(1)

# کاربرانی که روی «افزودن ماشین» یا «افزودن کانال» زده‌اند و منتظر تایپ هستیم.
_pending_add: set[int] = set()
_pending_add_channel: set[int] = set()
_pending_remove_channel: set[int] = set()


def _cache_query(text: str) -> int:
    token = next(_query_token)
    _query_cache[token] = text
    if len(_query_cache) > 500:
        for key in sorted(_query_cache)[: len(_query_cache) - 500]:
            _query_cache.pop(key, None)
    return token


def message_link(row) -> str | None:
    if row["source"] == "live" and row["channel_username"]:
        return f"https://t.me/{row['channel_username']}/{row['source_message_id']}"
    return None


def get_cheapest_whitelisted_models(conn, day_key: str | None = None) -> list[dict]:
    """کمترین قیمت هر مدلِ لیست‌سفیدی برای یه روز — دقیقاً همون منطقی که
    بریج CarX (کیوان‌خودرو) استفاده می‌کنه، تا نتایج این‌جا و سایت یکی باشه."""
    day_key = day_key or today_day_key()
    rows = conn.execute(
        "SELECT * FROM ads WHERE status = 'sale' AND price_million IS NOT NULL AND day_key = ?",
        (day_key,),
    ).fetchall()

    groups: dict[str, dict] = {}
    for row in rows:
        key = match_zero_whitelist(row["vehicle_name"], row["trim"])
        if key is None:
            continue
        price = row["price_million"]
        g = groups.get(key)
        if g is None:
            groups[key] = {"min_price": price, "sample": row, "count": 1}
        else:
            g["count"] += 1
            if price < g["min_price"]:
                g["min_price"] = price
                g["sample"] = row

    result = [
        {
            "key": key,
            "title": build_clean_title(g["sample"]["vehicle_name"], g["sample"]["trim"]),
            "min_price": g["min_price"],
            "count": g["count"],
        }
        for key, g in groups.items()
    ]
    result.sort(key=lambda x: x["title"])
    return result


CHEAPEST_PAGE_SIZE = 15


def format_cheapest_page(items: list[dict], offset: int, day_label: str) -> str:
    if not items:
        return f"💰 کمترین قیمت‌ها ({day_label})\n\nهنوز داده‌ای برای {day_label} نیست."
    page = items[offset : offset + CHEAPEST_PAGE_SIZE]
    lines = [f"💰 کمترین قیمت‌ها — {day_label} ({len(items)} مدل) — از مورد {offset + 1}", ""]
    for i, item in enumerate(page, start=offset + 1):
        lines.append(
            f"{i}. {item['title']}\n   از {format_price(item['min_price'])} — {item['count']} آگهی"
        )
    return "\n".join(lines)


def cheapest_nav_buttons(offset: int, total: int, day: str) -> list[list[Button]]:
    nav = []
    if offset > 0:
        nav.append(Button.inline("⬅️ قبلی", f"cheapest:{max(0, offset - CHEAPEST_PAGE_SIZE)}:{day}".encode()))
    if offset + CHEAPEST_PAGE_SIZE < total:
        nav.append(Button.inline("بعدی ➡️", f"cheapest:{offset + CHEAPEST_PAGE_SIZE}:{day}".encode()))
    rows = [nav] if nav else []
    other_day = "yesterday" if day == "today" else "today"
    other_label = "📅 دیروز" if day == "today" else "📅 امروز"
    rows.append([Button.inline(other_label, f"cheapest:0:{other_day}".encode())])
    rows.append([Button.inline("🏠 صفحه اصلی", b"home")])
    return rows


def main_buttons() -> list[list[Button]]:
    return [
        [Button.inline("💰 کمترین قیمت‌ها", b"cheapest:0:today")],
        [Button.inline("📡 کانال‌ها", b"chlist"), Button.inline("📊 آمار دیتابیس", b"stats")],
        [Button.inline("🏠 صفحه اصلی", b"home")],
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


def _channel_status(c: dict) -> str:
    if not c["active"]:
        return "🚪 در حال خروج..."
    if c["joined"]:
        return "✅ فعال"
    return "⏳ در حال عضویت..."


def channel_list_text(conn) -> str:
    channels = list_channels(conn, today_only=True)
    if not channels:
        return "📡 هنوز هیچ کانالی اضافه نشده."
    total_today = sum(c["message_count"] for c in channels)
    lines = [f"📡 کانال‌ها ({len(channels)}) — جمع پیام امروز: {total_today}", ""]
    for c in channels:
        lines.append(f"• {c['title'] or c['username']} (@{c['username']}) — {_channel_status(c)} — {c['message_count']} پیام امروز")
    return "\n".join(lines)


def channel_buttons(conn) -> list[list[Button]]:
    channels = [c for c in list_channels(conn, today_only=False) if c["active"]]
    rows: list[list[Button]] = []
    for i in range(0, len(channels), 2):
        rows.append(
            [Button.inline(f"🗑 {c['username']}", f"delch:{c['id']}".encode()) for c in channels[i : i + 2]]
        )
    rows.append([Button.inline("➕ افزودن کانال", b"addch"), Button.inline("🗑 حذف با یوزرنیم", b"delchtxt")])
    rows.append([Button.inline("🔄 تازه‌سازی", b"chlist"), Button.inline("🏠 صفحه اصلی", b"home")])
    return rows


def tabs_rows(kind: str, ref: int, counts: dict[str, int]) -> list[list[Button]]:
    return [
        [
            Button.inline(f"💰 با قیمت ({counts['priced']})", f"p:{kind}:{ref}:0".encode()),
            Button.inline(f"❓ بدون قیمت ({counts['unpriced']})", f"np:{kind}:{ref}:0".encode()),
        ],
        [
            Button.inline(f"📅 امروز ({counts['today']})", f"td:{kind}:{ref}:0".encode()),
            Button.inline(f"🙋 خریداران ({counts['buyers']})", f"by:{kind}:{ref}:0".encode()),
        ],
    ]


def control_buttons(kind: str, ref: int, counts: dict[str, int], active: str | None = None, offset: int = 0) -> list[list[Button]]:
    rows = list(tabs_rows(kind, ref, counts))
    prefix_by_active = {"priced": "p", "unpriced": "np", "today": "td", "buyers": "by"}
    total_by_active = {
        "priced": counts["priced"],
        "unpriced": counts["unpriced"],
        "today": counts["today"],
        "buyers": counts["buyers"],
    }
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
    # حروف تکراری/کشیده هم پوشش داده می‌شوند: «خوشششش قیمت»، «فوووری»
    (re.compile(r"خو+ش+\s*قی+مت"), "✨ خوش‌قیمت"),
    (re.compile(r"زیر\s*قیمت|کف\s*قیمت"), "🔻 زیر قیمت"),
    (re.compile(r"فو+ری+"), "⚡ فوری"),
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


def fire_count(raw_text: str) -> int:
    """تعداد 🔥 در متن اصلی — فروشنده‌ها با تعداد آتش شدت تخفیف/کیفیت را نشان می‌دهند."""
    return raw_text.count("🔥")


_PERSIAN_DIGITS_FOR_DEDUP = "۰۱۲۳۴۵۶۷۸۹"


def _normalize_for_dedup(word: str) -> str:
    out = []
    for ch in word:
        idx = _PERSIAN_DIGITS_FOR_DEDUP.find(ch)
        out.append(str(idx) if idx >= 0 else ch.lower())
    return "".join(out)


def build_clean_title(vehicle_name: str | None, trim: str | None) -> str:
    """همون منطق پاک‌سازی عنوان تو کیوان‌خودرو (BuildCleanTitle تو C#) —
    کلمه‌ی «خودرو» رو هرجا باشه حذف می‌کنه، کلمات دقیقاً تکراری رو حذف
    می‌کنه، و شبه‌تکرارهای چسبیده (مثل «هایما S5 هایماs5») رو هم می‌گیره."""
    parts = [p for p in [vehicle_name, trim] if p and p.strip()]
    words = " ".join(parts).split()

    seen: set[str] = set()
    running = ""
    deduped: list[str] = []
    for word in words:
        if word == "خودرو":
            continue
        normalized = _normalize_for_dedup(word)
        if normalized in seen:
            continue
        seen.add(normalized)
        if len(normalized) >= 2 and running and (normalized in running or running in normalized):
            continue
        deduped.append(word)
        running += normalized

    result = " ".join(deduped).strip()
    return result or "خودرو"


def ad_title(row) -> str:
    """خط اول معنادار متن آگهی به‌عنوان عنوان — تا معلوم باشد کدام ماشین است."""
    try:
        clean = build_clean_title(row["vehicle_name"], row["trim"])
    except (KeyError, IndexError):
        clean = "خودرو"
    if clean != "خودرو":
        return clean if len(clean) <= 70 else clean[:67] + "..."

    for line in row["raw_text"].split("\n"):
        stripped = line.strip()
        if stripped and re.search(r"[A-Za-zآ-ی]", stripped):
            return stripped if len(stripped) <= 70 else stripped[:67] + "..."
    return "—"


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
    line1 = f"{index}. 🚗 {ad_title(row)}"
    line2 = " | ".join(fields) if fields else None
    extra_lines = []
    if line2:
        extra_lines.append(line2)
    badges = detect_badges(row["normalized_text"])
    fires = fire_count(row["raw_text"])
    if fires:
        badges.append("🔥" * min(fires, 8))
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


_MAX_WHITELIST_SCAN = 300  # حداکثر تعداد ردیف خام که برای پیدا کردن نتایج لیست‌سفیدی می‌گردیم


def _fetch_whitelisted_page(fetch_fn, conn, name: str, limit: int, start_offset: int):
    """چون بعد از فیلتر لیست سفید ممکنه یه صفحه‌ی خام کامل هیچ نتیجه‌ی
    معتبری نداشته باشه (مثلاً «پراید» که اکثرش کارکرده‌ی معمولیه، نه
    ۱۵۱ GX)، تا وقتی به‌اندازه‌ی کافی نتیجه‌ی match‌شده پیدا نکنیم (یا به
    سقف اسکن برسیم) صفحه‌ی بعدی خام رو هم می‌گیریم."""
    collected: list = []
    raw_offset = start_offset
    scanned = 0
    while len(collected) < limit and scanned < _MAX_WHITELIST_SCAN:
        batch = fetch_fn(conn, name, limit=PAGE_SIZE, offset=raw_offset)
        if not batch:
            break
        scanned += len(batch)
        raw_offset += len(batch)
        collected.extend(
            r for r in batch if match_zero_whitelist(r["vehicle_name"], r["trim"])
        )
        if len(batch) < PAGE_SIZE:
            break
    return collected[:limit]


async def send_priced_tab(event, conn, kind: str, ref: int, name: str, offset: int = 0) -> None:
    counts = count_search_results(conn, name)
    rows = _fetch_whitelisted_page(search_priced_ads, conn, name, PAGE_SIZE, offset)
    text = format_ad_list(rows, with_price=True, title=f"💰 «{name}» — ارزان به گران، از مورد {offset + 1}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="priced", offset=offset))


async def send_unpriced_tab(event, conn, kind: str, ref: int, name: str, offset: int) -> None:
    counts = count_search_results(conn, name)
    rows = _fetch_whitelisted_page(search_unpriced_ads, conn, name, PAGE_SIZE, offset)
    text = format_ad_list(rows, with_price=False, title=f"❓ بدون قیمت «{name}» — از مورد {offset + 1}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="unpriced", offset=offset))


async def send_today_tab(event, conn, kind: str, ref: int, name: str, offset: int) -> None:
    counts = count_search_results(conn, name)
    rows = _fetch_whitelisted_page(search_today_ads, conn, name, PAGE_SIZE, offset)
    note = "" if rows or counts["today"] else " (این تب فقط پیام‌های زنده از الان به بعد را نشان می‌دهد)"
    text = format_ad_list(rows, with_price=True, title=f"📅 آگهی‌های امروز «{name}» — از مورد {offset + 1}{note}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="today", offset=offset))


async def send_buyers_tab(event, conn, kind: str, ref: int, name: str, offset: int) -> None:
    counts = count_search_results(conn, name)
    rows = search_buyer_ads(conn, name, limit=PAGE_SIZE, offset=offset)
    text = format_ad_list(rows, with_price=True, title=f"🙋 خریداران «{name}» — از مورد {offset + 1}", start_index=offset + 1)
    for part in split_messages(text):
        await event.respond(part)
    await event.respond("ادامه:", buttons=control_buttons(kind, ref, counts, active="buyers", offset=offset))


async def safe_edit(event, text: str, buttons=None) -> None:
    """مثل event.edit ولی وقتی محتوا دقیقاً همان قبلی است (کلیک دوباره روی
    «تازه‌سازی» یا دکمه‌ای که چیزی عوض نکرده) کرش نمی‌کند؛ تلگرام برای ادیت
    به محتوای عیناً یکسان ارور MessageNotModifiedError می‌دهد که اینجا
    بی‌خطر نادیده گرفته می‌شود.
    """
    try:
        await event.edit(text, buttons=buttons)
    except MessageNotModifiedError:
        await event.answer()


def build_excel_report(conn, day_key: str, label: str) -> str:
    """گزارش کمترین قیمت هر مدل را برای یک روز به‌صورت فایل اکسل می‌سازد و مسیرش را برمی‌گرداند."""
    rows = cheapest_per_vehicle_report(conn, day_key=day_key)
    wb = Workbook()
    ws = wb.active
    ws.title = label[:31]
    ws.sheet_view.rightToLeft = True
    headers = ["ماشین", "کمترین قیمت (میلیون)", "مدل", "برج", "رنگ", "تماس", "ارسال", "لینک تلگرام"]
    ws.append(headers)
    for row in rows:
        posted = format_posted_at(row["message_date"]) or ""
        ws.append(
            [
                row["vehicle_name"],
                row["price_million"],
                row["year"] or "",
                row["month"] or "",
                row["color"] or "",
                row["phone"] or "",
                posted,
                message_link(row) or "",
            ]
        )
    for column_cells in ws.columns:
        length = max((len(str(c.value)) for c in column_cells if c.value is not None), default=10)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 45)
    fd, path = tempfile.mkstemp(suffix=".xlsx", prefix=f"report_{day_key}_")
    os.close(fd)
    wb.save(path)
    return path


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
    # نکته: جمع‌آوری زنده‌ی پیام‌ها دیگر اینجا انجام نمی‌شود — از الان
    # collector.py (با اکانت شخصی) مسئول گوش‌دادن به همه‌ی کانال‌هاست، چون
    # فقط آن می‌تواند واقعاً عضو کانال‌های جدید شود. bot.py فقط UI/مدیریت است.

    # --- دستورات خصوصی ---
    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start(event) -> None:
        _pending_add.discard(event.sender_id)
        _pending_add_channel.discard(event.sender_id)
        _pending_remove_channel.discard(event.sender_id)
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
        if event.sender_id in _pending_add_channel:
            _pending_add_channel.discard(event.sender_id)
            channel_id = add_channel(conn, text)
            if channel_id:
                await event.respond(
                    f"✅ کانال «{text}» ثبت شد.\nظرف حداکثر ۳۰ ثانیه اکانت جمع‌آورنده عضو می‌شود و پیام‌های امروزش را می‌خواند.",
                    buttons=channel_buttons(conn),
                )
            else:
                await event.respond(f"⚠️ کانال «{text}» قبلاً ثبت شده یا نام معتبر نیست.", buttons=channel_buttons(conn))
            return
        if event.sender_id in _pending_remove_channel:
            _pending_remove_channel.discard(event.sender_id)
            channel = get_channel_by_username(conn, text)
            if not channel:
                await event.respond(f"⚠️ کانالی با یوزرنیم «{text}» پیدا نشد.", buttons=channel_buttons(conn))
            else:
                deactivate_channel(conn, channel["id"])
                await event.respond(
                    f"🗑 کانال «{channel['username']}» غیرفعال شد.\nظرف حداکثر ۳۰ ثانیه اکانت از آن خارج و کامل حذف می‌شود.",
                    buttons=channel_buttons(conn),
                )
            return
        key = match_zero_whitelist(text, None)
        if key is None:
            await event.respond(
                "🚫 ماشین شما به لیست «کمترین قیمت‌ها» اضافه نشده است.",
                buttons=[[Button.inline("💰 کمترین قیمت‌ها", b"cheapest:0:today")]],
            )
            return

        items = get_cheapest_whitelisted_models(conn, day_key=today_day_key())
        match = next((it for it in items if it["key"] == key), None)
        if match is None:
            await event.respond(
                "🚫 ماشین شما تو خانواده‌ی «کمترین قیمت‌ها» هست، ولی امروز آگهی قیمت‌داری ازش پیدا نشد.",
                buttons=[[Button.inline("💰 کمترین قیمت‌ها", b"cheapest:0:today")]],
            )
            return

        await event.respond(
            f"💰 {match['title']}\n\nاز {format_price(match['min_price'])} — {match['count']} آگهی امروز",
            buttons=[[Button.inline("💰 کمترین قیمت‌ها (همه)", b"cheapest:0:today")]],
        )

    @client.on(events.CallbackQuery)
    async def callback(event) -> None:
        data = event.data.decode("utf-8")
        parts = data.split(":")
        head = parts[0]

        if head == "home":
            _pending_add.discard(event.sender_id)
            _pending_add_channel.discard(event.sender_id)
            _pending_remove_channel.discard(event.sender_id)
            await safe_edit(event, WELCOME, buttons=main_buttons())
            return
        if head == "cheapest":
            offset = int(parts[1]) if len(parts) > 1 else 0
            day = parts[2] if len(parts) > 2 else "today"
            day_key = today_day_key() if day == "today" else yesterday_day_key()
            day_label = "امروز" if day == "today" else "دیروز"
            items = get_cheapest_whitelisted_models(conn, day_key=day_key)
            text = format_cheapest_page(items, offset, day_label)
            await safe_edit(event, text, buttons=cheapest_nav_buttons(offset, len(items), day))
            return
        if head == "stats":
            s = stats(conn, day_key=today_day_key())
            text = (
                "📊 آمار دیتابیس (فقط امروز)\n\n"
                f"کل پیام‌ها: {s['total']}\n"
                f"آگهی فروش: {s['sale']}\n"
                f"با قیمت: {s['with_price']}\n"
                f"بدون قیمت: {s['without_price']}\n"
                f"جمع‌شده زنده از گروه: {s['live_collected']}\n"
                f"خریدار: {s['buyer']}\n"
                f"تبلیغ/نامعتبر: {s['spam']}"
            )
            await safe_edit(event, text, buttons=main_buttons())
            return
        if head == "report":
            day_choice = parts[1] if len(parts) > 1 else "today"
            day_key = today_day_key() if day_choice == "today" else yesterday_day_key()
            label = "امروز" if day_choice == "today" else "دیروز"
            rows = cheapest_per_vehicle_report(conn, day_key=day_key)
            if not rows:
                await event.answer(f"برای {label} هنوز داده‌ای برای گزارش نیست.", alert=True)
                return
            await event.answer()
            path = build_excel_report(conn, day_key, label)
            try:
                await event.respond(file=path, message=f"📊 گزارش کمترین قیمت هر مدل — {label} ({len(rows)} مدل)")
            finally:
                os.remove(path)
            return
        if head == "myveh":
            vehicles = list_user_vehicles(conn)
            if not vehicles:
                await safe_edit(event, "لیست ماشین‌هایت خالی است.\nبا «➕ افزودن ماشین» اسم ماشین را اضافه کن.", buttons=main_buttons())
                return
            await safe_edit(event, f"🚘 ماشین‌های تو ({len(vehicles)} مورد):", buttons=my_vehicles_buttons(conn))
            return
        if head == "addveh":
            _pending_add.add(event.sender_id)
            await safe_edit(event, "✍️ اسم ماشین را بفرست (مثلاً: پراید یا کوییک).", buttons=[[Button.inline("انصراف", b"home")]])
            return
        if head == "delmenu":
            vehicles = list_user_vehicles(conn)
            if not vehicles:
                await safe_edit(event, "لیست خالی است؛ چیزی برای حذف نیست.", buttons=main_buttons())
                return
            await safe_edit(event, "روی هر ماشین بزنی حذف می‌شود:", buttons=delete_menu_buttons(conn))
            return
        if head == "del":
            vehicle_id = int(parts[1])
            vehicle = get_user_vehicle(conn, vehicle_id)
            removed = remove_user_vehicle(conn, vehicle_id)
            name = vehicle["name"] if vehicle else "?"
            note = f"🗑 «{name}» حذف شد." if removed else "این مورد قبلاً حذف شده."
            vehicles = list_user_vehicles(conn)
            await safe_edit(event, note, buttons=delete_menu_buttons(conn) if vehicles else main_buttons())
            return

        if head == "chlist":
            _pending_add_channel.discard(event.sender_id)
            _pending_remove_channel.discard(event.sender_id)
            await safe_edit(event, channel_list_text(conn), buttons=channel_buttons(conn))
            return
        if head == "addch":
            _pending_add_channel.add(event.sender_id)
            await safe_edit(event, 
                "✍️ یوزرنیم کانال عمومی را بفرست (مثلاً: khodro_tirgham یا لینک کامل t.me/...).",
                buttons=[[Button.inline("انصراف", b"chlist")]],
            )
            return
        if head == "delchtxt":
            _pending_remove_channel.add(event.sender_id)
            await safe_edit(event, 
                "✍️ یوزرنیم کانالی که می‌خوای حذف شود را بفرست.",
                buttons=[[Button.inline("انصراف", b"chlist")]],
            )
            return
        if head == "delch":
            channel_id = int(parts[1])
            deactivated = deactivate_channel(conn, channel_id)
            note = "🗑 کانال غیرفعال شد؛ ظرف چند لحظه اکانت از آن خارج می‌شود." if deactivated else "این کانال قبلاً حذف شده."
            await safe_edit(event, note + "\n\n" + channel_list_text(conn), buttons=channel_buttons(conn))
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
        elif head == "by":
            await send_buyers_tab(event, conn, kind, ref, name, offset)

    await client.start(bot_token=settings.bot_token)
    print("telegramonline bot is running.")
    await client.run_until_disconnected()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()