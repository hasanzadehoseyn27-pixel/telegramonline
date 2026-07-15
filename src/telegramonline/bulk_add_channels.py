from __future__ import annotations

"""اضافه‌کردن دسته‌جمعی چند کانال با یک اجرا.

اجرا (از ریشه‌ی پروژه):

    $env:PYTHONPATH="src"
    py -m telegramonline.bulk_add_channels

هر کانال را ثبت، join، و پیام‌های همان روز را بک‌فیل می‌کند. اگر کانالی
از قبل ثبت شده باشد، فقط دوباره فعالش می‌کند (خطا نمی‌دهد).
"""

import asyncio

from telegramonline.collector import add_and_activate_channel
from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env
from telegramonline.storage import connect
from telethon import TelegramClient


# لیست کانال‌هایی که باید اضافه بشن — می‌تونی این لیست رو هر بار عوض کنی.
CHANNELS: list[str] = [
    "autogalerymhmood",
    "ShahryarCars98",
    "nomonehtabriz",
    "autoamirhossein_mehrjo",
    "mehdinademi",
    "autoamiryazd0",
    "titan_khodro",
    "Miniuta_khodro",
    "farzancar1",
    "car_baba",
    "omid_biyabani",
    "auto_sefr_derakhshan",
    "damanicar",
    "aryancar0900",
    "autohiradd",
    "Mehranshahabicar",
    "RezaeiAutoGallery",
    "ArmanKhdro",
    "rezaee_khodro",
    "autoluxkhodaei",
    "BAZARBOZORGEKHODROIRAN",
]


async def run() -> None:
    settings = Settings.from_env()
    conn = connect(settings.database_path)
    proxy = parse_proxy_from_env()
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy)
    await client.start()

    ok, dup, failed = 0, 0, 0
    for username in CHANNELS:
        try:
            result = await add_and_activate_channel(client, conn, username)
            status = result.get("status")
            joined = result.get("joined")
            inserted = result.get("inserted_today", 0)
            if status == "ok" and joined:
                ok += 1
                print(f"✅ {username}: join شد، {inserted} آگهی امروز بک‌فیل شد.")
            elif status == "ok" and not joined:
                failed += 1
                print(f"⚠️ {username}: ثبت شد ولی join نشد (شاید یوزرنیم اشتباهه یا کانال محدودیت داره).")
            else:
                dup += 1
                print(f"↺ {username}: از قبل ثبت بود، دوباره فعال شد.")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"❌ {username}: خطا — {exc}")

    print(f"\nخلاصه: {ok} کانال جدید join شد | {dup} از قبل بود | {failed} مشکل داشت.")
    await client.disconnect()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
