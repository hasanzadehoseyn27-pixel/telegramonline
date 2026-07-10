from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import ParsedAd


SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_message_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_ads_vehicle_price ON ads(vehicle_key, price_million);
CREATE INDEX IF NOT EXISTS idx_ads_status_date ON ads(status, message_date);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_ads(conn: sqlite3.Connection, ads: Iterable[ParsedAd]) -> int:
    rows = [
        (
            ad.source_message_id,
            ad.raw_text,
            ad.normalized_text,
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
            source_message_id, raw_text, normalized_text, message_date, vehicle_key,
            vehicle_name, trim, price_million, year, month, color, mileage_km,
            phone, status, delivery, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


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


def available_vehicles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            vehicle_key,
            vehicle_name,
            COUNT(*) AS total,
            MIN(price_million) AS min_price
        FROM ads
        WHERE
            status = 'sale'
            AND vehicle_key IS NOT NULL
            AND vehicle_name IS NOT NULL
            AND price_million IS NOT NULL
            AND confidence >= 0.55
        GROUP BY vehicle_key, vehicle_name
        ORDER BY vehicle_name COLLATE NOCASE
        """
    ).fetchall()


def lowest_ads_for_vehicle(
    conn: sqlite3.Connection,
    vehicle_key: str,
    limit: int = 10,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM ads
        WHERE
            status = 'sale'
            AND vehicle_key = ?
            AND price_million IS NOT NULL
            AND confidence >= 0.55
        ORDER BY price_million ASC, confidence DESC, id DESC
        LIMIT ?
        """,
        (vehicle_key, limit),
    ).fetchall()


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'sale' THEN 1 ELSE 0 END) AS sale,
            SUM(CASE WHEN vehicle_key IS NOT NULL THEN 1 ELSE 0 END) AS with_vehicle,
            SUM(CASE WHEN price_million IS NOT NULL THEN 1 ELSE 0 END) AS with_price,
            SUM(CASE WHEN status = 'spam' THEN 1 ELSE 0 END) AS spam,
            SUM(CASE WHEN status = 'buyer' THEN 1 ELSE 0 END) AS buyer
        FROM ads
        """
    ).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}
