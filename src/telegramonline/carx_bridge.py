from __future__ import annotations

"""پل بین telegramonline و بک‌اند سایت اصلی (keyvankhodro-back / CarX).

آگهی‌های قیمت‌دار (و آگهی‌های خاص از لیست watched_vehicles) رو به یه API
روی بک‌اند ASP.NET می‌فرسته. دو کاربرد داره:

1. بک‌فیل یک‌باره‌ی «دیروز»:
       $env:PYTHONPATH="src"
       py -m telegramonline.push_yesterday_to_carx

2. فرستادن زنده‌ی هر آگهی تازه (فراخوانی از collector.py هنگام دریافت پیام
   زنده) — با try/except محافظت شده که اگه بک‌اند در دسترس نبود، collector
   کرش نکنه.

تنظیمات لازم توی .env:
    CARX_API_URL=http://localhost:5138/api
    CARX_IMPORT_API_KEY=همون-کلیدی-که-تو-appsettings.json-بک‌اند-گذاشتی
"""

import os
import sqlite3
from typing import Any, Iterable

import httpx

from .storage import list_priced_ads_for_web, list_special_ads, today_day_key, yesterday_day_key


def _source_id(row: sqlite3.Row) -> str:
    channel = row["channel_username"] or "unknown"
    return f"{channel}:{row['source_message_id']}"


def ad_row_to_dto(row: sqlite3.Row, is_special: bool = False) -> dict[str, Any]:
    return {
        "telegramSourceId": _source_id(row),
        "vehicleName": row["vehicle_name"],
        "trim": row["trim"],
        "year": row["year"],
        "color": row["color"],
        "mileageKm": row["mileage_km"],
        "phone": row["phone"],
        "priceMillion": row["price_million"],
        "rawText": row["raw_text"],
        "channelUsername": row["channel_username"],
        "sourceMessageId": row["source_message_id"],
        "status": row["status"],
        "isSpecial": is_special,
    }


def _api_config() -> tuple[str, str] | None:
    base_url = os.getenv("CARX_API_URL", "").strip().rstrip("/")
    api_key = os.getenv("CARX_IMPORT_API_KEY", "").strip()
    if not base_url or not api_key:
        return None
    return base_url, api_key


def push_ads_sync(rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """نسخه‌ی sync — برای اسکریپت‌های یک‌باره (بک‌فیل)."""
    rows = list(rows)
    if not rows:
        return None

    config = _api_config()
    if config is None:
        print("⚠️ CARX_API_URL / CARX_IMPORT_API_KEY تنظیم نشده — از ارسال صرف‌نظر شد.")
        return None
    base_url, api_key = config

    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{base_url}/telegram-import/ads",
            json={"ads": rows},
            headers={"X-Import-Key": api_key},
        )
        response.raise_for_status()
        return response.json()


async def push_ads_async(rows: Iterable[dict[str, Any]]) -> None:
    """نسخه‌ی async — برای فراخوانی از collector.py حین دریافت پیام زنده.

    عمداً هیچ Exception ای رو بالا پرتاب نمی‌کنه؛ اگه بک‌اند در دسترس نبود
    یا خطا داد، فقط لاگ می‌کنه تا collector زنده از کار نیفته.
    """
    rows = list(rows)
    if not rows:
        return

    config = _api_config()
    if config is None:
        return
    base_url, api_key = config

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{base_url}/telegram-import/ads",
                json={"ads": rows},
                headers={"X-Import-Key": api_key},
            )
            if response.status_code >= 400:
                print(f"⚠️ ارسال زنده به CarX ناموفق بود ({response.status_code}): {response.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ ارسال زنده به CarX با خطا مواجه شد: {exc}")


def collect_yesterday_rows(conn: sqlite3.Connection, limit: int = 500) -> list[dict[str, Any]]:
    """آگهی‌های قیمت‌دار + آگهی‌های خاصِ دیروز رو جمع می‌کنه (بدون تکرار)."""
    day_key = yesterday_day_key()

    priced = list_priced_ads_for_web(conn, sort="newest", limit=limit, offset=0, day_key=day_key)
    special = list_special_ads(conn, limit=limit, offset=0, day_key=day_key)

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    for row in special:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=True))

    for row in priced:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=False))

    return rows
