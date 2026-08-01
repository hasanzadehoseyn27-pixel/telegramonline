from __future__ import annotations

"""پل بین telegramonline و بک‌اند سایت اصلی (keyvankhodro-back / CarX).

آگهی‌های قیمت‌دار + خاص (watched_vehicles) + خریدارم رو به یه API روی
بک‌اند ASP.NET می‌فرسته. هر کانال تلگرام اونجا یه پروفایل/نمایشگاه جدا و
خودکار می‌گیره (نه یه اکانت مشترک). دو کاربرد داره:

1. بک‌فیل یک‌باره‌ی امروز/دیروز:
       $env:PYTHONPATH="src"
       py -m telegramonline.push_today_to_carx
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

from .storage import _watched_vehicles_where, today_day_key, yesterday_day_key
from .zero_whitelist import match_zero_whitelist


def _source_id(row: sqlite3.Row) -> str:
    channel = row["channel_username"] or "unknown"
    return f"{channel}:{row['source_message_id']}"


def _channel_titles(conn: sqlite3.Connection) -> dict[str, str]:
    """نقشه‌ی username کانال -> عنوان واقعیش (برای اسم نمایشگاه تو CarX)."""
    rows = conn.execute("SELECT username, title FROM channels").fetchall()
    return {row["username"]: row["title"] for row in rows if row["title"]}


def _query_ads_per_channel(
    conn: sqlite3.Connection,
    day_key: str,
    status_sql: str,
    extra_params: list | None = None,
    limit: int = 20000,
) -> list[sqlite3.Row]:
    """مثل توابع list_*_ads_for_web توی storage.py، ولی به‌جای دی‌ادوپ سراسری
    (PARTITION BY dedup_key)، دی‌ادوپ رو به‌ازای هر کانال جدا انجام می‌ده
    (PARTITION BY channel_username, dedup_key). یعنی اگه یه آگهی هم توی
    کانال خودش، هم توی یه کانال/گروه دیگه (مثلاً بازار بزرگ) پست شده باشه،
    زیر هر دو کانال جدا دیده می‌شه — فقط تکرار داخل خودِ یک کانال حذف می‌شه.
    """
    conn.row_factory = sqlite3.Row
    extra_params = extra_params or []
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY channel_username, dedup_key
                    ORDER BY id DESC
                ) AS rn
            FROM ads
            WHERE day_key = ? AND {status_sql}
        )
        SELECT * FROM matched WHERE rn = 1
        ORDER BY id DESC
        LIMIT ?
        """,
        [day_key, *extra_params, limit],
    ).fetchall()


def ad_row_to_dto(
    row: sqlite3.Row,
    is_special: bool = False,
    channel_titles: dict[str, str] | None = None,
) -> dict[str, Any]:
    channel_username = row["channel_username"]
    channel_title = (channel_titles or {}).get(channel_username or "")

    return {
        "telegramSourceId": _source_id(row),
        "vehicleName": row["vehicle_name"],
        "vehicleKey": match_zero_whitelist(row["vehicle_name"], row["trim"], row["raw_text"]),
        "trim": row["trim"],
        "year": row["year"],
        "color": row["color"],
        "mileageKm": row["mileage_km"],
        "phone": row["phone"],
        "priceMillion": row["price_million"] if "price_million" in row.keys() else None,
        "rawText": row["raw_text"],
        "channelUsername": channel_username,
        "channelTitle": channel_title,
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


def collect_rows_for_day(conn: sqlite3.Connection, day_key: str, limit: int = 20000) -> list[dict[str, Any]]:
    """آگهی‌های قیمت‌دار + بدون‌قیمت + تماس‌بگیرید + خاص + خریدارمِ یه روز
    خاص رو جمع می‌کنه — دی‌ادوپ فقط داخل خودِ هر کانال، نه بین کانال‌ها."""
    channel_titles = _channel_titles(conn)

    priced = _query_ads_per_channel(
        conn, day_key, "status = 'sale' AND price_million IS NOT NULL", limit=limit
    )
    unpriced = _query_ads_per_channel(
        conn, day_key, "status = 'sale' AND price_million IS NULL", limit=limit
    )
    call_price = _query_ads_per_channel(conn, day_key, "status = 'call_price'", limit=limit)
    buyers = _query_ads_per_channel(conn, day_key, "status = 'buyer'", limit=limit)

    watched_clause = _watched_vehicles_where(conn)
    if watched_clause is not None:
        watched_where, watched_params = watched_clause
        special = _query_ads_per_channel(
            conn,
            day_key,
            f"status = 'sale' AND price_million IS NOT NULL AND {watched_where}",
            extra_params=watched_params,
            limit=limit,
        )
    else:
        special = []

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    for row in special:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=True, channel_titles=channel_titles))

    for row in priced:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=False, channel_titles=channel_titles))

    for row in unpriced:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=False, channel_titles=channel_titles))

    for row in call_price:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=False, channel_titles=channel_titles))

    for row in buyers:
        sid = _source_id(row)
        if sid in seen:
            continue
        seen.add(sid)
        rows.append(ad_row_to_dto(row, is_special=False, channel_titles=channel_titles))

    return rows


def collect_yesterday_rows(conn: sqlite3.Connection, limit: int = 20000) -> list[dict[str, Any]]:
    return collect_rows_for_day(conn, yesterday_day_key(), limit=limit)


def collect_today_rows(conn: sqlite3.Connection, limit: int = 20000) -> list[dict[str, Any]]:
    return collect_rows_for_day(conn, today_day_key(), limit=limit)

