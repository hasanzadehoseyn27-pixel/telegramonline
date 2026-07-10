from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import ParsedAd
from .normalizer import compact_text


TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_message_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    dedup_key TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'import',
    message_date TEXT,
    vehicle_key TEXT,
    vehicle_name TEXT,
    trim TEXT,
    price_million INTEGER,
    year INTEGER,
    month INTEGER,
    color TEXT,
    mileage_km INTEGER,
    phone TEXT,
    status TEXT NOT NULL,
    delivery TEXT,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_message_id, raw_text)
);

CREATE TABLE IF NOT EXISTS user_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_ads_vehicle_price ON ads(vehicle_key, price_million);
CREATE INDEX IF NOT EXISTS idx_ads_status_date ON ads(status, message_date);
CREATE INDEX IF NOT EXISTS idx_ads_status_price ON ads(status, price_million);
CREATE INDEX IF NOT EXISTS idx_ads_dedup ON ads(dedup_key);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(TABLE_SCHEMA)
    _ensure_columns(conn)
    conn.executescript(INDEX_SCHEMA)
    return conn


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """اگر دیتابیس قدیمی (بدون dedup_key/source) باز شود، ستون‌ها را اضافه می‌کند."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(ads)").fetchall()}
    if "dedup_key" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN dedup_key TEXT NOT NULL DEFAULT ''")
    if "source" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN source TEXT NOT NULL DEFAULT 'import'")
    conn.commit()


def save_ads(conn: sqlite3.Connection, ads: Iterable[ParsedAd]) -> int:
    rows = [
        (
            ad.source_message_id,
            ad.raw_text,
            ad.normalized_text,
            ad.dedup_key,
            ad.source,
            ad.message_date.isoformat() if ad.message_date else None,
            ad.vehicle_key,
            ad.vehicle_name,
            ad.trim,
            ad.price_million,
            ad.year,
            ad.month,
            ad.color,
            ad.mileage_km,
            ad.phone,
            ad.status,
            ad.delivery,
            ad.confidence,
        )
        for ad in ads
    ]
    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO ads (
            source_message_id, raw_text, normalized_text, dedup_key, source, message_date,
            vehicle_key, vehicle_name, trim, price_million, year, month, color, mileage_km,
            phone, status, delivery, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


# ---------------------------------------------------------------------------
# لیست ماشین‌های دستی کاربر
# ---------------------------------------------------------------------------

def add_user_vehicle(conn: sqlite3.Connection, name: str) -> bool:
    """ماشین جدید به لیست کاربر اضافه می‌کند. اگر تکراری باشد False برمی‌گرداند."""
    display = name.strip()
    normalized = compact_text(display)
    if not normalized:
        return False
    try:
        conn.execute(
            "INSERT INTO user_vehicles (name, normalized_name) VALUES (?, ?)",
            (display, normalized),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_user_vehicle(conn: sqlite3.Connection, vehicle_id: int) -> bool:
    cursor = conn.execute("DELETE FROM user_vehicles WHERE id = ?", (vehicle_id,))
    conn.commit()
    return cursor.rowcount > 0


def list_user_vehicles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name, normalized_name FROM user_vehicles ORDER BY name COLLATE NOCASE"
    ).fetchall()


def get_user_vehicle(conn: sqlite3.Connection, vehicle_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, normalized_name FROM user_vehicles WHERE id = ?",
        (vehicle_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# جست‌وجوی متنی آگهی‌ها بر اساس نام ماشینی که کاربر وارد کرده
# ---------------------------------------------------------------------------

def _search_filters(query: str) -> tuple[str, list[object]]:
    """کوئری کاربر را نرمال می‌کند و شرط LIKE می‌سازد.

    چند کلمه با فاصله => همه باید در متن باشند (AND).
    """
    normalized = compact_text(query)
    words = [w for w in normalized.split(" ") if w]
    conditions = []
    params: list[object] = []
    for word in words:
        conditions.append("normalized_text LIKE ?")
        params.append(f"%{word}%")
    if not conditions:
        conditions.append("1=0")
    return " AND ".join(conditions), params


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def search_priced_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """آگهی‌های ارزان‌تر (با قیمت) که متن‌شان شامل نام واردشده توسط کاربر است.

    آگهی‌های با dedup_key یکسان (همان آگهی با فاصله‌گذاری متفاوت) فقط یک بار می‌آیند.
    """
    like_where, params = _search_filters(query)
    params_all = params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY price_million ASC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND price_million IS NOT NULL
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY price_million ASC, id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def search_unpriced_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """آگهی‌های فروش بدون قیمت که متن‌شان شامل نام واردشده است (جدیدترین اول)."""
    like_where, params = _search_filters(query)
    params_all = params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND price_million IS NULL
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def search_today_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """همه آگهی‌های امروز (با یا بدون قیمت) که متن‌شان شامل نام واردشده است.

    فقط روی آگهی‌هایی کار می‌کند که message_date واقعی دارند (یعنی زنده از گروه
    جمع شده‌اند، نه از فایل export قدیمی که تاریخ ندارد).
    """
    like_where, params = _search_filters(query)
    params_all = [_today_start_iso()] + params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND message_date IS NOT NULL
                AND message_date >= ?
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def count_search_results(conn: sqlite3.Connection, query: str) -> dict[str, int]:
    """تعداد نتایج با‌قیمت/بدون‌قیمت/امروز برای نمایش روی دکمه‌ها."""
    like_where, params = _search_filters(query)
    row = conn.execute(
        f"""
        SELECT
            COUNT(DISTINCT CASE WHEN price_million IS NOT NULL THEN dedup_key END) AS priced,
            COUNT(DISTINCT CASE WHEN price_million IS NULL THEN dedup_key END) AS unpriced
        FROM ads
        WHERE status = 'sale' AND {like_where}
        """,
        params,
    ).fetchone()
    today_row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT dedup_key) AS today
        FROM ads
        WHERE status = 'sale' AND message_date IS NOT NULL AND message_date >= ? AND {like_where}
        """,
        [_today_start_iso()] + params,
    ).fetchone()
    return {
        "priced": int(row["priced"] or 0),
        "unpriced": int(row["unpriced"] or 0),
        "today": int(today_row["today"] or 0),
    }


# ---------------------------------------------------------------------------
# توابع قبلی (برای سازگاری با query.py)
# ---------------------------------------------------------------------------

def lowest_by_vehicle(
    conn: sqlite3.Connection,
    days: int | None = None,
    limit: int = 20,
    vehicle_query: str | None = None,
) -> list[sqlite3.Row]:
    filters = [
        "status = 'sale'",
        "vehicle_key IS NOT NULL",
        "price_million IS NOT NULL",
        "confidence >= 0.55",
    ]
    params: list[object] = []
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filters.append("(message_date IS NULL OR message_date >= ?)")
        params.append(cutoff.isoformat())
    if vehicle_query:
        filters.append("(vehicle_name LIKE ? OR normalized_text LIKE ?)")
        like = f"%{vehicle_query}%"
        params.extend([like, like])
    where = " AND ".join(filters)
    params.append(limit)
    return conn.execute(
        f"""
        WITH ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY vehicle_key
                    ORDER BY price_million ASC, confidence DESC, id DESC
                ) AS rn
            FROM ads
            WHERE {where}
        )
        SELECT * FROM ranked
        WHERE rn = 1
        ORDER BY price_million ASC
        LIMIT ?
        """,
        params,
    ).fetchall()


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'sale' THEN 1 ELSE 0 END) AS sale,
            SUM(CASE WHEN status = 'sale' AND price_million IS NOT NULL THEN 1 ELSE 0 END) AS with_price,
            SUM(CASE WHEN status = 'sale' AND price_million IS NULL THEN 1 ELSE 0 END) AS without_price,
            SUM(CASE WHEN status = 'spam' THEN 1 ELSE 0 END) AS spam,
            SUM(CASE WHEN status = 'buyer' THEN 1 ELSE 0 END) AS buyer,
            SUM(CASE WHEN source = 'live' THEN 1 ELSE 0 END) AS live_collected
        FROM ads
        """
    ).fetchone()
    result = {key: int(row[key] or 0) for key in row.keys()}
    result["saved_vehicles"] = int(
        conn.execute("SELECT COUNT(*) FROM user_vehicles").fetchone()[0]
    )
    return result