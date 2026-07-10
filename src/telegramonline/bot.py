from __future__ import annotations

import asyncio
from textwrap import shorten

from telethon import Button, TelegramClient, events

from .config import Settings
from .net import parse_proxy_from_env
from .query import format_price
from .storage import available_vehicles, connect, lowest_ads_for_vehicle, lowest_by_vehicle, stats


WELCOME = """
telegramonline آماده است.

هدف: پیدا کردن کمترین قیمت معتبر از بین آگهی‌های خودرو و آوردن متن دقیق همان پیام.
""".strip()


def main_buttons() -> list[list[Button]]:
    return [
        [
            Button.inline("🚘 لیست ماشین‌ها", b"vehicles:0"),
        ],
        [
            Button.inline("📊 آمار دیتابیس", b"stats"),
            Button.inline("🔄 تازه‌سازی", b"home"),
        ],
    ]


def vehicle_list_buttons(conn, page: int = 0, page_size: int = 12) -> list[list[Button]]:
    vehicles = available_vehicles(conn)
    start = page * page_size
    selected = vehicles[start : start + page_size]
    rows: list[list[Button]] = []
    for index in range(0, len(selected), 2):
        row_buttons = []
        for item in selected[index : index + 2]:
            label = f"{item['vehicle_name']} ({item['total']})"
            row_buttons.append(Button.inline(label, f"vehicle:{item['vehicle_key']}".encode("utf-8")))
        rows.append(row_buttons)

    nav = []
    if page > 0:
        nav.append(Button.inline("⬅️ قبلی", f"vehicles:{page - 1}".encode("utf-8")))
    if start + page_size < len(vehicles):
        nav.append(Button.inline("بعدی ➡️", f"vehicles:{page + 1}".encode("utf-8")))
    if nav:
        rows.append(nav)
    rows.append([Button.inline("🏠 صفحه اصلی", b"home"), Button.inline("📊 آمار", b"stats")])
    return rows


def format_vehicle_list_text(conn, page: int = 0, page_size: int = 12) -> str:
    vehicles = available_vehicles(conn)
    if not vehicles:
        return "هنوز ماشین قیمت‌دار معتبری در دیتابیس پیدا نشده."
    start = page * page_size
    end = min(start + page_size, len(vehicles))
    return (
        "🚘 لیست ماشین‌های موجود\n\n"
        f"تعداد مدل‌های تشخیص‌داده‌شده: {len(vehicles)}\n"
        f"نمایش {start + 1} تا {end}\n\n"
        "روی هر ماشین بزنی، ۱۰ آگهی ارزان‌تر همان ماشین می‌آید."
    )


def split_messages(text: str, max_len: int = 3600) -> list[str]:
    parts: list[str] = []
    current = ""
    for chunk in text.split("\n\n--------------------\n\n"):
        candidate = chunk if not current else current + "\n\n--------------------\n\n" + chunk
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = chunk
    if current:
        parts.append(current)
    return parts


def format_ad(row, raw_width: int = 650) -> str:
    details = []
    if row["year"]:
        details.append(f"مدل {row['year']}")
    if row["month"]:
        details.append(f"برج {row['month']}")
    if row["color"]:
        details.append(row["color"])
    if row["trim"]:
        details.append(row["trim"])
    if row["phone"]:
        details.append(f"تماس: {row['phone']}")
    meta = " | ".join(details)
    if meta:
        meta = "\n" + meta
    raw = shorten(row["raw_text"].replace("\n\n", "\n"), width=raw_width, placeholder=" ...")
    return (
        f"🚗 {row['vehicle_name']}\n"
        f"💰 {format_price(row['price_million'])}"
        f"{meta}\n"
        f"🎯 اطمینان: {row['confidence']:.2f}\n\n"
        f"متن پیام:\n{raw}"
    )


def format_lowest(rows) -> str:
    if not rows:
        return "فعلا آگهی معتبر با قیمت پیدا نشد."
    chunks = []
    for index, row in enumerate(rows, start=1):
        chunks.append(f"{index}. {format_ad(row)}")
    message = "\n\n" + ("-" * 20) + "\n\n"
    return message.join(chunks)


def format_vehicle_ads(vehicle_name: str, rows) -> str:
    if not rows:
        return f"برای {vehicle_name} آگهی قیمت‌دار معتبر پیدا نشد."
    chunks = [f"💰 ۱۰ قیمت پایین‌تر برای {vehicle_name}\n"]
    for index, row in enumerate(rows, start=1):
        chunks.append(f"{index}. {format_ad(row, raw_width=430)}")
    return ("\n\n" + ("-" * 20) + "\n\n").join(chunks)


async def run_bot() -> None:
    settings = Settings.from_env()
    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty. Add your BotFather token to .env first.")

    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    if proxy:
        print("Using Telegram proxy from TELEGRAM_PROXY.", flush=True)
    client = TelegramClient("telegramonline_bot", settings.api_id, settings.api_hash, proxy=proxy)

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start(event) -> None:
        await event.respond(WELCOME, buttons=main_buttons())

    @client.on(events.NewMessage(pattern=r"^/lowest(?:\s+(\d+))?$"))
    async def lowest_command(event) -> None:
        days_text = event.pattern_match.group(1)
        days = int(days_text) if days_text else None
        rows = lowest_by_vehicle(conn, days=days, limit=10)
        await event.respond(format_lowest(rows), buttons=main_buttons())

    @client.on(events.NewMessage(pattern=r"^/search\s+(.+)$"))
    async def search_command(event) -> None:
        vehicle = event.pattern_match.group(1).strip()
        rows = lowest_by_vehicle(conn, days=None, limit=10, vehicle_query=vehicle)
        for part in split_messages(format_lowest(rows)):
            await event.respond(part, buttons=main_buttons())

    @client.on(events.CallbackQuery)
    async def callback(event) -> None:
        data = event.data.decode("utf-8")
        if data == "home":
            await event.edit(WELCOME, buttons=main_buttons())
            return
        if data == "stats":
            current = stats(conn)
            text = (
                "📊 آمار دیتابیس\n\n"
                f"کل پیام‌ها: {current['total']}\n"
                f"فروش: {current['sale']}\n"
                f"دارای خودرو: {current['with_vehicle']}\n"
                f"دارای قیمت: {current['with_price']}\n"
                f"خریدار: {current['buyer']}\n"
                f"تبلیغ/نامعتبر: {current['spam']}"
            )
            await event.edit(text, buttons=main_buttons())
            return
        if data.startswith("vehicles:"):
            page = int(data.split(":", 1)[1])
            await event.edit(format_vehicle_list_text(conn, page), buttons=vehicle_list_buttons(conn, page))
            return
        if data.startswith("vehicle:"):
            vehicle_key = data.split(":", 1)[1]
            rows = lowest_ads_for_vehicle(conn, vehicle_key, limit=10)
            vehicle_name = rows[0]["vehicle_name"] if rows else vehicle_key
            await event.edit(
                f"✅ {vehicle_name} انتخاب شد.\n۱۰ قیمت پایین‌تر را در پیام‌های بعدی می‌فرستم.",
                buttons=vehicle_list_buttons(conn, 0),
            )
            for part in split_messages(format_vehicle_ads(vehicle_name, rows)):
                await event.respond(part)
            return
        if data.startswith("lowest:"):
            value = data.split(":", 1)[1]
            days = None if value == "all" else int(value)
            rows = lowest_by_vehicle(conn, days=days, limit=10)
            title = "🔥 کمترین قیمت‌های معتبر"
            if days:
                title += f" در {days} روز گذشته"
            else:
                title += " در دیتابیس فعلی"
            await event.edit(title + "\n\n" + format_lowest(rows), buttons=main_buttons())
            return
        if data.startswith("search:"):
            vehicle = data.split(":", 1)[1]
            rows = lowest_by_vehicle(conn, days=None, limit=10, vehicle_query=vehicle)
            await event.edit(f"🔎 نتیجه برای {vehicle}", buttons=main_buttons())
            for part in split_messages(format_lowest(rows)):
                await event.respond(part)

    await client.start(bot_token=settings.bot_token)
    print("telegramonline bot is running.")
    await client.run_until_disconnected()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
