from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import ParsedAd
from .normalizer import compact_text


TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    title TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    joined INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER,
    channel_username TEXT,
    source_message_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    dedup_key TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'import',
    message_date TEXT,
    day_key TEXT,
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
    UNIQUE(channel_id, source_message_id, raw_text)
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
CREATE INDEX IF NOT EXISTS idx_ads_day_key ON ads(day_key);
CREATE INDEX IF NOT EXISTS idx_ads_channel ON ads(channel_id);
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
    """اگر دیتابیس قدیمی (بدون این ستون‌ها) باز شود، ستون‌ها را اضافه می‌کند."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(ads)").fetchall()}
    if "dedup_key" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN dedup_key TEXT NOT NULL DEFAULT ''")
    if "source" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN source TEXT NOT NULL DEFAULT 'import'")
    if "channel_id" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN channel_id INTEGER")
    if "channel_username" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN channel_username TEXT")
    if "day_key" not in existing:
        conn.execute("ALTER TABLE ads ADD COLUMN day_key TEXT")
    existing_channels_cols = set()
    try:
        existing_channels_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(channels)").fetchall()
        }
    except sqlite3.OperationalError:
        pass
    if existing_channels_cols and "joined" not in existing_channels_cols:
        conn.execute("ALTER TABLE channels ADD COLUMN joined INTEGER NOT NULL DEFAULT 0")
    conn.commit()


TEHRAN_OFFSET = timedelta(hours=3, minutes=30)


def _compute_day_key(message_date: datetime | None) -> str | None:
    """تاریخ روز (به‌وقت تهران) برای پیام، جهت فیلتر «فقط امروز» و پاک‌سازی شبانه."""
    if message_date is None:
        return None
    if message_date.tzinfo is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    local = message_date.astimezone(timezone.utc) + TEHRAN_OFFSET
    return local.strftime("%Y-%m-%d")


def save_ads(
    conn: sqlite3.Connection,
    ads: Iterable[ParsedAd],
    channel_id: int | None = None,
    channel_username: str | None = None,
) -> int:
    rows = [
        (
            channel_id,
            channel_username,
            ad.source_message_id,
            ad.raw_text,
            ad.normalized_text,
            ad.dedup_key,
            ad.source,
            ad.message_date.isoformat() if ad.message_date else None,
            _compute_day_key(ad.message_date),
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
            channel_id, channel_username, source_message_id, raw_text, normalized_text,
            dedup_key, source, message_date, day_key,
            vehicle_key, vehicle_name, trim, price_million, year, month, color, mileage_km,
            phone, status, delivery, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


# ---------------------------------------------------------------------------
# مدیریت کانال‌ها
# ---------------------------------------------------------------------------

def _clean_username(raw: str) -> str:
    """یوزرنیم کانال را از حالت‌های مختلف ورودی (لینک کامل، با @، بدون @) یکسان می‌کند."""
    value = raw.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "@"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    return value.strip().rstrip("/")


def add_channel(conn: sqlite3.Connection, username: str, title: str | None = None) -> int | None:
    """کانال جدید اضافه می‌کند. اگر تکراری باشد None برمی‌گرداند."""
    clean = _clean_username(username)
    if not clean:
        return None
    try:
        cursor = conn.execute(
            "INSERT INTO channels (username, title) VALUES (?, ?)",
            (clean, title),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def delete_ads_by_channel_username(conn: sqlite3.Connection, username: str) -> int:
    """پاک‌سازی دستی آگهی‌های یک یوزرنیم — برای کانال‌هایی که قبل از این اصلاح حذف شدند."""
    clean = _clean_username(username)
    before = conn.total_changes
    conn.execute("DELETE FROM ads WHERE channel_username = ?", (clean,))
    conn.commit()
    return conn.total_changes - before


def delete_ads_for_channel(conn: sqlite3.Connection, channel_id: int) -> int:
    """همه آگهی‌های یک کانال را پاک می‌کند (وقتی کانال کامل حذف می‌شود)."""
    before = conn.total_changes
    conn.execute("DELETE FROM ads WHERE channel_id = ?", (channel_id,))
    conn.commit()
    return conn.total_changes - before


def remove_channel(conn: sqlite3.Connection, channel_id: int) -> bool:
    cursor = conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    return cursor.rowcount > 0


def deactivate_channel(conn: sqlite3.Connection, channel_id: int) -> bool:
    """کانال را برای حذف نشانه‌گذاری می‌کند.

    حذف واقعی (هم از دیتابیس هم خروج از عضویت تلگرام) را collector.py با
    اکانت شخصی انجام می‌دهد (چون فقط او می‌تواند LeaveChannelRequest بزند)؛
    اینجا فقط active=0 می‌شود تا هندلر پیام زنده هم فوراً پردازشش را متوقف کند.
    """
    cursor = conn.execute("UPDATE channels SET active = 0 WHERE id = ?", (channel_id,))
    conn.commit()
    return cursor.rowcount > 0


def list_channels_pending_leave(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """کانال‌هایی که غیرفعال شده‌اند ولی اکانت هنوز واقعاً از آن‌ها خارج نشده."""
    return conn.execute("SELECT * FROM channels WHERE active = 0 AND joined = 1").fetchall()


def get_channel(conn: sqlite3.Connection, channel_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()


def get_channel_by_username(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    clean = _clean_username(username)
    return conn.execute("SELECT * FROM channels WHERE username = ?", (clean,)).fetchone()


def list_unjoined_channels(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """کانال‌هایی که فقط ثبت شده‌اند ولی هنوز اکانت تلگرام عضوشان نشده."""
    return conn.execute(
        "SELECT * FROM channels WHERE active = 1 AND joined = 0 ORDER BY added_at"
    ).fetchall()


def list_active_joined_channels(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM channels WHERE active = 1 AND joined = 1 ORDER BY added_at"
    ).fetchall()


def mark_channel_joined(conn: sqlite3.Connection, channel_id: int, title: str | None = None) -> None:
    conn.execute(
        "UPDATE channels SET joined = 1, title = COALESCE(?, title) WHERE id = ?",
        (title, channel_id),
    )
    conn.commit()


def list_channels(conn: sqlite3.Connection, today_only: bool = True) -> list[dict]:
    """لیست کانال‌ها همراه با تعداد پیام‌های امروزشان."""
    today = _compute_day_key(datetime.now(timezone.utc))
    channels = conn.execute("SELECT * FROM channels ORDER BY added_at").fetchall()
    result = []
    for ch in channels:
        if today_only:
            count_row = conn.execute(
                "SELECT COUNT(*) AS c FROM ads WHERE channel_id = ? AND day_key = ?",
                (ch["id"], today),
            ).fetchone()
        else:
            count_row = conn.execute(
                "SELECT COUNT(*) AS c FROM ads WHERE channel_id = ?",
                (ch["id"],),
            ).fetchone()
        result.append(
            {
                "id": ch["id"],
                "username": ch["username"],
                "title": ch["title"],
                "active": bool(ch["active"]),
                "joined": bool(ch["joined"]),
                "added_at": ch["added_at"],
                "message_count": int(count_row["c"] or 0),
            }
        )
    return result


def total_messages_today(conn: sqlite3.Connection) -> int:
    """مجموع پیام‌های امروز روی همه‌ی کانال‌ها (برای نمایش در لیست کانال‌ها)."""
    today = _compute_day_key(datetime.now(timezone.utc))
    row = conn.execute("SELECT COUNT(*) AS c FROM ads WHERE day_key = ?", (today,)).fetchone()
    return int(row["c"] or 0)


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


def purge_old_ads(conn: sqlite3.Connection) -> int:
    """فقط امروز و دیروز نگه می‌دارد؛ هر چیز قدیمی‌تر (یا بدون تاریخ) حذف می‌شود.

    قرار است هر شب حوالی نیمه‌شب به‌وقت تهران اجرا شود (توسط collector.py).
    """
    cutoff = yesterday_day_key()
    before = conn.total_changes
    conn.execute("DELETE FROM ads WHERE day_key IS NULL OR day_key < ?", (cutoff,))
    conn.commit()
    conn.execute("VACUUM")
    return conn.total_changes - before


def today_day_key() -> str:
    return _compute_day_key(datetime.now(timezone.utc))


def yesterday_day_key() -> str:
    return _compute_day_key(datetime.now(timezone.utc) - timedelta(days=1))


def search_priced_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """آگهی‌های ارزان‌تر (با قیمت) همان روز که متن‌شان شامل نام واردشده است.

    پیش‌فرض «امروز» است؛ برای گزارش دیروز می‌توان day_key را صریح داد.
    آگهی‌های با dedup_key یکسان (همان آگهی با فاصله‌گذاری متفاوت) فقط یک بار می‌آیند.
    """
    day_key = day_key or today_day_key()
    like_where, params = _search_filters(query)
    params_all = [day_key] + params + [limit, offset]
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
                AND day_key = ?
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
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """آگهی‌های فروش بدون قیمت همان روز که متن‌شان شامل نام واردشده است (جدیدترین اول)."""
    day_key = day_key or today_day_key()
    like_where, params = _search_filters(query)
    params_all = [day_key] + params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY message_date IS NULL, message_date DESC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND price_million IS NULL
                AND day_key = ?
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY message_date IS NULL, message_date DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def search_today_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """همه آگهی‌های امروز (با یا بدون قیمت) که متن‌شان شامل نام واردشده است."""
    day_key = day_key or today_day_key()
    like_where, params = _search_filters(query)
    params_all = [day_key] + params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY message_date IS NULL, message_date DESC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND day_key = ?
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY message_date IS NULL, message_date DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def search_buyer_ads(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 10,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """پیام‌های «خریدارم/دنبال ... هستم» همان روز که متن‌شان شامل نام واردشده است."""
    day_key = day_key or today_day_key()
    like_where, params = _search_filters(query)
    params_all = [day_key] + params + [limit, offset]
    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY message_date IS NULL, message_date DESC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'buyer'
                AND day_key = ?
                AND {like_where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY message_date IS NULL, message_date DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        params_all,
    ).fetchall()


def count_search_results(conn: sqlite3.Connection, query: str, day_key: str | None = None) -> dict[str, int]:
    """تعداد نتایج با‌قیمت/بدون‌قیمت/امروز/خریدار (همه محدود به همان روز) برای دکمه‌ها."""
    day_key = day_key or today_day_key()
    like_where, params = _search_filters(query)
    row = conn.execute(
        f"""
        SELECT
            COUNT(DISTINCT CASE WHEN price_million IS NOT NULL THEN dedup_key END) AS priced,
            COUNT(DISTINCT CASE WHEN price_million IS NULL THEN dedup_key END) AS unpriced
        FROM ads
        WHERE status = 'sale' AND day_key = ? AND {like_where}
        """,
        [day_key] + params,
    ).fetchone()
    today_row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT dedup_key) AS today
        FROM ads
        WHERE status = 'sale' AND day_key = ? AND {like_where}
        """,
        [day_key] + params,
    ).fetchone()
    buyer_row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT dedup_key) AS buyers
        FROM ads
        WHERE status = 'buyer' AND day_key = ? AND {like_where}
        """,
        [day_key] + params,
    ).fetchone()
    return {
        "priced": int(row["priced"] or 0),
        "unpriced": int(row["unpriced"] or 0),
        "today": int(today_row["today"] or 0),
        "buyers": int(buyer_row["buyers"] or 0),
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