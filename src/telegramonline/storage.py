from __future__ import annotations

import sqlite3

import jdatetime
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .models import ParsedAd
from .normalizer import compact_text
from .parser import known_vehicle_options


TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    title TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    joined INTEGER NOT NULL DEFAULT 0,
    join_attempts INTEGER NOT NULL DEFAULT 0,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    title TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    joined INTEGER NOT NULL DEFAULT 0,
    join_attempts INTEGER NOT NULL DEFAULT 0,
    discovered_channels INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    vehicle_key TEXT NOT NULL,
    vehicle_name TEXT,

    condition TEXT NOT NULL,

    min_price INTEGER,
    max_price INTEGER,

    active INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    alert_id INTEGER NOT NULL,

    ad_id INTEGER NOT NULL,

    vehicle_key TEXT,

    price_million INTEGER,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(alert_id, ad_id)
);
"""


INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_ads_vehicle_price
ON ads(vehicle_key, price_million);

CREATE INDEX IF NOT EXISTS idx_ads_status_date
ON ads(status, message_date);

CREATE INDEX IF NOT EXISTS idx_ads_status_price
ON ads(status, price_million);

CREATE INDEX IF NOT EXISTS idx_ads_dedup
ON ads(dedup_key);

CREATE INDEX IF NOT EXISTS idx_ads_day_key
ON ads(day_key);

CREATE INDEX IF NOT EXISTS idx_ads_channel
ON ads(channel_id);

CREATE INDEX IF NOT EXISTS idx_price_alert_vehicle
ON price_alerts(vehicle_key);

CREATE INDEX IF NOT EXISTS idx_price_alert_active
ON price_alerts(active);

CREATE INDEX IF NOT EXISTS idx_alert_events_alert
ON alert_events(alert_id);

CREATE INDEX IF NOT EXISTS idx_alert_events_ad
ON alert_events(ad_id);
"""

def connect(db_path: str | Path) -> sqlite3.Connection:
    """اتصال «کامل»: اسکیما/ایندکس‌ها/مهاجرت ستون‌ها را هم تضمین می‌کند.

    برای استفاده‌ی یک‌باره در شروع برنامه (API startup) یا فرآیندهای
    تک‌رشته‌ای مثل collector.py مناسب است. برای هر ریکوئست وب از
    connect_for_request استفاده کن که سبک‌تر و thread-safe است.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(TABLE_SCHEMA)
    _ensure_columns(conn)
    conn.executescript(INDEX_SCHEMA)
    return conn


def ensure_schema(db_path: str | Path) -> None:
    """فقط اسکیما/مهاجرت را تضمین می‌کند (بدون نگه‌داشتن کانکشن باز).

    باید یک‌بار موقع بالا آمدن API صدا زده شود.
    """
    connect(db_path).close()


def connect_for_request(db_path: str | Path) -> sqlite3.Connection:
    """اتصال سبک برای هر ریکوئست FastAPI.

    FastAPI دیپندنسی‌های sync generator را داخل یک thread pool اجرا می‌کند
    و ورود/خروج generator ممکن است روی دو OS thread متفاوت اتفاق بیفتد؛
    چون هر کانکشن فقط در طول یک ریکوئست استفاده می‌شود (هیچ‌وقت هم‌زمان
    بین دو ریکوئست به اشتراک گذاشته نمی‌شود)، غیرفعال‌کردن چک
    same-thread اینجا امن است و از خطای
    «SQLite objects created in a thread can only be used in that same thread»
    جلوگیری می‌کند. اسکیما را دوباره نمی‌سازد (چون در startup ساخته شده).
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
    if existing_channels_cols and "join_attempts" not in existing_channels_cols:
        conn.execute("ALTER TABLE channels ADD COLUMN join_attempts INTEGER NOT NULL DEFAULT 0")
    existing_groups_cols = set()
    try:
        existing_groups_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(source_groups)").fetchall()
        }
    except sqlite3.OperationalError:
        pass
    if existing_groups_cols and "joined" not in existing_groups_cols:
        conn.execute("ALTER TABLE source_groups ADD COLUMN joined INTEGER NOT NULL DEFAULT 0")
    if existing_groups_cols and "discovered_channels" not in existing_groups_cols:
        conn.execute("ALTER TABLE source_groups ADD COLUMN discovered_channels INTEGER NOT NULL DEFAULT 0")
    if existing_groups_cols and "join_attempts" not in existing_groups_cols:
        conn.execute("ALTER TABLE source_groups ADD COLUMN join_attempts INTEGER NOT NULL DEFAULT 0")
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




def format_shamsi_datetime(
    message_date: str | datetime | None,
) -> str | None:
    """
    تبدیل تاریخ پیام به تاریخ و ساعت شمسی قابل نمایش در سایت.

    خروجی:
    ۱۴۰۵/۰۴/۲۴ - ۱۴:۴۳
    """

    if not message_date:
        return None

    try:
        if isinstance(message_date, str):
            dt = datetime.fromisoformat(
                message_date.replace("Z", "+00:00")
            )
        else:
            dt = message_date

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        local = (
            dt.astimezone(timezone.utc)
            + TEHRAN_OFFSET
        )

        jalali = jdatetime.datetime.fromgregorian(
            datetime=local.replace(tzinfo=None)
        )

        return (
            f"{jalali.year:04d}/"
            f"{jalali.month:02d}/"
            f"{jalali.day:02d}"
            f" - "
            f"{jalali.hour:02d}:"
            f"{jalali.minute:02d}"
        )

    except Exception:
        return None


def save_ads(
    conn: sqlite3.Connection,
    ads: Iterable[ParsedAd],
    channel_id: int | None = None,
    channel_username: str | None = None,
) -> list[sqlite3.Row]:
    """
    ذخیره آگهی‌ها و برگرداندن آگهی‌های تازه ذخیره‌شده با id واقعی دیتابیس.

    این id برای سیستم هشدار قیمت لازم است تا alert_events
    دقیقاً به رکورد ads وصل شود.
    """

    saved_ads: list[sqlite3.Row] = []

    for ad in ads:

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO ads (
                channel_id,
                channel_username,
                source_message_id,
                raw_text,
                normalized_text,
                dedup_key,
                source,
                message_date,
                day_key,
                vehicle_key,
                vehicle_name,
                trim,
                price_million,
                year,
                month,
                color,
                mileage_km,
                phone,
                status,
                delivery,
                confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                channel_id,
                channel_username,
                ad.source_message_id,
                ad.raw_text,
                ad.normalized_text,
                ad.dedup_key,
                ad.source,
                ad.message_date.isoformat()
                if ad.message_date
                else None,
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
            ),
        )

        conn.commit()


        # اگر آگهی جدید واقعاً ذخیره شد
        if cursor.rowcount > 0:

            row = conn.execute(
                """
                SELECT *
                FROM ads
                WHERE rowid = last_insert_rowid()
                """
            ).fetchone()

            if row:
                saved_ads.append(row)


    return saved_ads


# ---------------------------------------------------------------------------
# مدیریت کانال‌ها
# ---------------------------------------------------------------------------

def _clean_username(raw: str) -> str:
    """یوزرنیم کانال را از حالت‌های مختلف ورودی (لینک کامل، با @، بدون @) یکسان می‌کند."""
    value = raw.strip()
    for prefix in (
    "https://t.me/",
    "http://t.me/",
    "t.me/",
    "https://telegram.me/",
    "http://telegram.me/",
    "telegram.me/",
    "@",
):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    return value.strip().rstrip("/")


def add_channel(conn: sqlite3.Connection, username: str, title: str | None = None) -> int | None:
    """کانال جدید اضافه می‌کند. اگر تکراری بود، همون رکورد موجود را فعال می‌کند."""
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
        row = conn.execute("SELECT id FROM channels WHERE username = ?", (clean,)).fetchone()
        if row:
            conn.execute("UPDATE channels SET active = 1 WHERE id = ?", (row["id"],))
            conn.commit()
            return row["id"]
        return None


def add_source_group(conn: sqlite3.Connection, username: str, title: str | None = None) -> int | None:
    clean = _clean_username(username)
    if not clean:
        return None
    try:
        cursor = conn.execute(
            "INSERT INTO source_groups (username, title) VALUES (?, ?)",
            (clean, title),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT id FROM source_groups WHERE username = ?", (clean,)).fetchone()
        if row:
            conn.execute("UPDATE source_groups SET active = 1 WHERE id = ?", (row["id"],))
            conn.commit()
            return row["id"]
        return None


def get_source_group(conn: sqlite3.Connection, group_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM source_groups WHERE id = ?", (group_id,)).fetchone()


def get_source_group_by_username(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    clean = _clean_username(username)
    return conn.execute("SELECT * FROM source_groups WHERE username = ?", (clean,)).fetchone()


def deactivate_source_group(conn: sqlite3.Connection, group_id: int) -> bool:
    cursor = conn.execute("UPDATE source_groups SET active = 0 WHERE id = ?", (group_id,))
    conn.commit()
    return cursor.rowcount > 0


def remove_source_group(conn: sqlite3.Connection, group_id: int) -> bool:
    cursor = conn.execute("DELETE FROM source_groups WHERE id = ?", (group_id,))
    conn.commit()
    return cursor.rowcount > 0


def list_unjoined_source_groups(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM source_groups WHERE active = 1 AND joined = 0 ORDER BY added_at"
    ).fetchall()


def list_source_groups_pending_leave(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM source_groups WHERE active = 0 AND joined = 1 ORDER BY added_at"
    ).fetchall()


def list_active_joined_source_groups(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM source_groups WHERE active = 1 AND joined = 1 ORDER BY added_at"
    ).fetchall()


def mark_source_group_joined(conn: sqlite3.Connection, group_id: int, title: str | None = None) -> None:
    conn.execute(
        "UPDATE source_groups SET joined = 1, join_attempts = 0, title = COALESCE(?, title) WHERE id = ?",
        (title, group_id),
    )
    conn.commit()


def increment_source_group_join_attempts(conn: sqlite3.Connection, group_id: int) -> int:
    conn.execute(
        "UPDATE source_groups SET join_attempts = join_attempts + 1 WHERE id = ?",
        (group_id,),
    )
    conn.commit()
    row = conn.execute("SELECT join_attempts FROM source_groups WHERE id = ?", (group_id,)).fetchone()
    return int(row["join_attempts"]) if row else 0


def increment_source_group_discovered(conn: sqlite3.Connection, username: str) -> None:
    clean = _clean_username(username)
    conn.execute(
        "UPDATE source_groups SET discovered_channels = discovered_channels + 1 WHERE username = ?",
        (clean,),
    )
    conn.commit()


def list_source_groups(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM source_groups ORDER BY added_at DESC").fetchall()
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "title": row["title"],
            "active": bool(row["active"]),
            "joined": bool(row["joined"]),
            "discovered_channels": int(row["discovered_channels"] or 0),
            "added_at": row["added_at"],
        }
        for row in rows
    ]


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
        "UPDATE channels SET joined = 1, join_attempts = 0, title = COALESCE(?, title) WHERE id = ?",
        (title, channel_id),
    )
    conn.commit()


def increment_channel_join_attempts(conn: sqlite3.Connection, channel_id: int) -> int:
    """شمارنده‌ی تلاش‌های ناموفق join را یکی زیاد می‌کند و مقدار جدید را برمی‌گرداند."""
    conn.execute(
        "UPDATE channels SET join_attempts = join_attempts + 1 WHERE id = ?",
        (channel_id,),
    )
    conn.commit()
    row = conn.execute("SELECT join_attempts FROM channels WHERE id = ?", (channel_id,)).fetchone()
    return int(row["join_attempts"]) if row else 0


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

def get_live_channel_stats(
    conn: sqlite3.Connection,
) -> dict:
    """
    آمار لحظه‌ای کانال‌ها برای داشبورد سایت.
    """

    today = today_day_key()


    channels = conn.execute(
        """
        SELECT
            id,
            username,
            title,
            active,
            joined,
            added_at

        FROM channels

        ORDER BY added_at DESC
        """
    ).fetchall()


    result = []


    for channel in channels:

        count = conn.execute(
            """
            SELECT COUNT(*) AS c

            FROM ads

            WHERE
                channel_id = ?
                AND day_key = ?
            """,
            (
                channel["id"],
                today,
            ),
        ).fetchone()


        result.append(
            {
                "id": channel["id"],
                "username": channel["username"],
                "title": channel["title"],
                "active": bool(channel["active"]),
                "joined": bool(channel["joined"]),
                "today_messages": int(count["c"] or 0),
                "added_at": channel["added_at"],
            }
        )


    total_today = conn.execute(
        """
        SELECT COUNT(*) AS c

        FROM ads

        WHERE day_key = ?
        """,
        (today,),
    ).fetchone()


    return {
        "channels": result,

        "summary": {
            "active_channels": len(
                [
                    x
                    for x in result
                    if x["active"]
                ]
            ),

            "messages_today": int(
                total_today["c"] or 0
            ),
        },
    }


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
# مدیریت هشدار قیمت
# ---------------------------------------------------------------------------

def create_price_alert(
    conn: sqlite3.Connection,
    user_id: int,
    vehicle_key: str,
    vehicle_name: str | None,
    condition: str,
    min_price: int | None = None,
    max_price: int | None = None,
) -> int:

    """
    ساخت هشدار قیمت جدید.

    اگر هشدار مشابه قبلاً وجود داشته باشد،
    همان id قبلی برگردانده می‌شود.
    """

    existing = conn.execute(
        """
        SELECT id
        FROM price_alerts
        WHERE
            user_id = ?
            AND vehicle_key = ?
            AND condition = ?
            AND (
                min_price IS ?
                OR min_price = ?
            )
            AND (
                max_price IS ?
                OR max_price = ?
            )
            AND active = 1
        """,
        (
            user_id,
            vehicle_key,
            condition,
            min_price,
            min_price,
            max_price,
            max_price,
        ),
    ).fetchone()


    if existing:
        return int(existing["id"])


    cursor = conn.execute(
        """
        INSERT INTO price_alerts (
            user_id,
            vehicle_key,
            vehicle_name,
            condition,
            min_price,
            max_price
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            vehicle_key,
            vehicle_name,
            condition,
            min_price,
            max_price,
        ),
    )

    conn.commit()

    return cursor.lastrowid


def list_price_alerts(
    conn: sqlite3.Connection,
    user_id: int,
) -> list[sqlite3.Row]:
    """
    لیست هشدارهای یک کاربر.
    """

    return conn.execute(
        """
        SELECT *
        FROM price_alerts
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()


def get_price_alert(
    conn: sqlite3.Connection,
    alert_id: int,
) -> sqlite3.Row | None:
    """
    گرفتن یک هشدار با id.
    """

    return conn.execute(
        """
        SELECT *
        FROM price_alerts
        WHERE id = ?
        """,
        (alert_id,),
    ).fetchone()


def delete_price_alert(
    conn: sqlite3.Connection,
    alert_id: int,
) -> bool:
    """
    حذف هشدار.
    """

    cursor = conn.execute(
        """
        DELETE FROM price_alerts
        WHERE id = ?
        """,
        (alert_id,),
    )

    conn.commit()

    return cursor.rowcount > 0


def toggle_price_alert(
    conn: sqlite3.Connection,
    alert_id: int,
) -> bool:
    """
    تغییر وضعیت فعال/غیرفعال هشدار.
    """

    cursor = conn.execute(
        """
        UPDATE price_alerts
        SET active =
            CASE
                WHEN active = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
        """,
        (alert_id,),
    )

    conn.commit()

    return cursor.rowcount > 0

def check_price_alerts(
    conn: sqlite3.Connection,
    ads: Iterable[sqlite3.Row],
) -> list[sqlite3.Row]:
    """
    بررسی آگهی‌های جدید با هشدارهای فعال.

    خروجی:
    لیست هشدارهایی که فعال شده‌اند.
    """

    triggered = []

    alerts = conn.execute(
        """
        SELECT *
        FROM price_alerts
        WHERE active = 1
        """
    ).fetchall()

  # ---------------------------------------------------------------------------
# بررسی هشدارهای قیمت
# ---------------------------------------------------------------------------
def check_price_alerts(
    conn: sqlite3.Connection,
    ads: Iterable[sqlite3.Row],
) -> list[sqlite3.Row]:
    """
    بررسی آگهی‌های جدید با هشدارهای فعال.

    اگر شرط یک هشدار برقرار شود:
    - داخل alert_events ذخیره می‌شود
    - آگهی در خروجی برگردانده می‌شود
    """

    triggered = []

    alerts = conn.execute(
        """
        SELECT *
        FROM price_alerts
        WHERE active = 1
        """
    ).fetchall()


    for ad in ads:

        if not ad["vehicle_key"]:
            continue

        if ad["price_million"] is None:
            continue


        for alert in alerts:

            if alert["vehicle_key"] != ad["vehicle_key"]:
                continue


            matched = False

            price = ad["price_million"]

            condition = alert["condition"]


            if condition == "below":

                matched = (
                    alert["min_price"] is not None
                    and price < alert["min_price"]
                )


            elif condition == "above":

                matched = (
                    alert["max_price"] is not None
                    and price > alert["max_price"]
                )


            elif condition == "between":

                matched = (
                    alert["min_price"] is not None
                    and alert["max_price"] is not None
                    and alert["min_price"] <= price <= alert["max_price"]
                )


            if not matched:
                continue


            try:

                conn.execute(
                    """
                    INSERT OR IGNORE INTO alert_events (
                        alert_id,
                        ad_id,
                        vehicle_key,
                        price_million
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        alert["id"],
                        ad["id"],
                        ad["vehicle_key"],
                        price,
                    ),
                )

                conn.commit()

                triggered.append(ad)


            except Exception:
                continue


    return triggered



# ---------------------------------------------------------------------------
# مدیریت رخدادهای هشدار قیمت
# ---------------------------------------------------------------------------

def list_alert_events(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """
    لیست آخرین هشدارهای فعال‌شده.
    """

    return conn.execute(
        """
        SELECT
            ae.*,
            pa.vehicle_name,
            pa.condition,
            pa.user_id,
            ads.raw_text,
            ads.channel_username,
            ads.source_message_id

        FROM alert_events ae

        LEFT JOIN price_alerts pa
            ON pa.id = ae.alert_id

        LEFT JOIN ads
            ON ads.id = ae.ad_id

        ORDER BY ae.created_at DESC

        LIMIT ?
        OFFSET ?
        """,
        (
            limit,
            offset,
        ),
    ).fetchall()



def count_alert_events(
    conn: sqlite3.Connection,
) -> int:
    """
    تعداد کل رخدادهای هشدار.
    """

    row = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM alert_events
        """
    ).fetchone()

    return int(row["c"] or 0)

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

def get_ad_by_id(
    conn: sqlite3.Connection,
    ad_id: int,
) -> sqlite3.Row | None:
    """
    دریافت یک آگهی کامل برای نمایش Modal.
    """

    return conn.execute(
        """
        SELECT *
        FROM ads
        WHERE id = ?
        """,
        (ad_id,),
    ).fetchone()


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


def cheapest_by_vehicle(conn: sqlite3.Connection, day_key: str | None = None) -> list[sqlite3.Row]:
    """ارزان‌ترین آگهی هر مدل خودرو (بر اساس vehicle_key) در یک روز مشخص.

    فقط مدل‌هایی که پارسر تشخیص داده (vehicle_key ست شده) در گزارش می‌آیند؛
    آگهی‌های بدون مدل مشخص (که تعدادشان کم نیست) در این گزارش نمی‌آیند.
    """
    day_key = day_key or today_day_key()
    return conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY vehicle_key
                    ORDER BY price_million ASC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND price_million IS NOT NULL
                AND vehicle_key IS NOT NULL
                AND day_key = ?
        )
        SELECT * FROM ranked
        WHERE rn = 1
        ORDER BY vehicle_name COLLATE NOCASE
        """,
        (day_key,),
    ).fetchall()

def get_filter_options_for_web(
    conn: sqlite3.Connection,
    day_key: str | None = None,
) -> dict:
    """گزینه‌های فیلتر برای فرانت‌اند وب، بر اساس آگهی‌های همان روز."""
    day_key = day_key or today_day_key()

    vehicle_rows = conn.execute(
        """
        SELECT vehicle_key, vehicle_name, COUNT(DISTINCT dedup_key) AS count
        FROM ads
        WHERE
            day_key = ?
            AND status = 'sale'
            AND vehicle_key IS NOT NULL
            AND vehicle_name IS NOT NULL
        GROUP BY vehicle_key, vehicle_name
        ORDER BY vehicle_name COLLATE NOCASE
        """,
        (day_key,),
    ).fetchall()

    year_rows = conn.execute(
        """
        SELECT year, COUNT(DISTINCT dedup_key) AS count
        FROM ads
        WHERE
            day_key = ?
            AND status = 'sale'
            AND year IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
        """,
        (day_key,),
    ).fetchall()

    color_rows = conn.execute(
        """
        SELECT color, COUNT(DISTINCT dedup_key) AS count
        FROM ads
        WHERE
            day_key = ?
            AND status = 'sale'
            AND color IS NOT NULL
        GROUP BY color
        ORDER BY color COLLATE NOCASE
        """,
        (day_key,),
    ).fetchall()

    range_row = conn.execute(
        """
        SELECT
            MIN(price_million) AS min_price,
            MAX(price_million) AS max_price,
            MIN(mileage_km) AS min_mileage,
            MAX(mileage_km) AS max_mileage
        FROM ads
        WHERE
            day_key = ?
            AND status = 'sale'
        """,
        (day_key,),
    ).fetchone()

    count_row = conn.execute(
        """
        SELECT
            COUNT(DISTINCT CASE WHEN status = 'sale' AND price_million IS NOT NULL THEN dedup_key END) AS priced,
            COUNT(DISTINCT CASE WHEN status = 'sale' AND price_million IS NULL THEN dedup_key END) AS unpriced,
            COUNT(DISTINCT CASE WHEN status = 'sale' AND mileage_km IS NOT NULL THEN dedup_key END) AS used,
            COUNT(DISTINCT CASE WHEN status = 'buyer' THEN dedup_key END) AS buyers
        FROM ads
        WHERE day_key = ?
        """,
        (day_key,),
    ).fetchone()

    vehicles_by_key: dict[str, dict] = {}
    for row in vehicle_rows:
        vehicles_by_key[row["vehicle_key"]] = {
            "key": row["vehicle_key"],
            "name": row["vehicle_name"],
            "count": int(row["count"] or 0),
        }

    for key, name in known_vehicle_options():
        vehicles_by_key.setdefault(
            key,
            {
                "key": key,
                "name": name,
                "count": 0,
            },
        )

    return {
        "vehicles": sorted(
            vehicles_by_key.values(),
            key=lambda item: item["name"],
        ),
        "years": [
            {
                "year": int(row["year"]),
                "count": int(row["count"] or 0),
            }
            for row in year_rows
        ],
        "colors": [
            {
                "color": row["color"],
                "count": int(row["count"] or 0),
            }
            for row in color_rows
        ],
        "ranges": {
            "min_price": int(range_row["min_price"] or 0),
            "max_price": int(range_row["max_price"] or 0),
            "min_mileage": int(range_row["min_mileage"] or 0),
            "max_mileage": int(range_row["max_mileage"] or 0),
        },
        "counts": {
            "priced": int(count_row["priced"] or 0),
            "unpriced": int(count_row["unpriced"] or 0),
            "used": int(count_row["used"] or 0),
            "buyers": int(count_row["buyers"] or 0),
        },
    }



def today_day_key() -> str:
    return _compute_day_key(datetime.now(timezone.utc))


def yesterday_day_key() -> str:
    return _compute_day_key(datetime.now(timezone.utc) - timedelta(days=1))


def cheapest_per_vehicle_report(conn: sqlite3.Connection, day_key: str | None = None) -> list[sqlite3.Row]:
    """کمترین قیمت هر مدل خودرو (شناخته‌شده) برای یک روز — پایه‌ی گزارش اکسل.

    فقط روی خودروهایی کار می‌کند که vehicle_key تشخیص داده شده (لیست الگوهای
    شناخته‌شده در parser.py)، تا گزارش شامل «هر مدل مشخص» باشد، نه هر متن آزاد.
    """
    day_key = day_key or today_day_key()
    return conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY vehicle_key
                    ORDER BY price_million ASC, id DESC
                ) AS rn
            FROM ads
            WHERE
                status = 'sale'
                AND vehicle_key IS NOT NULL
                AND price_million IS NOT NULL
                AND day_key = ?
        )
        SELECT * FROM ranked WHERE rn = 1 ORDER BY vehicle_name
        """,
        (day_key,),
    ).fetchall()


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


def _build_ads_where(
    base_filters: list[str],
    day_key: str | None,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_mileage: int | None = None,
    max_mileage: int | None = None,
) -> tuple[str, list[object]]:
    """شرط WHERE مشترک بین توابع list_*_for_web و count_*_for_web را می‌سازد
    تا شمارش تعداد کل (برای صفحه‌بندی) دقیقاً همان فیلترهای جدول را ببیند.
    """
    day_key = day_key or today_day_key()
    filters = [*base_filters, "day_key = ?"]
    params: list[object] = [day_key]

    if query:
        like_where, like_params = _search_filters(query)
        filters.append(like_where)
        params.extend(like_params)

    if vehicle_keys:
        placeholders = ", ".join("?" for _ in vehicle_keys)
        filters.append(f"vehicle_key IN ({placeholders})")
        params.extend(vehicle_keys)

    if years:
        placeholders = ", ".join("?" for _ in years)
        filters.append(f"year IN ({placeholders})")
        params.extend(years)

    if colors:
        placeholders = ", ".join("?" for _ in colors)
        filters.append(f"color IN ({placeholders})")
        params.extend(colors)

    if min_price is not None:
        filters.append("price_million >= ?")
        params.append(min_price)

    if max_price is not None:
        filters.append("price_million <= ?")
        params.append(max_price)

    if min_mileage is not None:
        filters.append("mileage_km >= ?")
        params.append(min_mileage)

    if max_mileage is not None:
        filters.append("mileage_km <= ?")
        params.append(max_mileage)

    return " AND ".join(filters), params


def _count_ads_for_web(conn: sqlite3.Connection, base_filters: list[str], day_key: str | None, **kwargs) -> int:
    where, params = _build_ads_where(base_filters, day_key, **kwargs)
    row = conn.execute(
        f"SELECT COUNT(DISTINCT dedup_key) AS c FROM ads WHERE {where}",
        params,
    ).fetchone()
    return int(row["c"] or 0)


def count_priced_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_mileage: int | None = None,
    max_mileage: int | None = None,
    day_key: str | None = None,
) -> int:
    return _count_ads_for_web(
        conn,
        ["status = 'sale'", "price_million IS NOT NULL"],
        day_key,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
    )


def count_unpriced_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    day_key: str | None = None,
) -> int:
    return _count_ads_for_web(
        conn,
        ["status = 'sale'", "price_million IS NULL"],
        day_key,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
    )


def count_used_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_mileage: int | None = None,
    max_mileage: int | None = None,
    day_key: str | None = None,
) -> int:
    return _count_ads_for_web(
        conn,
        ["status = 'sale'", "mileage_km IS NOT NULL"],
        day_key,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
    )


def count_buyer_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    day_key: str | None = None,
) -> int:
    return _count_ads_for_web(
        conn,
        ["status = 'buyer'"],
        day_key,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
    )


def list_priced_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_mileage: int | None = None,
    max_mileage: int | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """آگهی‌های قیمت‌دار امروز برای جدول اصلی وب با فیلترهای پیشرفته.

    پشتیبانی از:
    - جست‌وجوی متنی
    - چند vehicle_key
    - چند year
    - چند color
    - بازه قیمت
    - بازه کارکرد
    - مرتب‌سازی
    """
    day_key = day_key or today_day_key()

    filters = [
        "status = 'sale'",
        "price_million IS NOT NULL",
        "day_key = ?",
    ]
    params: list[object] = [day_key]

    if query:
        like_where, like_params = _search_filters(query)
        filters.append(like_where)
        params.extend(like_params)

    if vehicle_keys:
        placeholders = ", ".join("?" for _ in vehicle_keys)
        filters.append(f"vehicle_key IN ({placeholders})")
        params.extend(vehicle_keys)

    if years:
        placeholders = ", ".join("?" for _ in years)
        filters.append(f"year IN ({placeholders})")
        params.extend(years)

    if colors:
        placeholders = ", ".join("?" for _ in colors)
        filters.append(f"color IN ({placeholders})")
        params.extend(colors)

    if min_price is not None:
        filters.append("price_million >= ?")
        params.append(min_price)

    if max_price is not None:
        filters.append("price_million <= ?")
        params.append(max_price)

    if min_mileage is not None:
        filters.append("mileage_km >= ?")
        params.append(min_mileage)

    if max_mileage is not None:
        filters.append("mileage_km <= ?")
        params.append(max_mileage)

    sort_sql_by_name = {
        "newest": "message_date IS NULL, message_date DESC, id DESC",
        "oldest": "message_date IS NULL, message_date ASC, id ASC",
        "price_asc": "price_million ASC, id DESC",
        "price_desc": "price_million DESC, id DESC",
        "year_desc": "year IS NULL, year DESC, id DESC",
        "year_asc": "year IS NULL, year ASC, id DESC",
        "mileage_asc": "mileage_km IS NULL, mileage_km ASC, id DESC",
        "mileage_desc": "mileage_km IS NULL, mileage_km DESC, id DESC",
    }
    order_by = sort_sql_by_name.get(sort, sort_sql_by_name["newest"])

    where = " AND ".join(filters)
    params.extend([limit, offset])

    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY {order_by}
                ) AS rn
            FROM ads
            WHERE {where}
        )
        SELECT * FROM matched
        WHERE rn = 1
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()

def list_unpriced_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """آگهی‌های فروش بدون قیمت امروز برای وب با فیلترهای پیشرفته."""

    day_key = day_key or today_day_key()

    filters = [
        "status = 'sale'",
        "price_million IS NULL",
        "day_key = ?",
    ]

    params: list[object] = [day_key]

    if query:
        like_where, like_params = _search_filters(query)
        filters.append(like_where)
        params.extend(like_params)

    if vehicle_keys:
        placeholders = ", ".join("?" for _ in vehicle_keys)
        filters.append(f"vehicle_key IN ({placeholders})")
        params.extend(vehicle_keys)

    if years:
        placeholders = ", ".join("?" for _ in years)
        filters.append(f"year IN ({placeholders})")
        params.extend(years)

    if colors:
        placeholders = ", ".join("?" for _ in colors)
        filters.append(f"color IN ({placeholders})")
        params.extend(colors)

    sort_sql = {
        "newest": "message_date IS NULL, message_date DESC, id DESC",
        "oldest": "message_date IS NULL, message_date ASC, id ASC",
        "year_desc": "year IS NULL, year DESC, id DESC",
        "year_asc": "year IS NULL, year ASC, id DESC",
    }

    order_by = sort_sql.get(
        sort,
        sort_sql["newest"]
    )

    where = " AND ".join(filters)

    params.extend([limit, offset])

    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY {order_by}
                ) AS rn
            FROM ads
            WHERE {where}
        )
        SELECT *
        FROM matched
        WHERE rn = 1
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()

def list_used_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_mileage: int | None = None,
    max_mileage: int | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """آگهی‌های کارکرده امروز برای وب با فیلترهای کامل."""

    day_key = day_key or today_day_key()

    filters = [
        "status = 'sale'",
        "mileage_km IS NOT NULL",
        "day_key = ?",
    ]

    params: list[object] = [day_key]

    if query:
        like_where, like_params = _search_filters(query)
        filters.append(like_where)
        params.extend(like_params)

    if vehicle_keys:
        placeholders = ", ".join("?" for _ in vehicle_keys)
        filters.append(f"vehicle_key IN ({placeholders})")
        params.extend(vehicle_keys)

    if years:
        placeholders = ", ".join("?" for _ in years)
        filters.append(f"year IN ({placeholders})")
        params.extend(years)

    if colors:
        placeholders = ", ".join("?" for _ in colors)
        filters.append(f"color IN ({placeholders})")
        params.extend(colors)

    if min_price is not None:
        filters.append("price_million >= ?")
        params.append(min_price)

    if max_price is not None:
        filters.append("price_million <= ?")
        params.append(max_price)

    if min_mileage is not None:
        filters.append("mileage_km >= ?")
        params.append(min_mileage)

    if max_mileage is not None:
        filters.append("mileage_km <= ?")
        params.append(max_mileage)

    sort_sql = {
        "newest": "message_date IS NULL, message_date DESC, id DESC",
        "oldest": "message_date IS NULL, message_date ASC, id ASC",
        "price_asc": "price_million ASC, id DESC",
        "price_desc": "price_million DESC, id DESC",
        "mileage_asc": "mileage_km ASC, id DESC",
        "mileage_desc": "mileage_km DESC, id DESC",
        "year_desc": "year IS NULL, year DESC, id DESC",
        "year_asc": "year IS NULL, year ASC, id DESC",
    }

    order_by = sort_sql.get(
        sort,
        sort_sql["newest"]
    )

    where = " AND ".join(filters)

    params.extend([limit, offset])

    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY {order_by}
                ) AS rn
            FROM ads
            WHERE {where}
        )
        SELECT *
        FROM matched
        WHERE rn = 1
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()

def list_buyer_ads_for_web(
    conn: sqlite3.Connection,
    query: str | None = None,
    vehicle_keys: list[str] | None = None,
    years: list[int] | None = None,
    colors: list[str] | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    day_key: str | None = None,
) -> list[sqlite3.Row]:
    """پیام‌های خریدار امروز برای وب با فیلترهای پیشرفته."""

    day_key = day_key or today_day_key()

    filters = [
        "status = 'buyer'",
        "day_key = ?",
    ]

    params: list[object] = [day_key]

    if query:
        like_where, like_params = _search_filters(query)
        filters.append(like_where)
        params.extend(like_params)

    if vehicle_keys:
        placeholders = ", ".join("?" for _ in vehicle_keys)
        filters.append(f"vehicle_key IN ({placeholders})")
        params.extend(vehicle_keys)

    if years:
        placeholders = ", ".join("?" for _ in years)
        filters.append(f"year IN ({placeholders})")
        params.extend(years)

    if colors:
        placeholders = ", ".join("?" for _ in colors)
        filters.append(f"color IN ({placeholders})")
        params.extend(colors)

    sort_sql = {
        "newest": "message_date IS NULL, message_date DESC, id DESC",
        "oldest": "message_date IS NULL, message_date ASC, id ASC",
        "year_desc": "year IS NULL, year DESC, id DESC",
        "year_asc": "year IS NULL, year ASC, id DESC",
    }

    order_by = sort_sql.get(
        sort,
        sort_sql["newest"]
    )

    where = " AND ".join(filters)

    params.extend([limit, offset])

    return conn.execute(
        f"""
        WITH matched AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY dedup_key
                    ORDER BY {order_by}
                ) AS rn
            FROM ads
            WHERE {where}
        )
        SELECT *
        FROM matched
        WHERE rn = 1
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        params,
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

def get_dashboard_summary(
    conn: sqlite3.Connection,
) -> dict:
    """
    خلاصه کامل داشبورد سایت.
    """

    today = today_day_key()

    ads_row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_ads,

            SUM(
                CASE
                    WHEN status = 'sale'
                    AND price_million IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS priced,

            SUM(
                CASE
                    WHEN status = 'sale'
                    AND price_million IS NULL
                    THEN 1 ELSE 0
                END
            ) AS unpriced,

            SUM(
                CASE
                    WHEN status = 'sale'
                    AND mileage_km IS NOT NULL
                    THEN 1 ELSE 0
                END
            ) AS used,

            SUM(
                CASE
                    WHEN status = 'buyer'
                    THEN 1 ELSE 0
                END
            ) AS buyers

        FROM ads

        WHERE day_key = ?
        """,
        (today,),
    ).fetchone()


    channel_row = conn.execute(
        """
        SELECT
            COUNT(*) AS active_channels
        FROM channels
        WHERE active = 1
        """
    ).fetchone()


    message_row = conn.execute(
        """
        SELECT
            COUNT(*) AS messages_today
        FROM ads
        WHERE day_key = ?
        """,
        (today,),
    ).fetchone()


    alert_row = conn.execute(
        """
        SELECT
            COUNT(*) AS alerts
        FROM alert_events
        """
    ).fetchone()


    cheapest_rows = conn.execute(
        """
        WITH ranked AS (

            SELECT
                *,

                ROW_NUMBER() OVER (
                    PARTITION BY vehicle_key
                    ORDER BY price_million ASC, id DESC
                ) AS rn

            FROM ads

            WHERE
                day_key = ?

                AND status = 'sale'

                AND price_million IS NOT NULL

                AND vehicle_key IS NOT NULL
        )


        SELECT
            id,
            vehicle_key,
            vehicle_name,
            price_million,
            year,
            month,
            color,
            mileage_km,
            phone,
            channel_username,
            source_message_id

        FROM ranked

        WHERE rn = 1

        ORDER BY price_million ASC

        LIMIT 10
        """,
        (today,),
    ).fetchall()


    return {
        "today": {
            "total_ads": int(ads_row["total_ads"] or 0),
            "priced": int(ads_row["priced"] or 0),
            "unpriced": int(ads_row["unpriced"] or 0),
            "used": int(ads_row["used"] or 0),
            "buyers": int(ads_row["buyers"] or 0),
        },

        "channels": {
            "active": int(channel_row["active_channels"] or 0),
            "messages_today": int(message_row["messages_today"] or 0),
        },

        "alerts": {
            "count": int(alert_row["alerts"] or 0),
        },

        "cheapest": [
            {
                "id": row["id"],
                "vehicle_key": row["vehicle_key"],
                "vehicle_name": row["vehicle_name"],
                "price_million": row["price_million"],
                "year": row["year"],
                "month": row["month"],
                "color": row["color"],
                "mileage_km": row["mileage_km"],
                "phone": row["phone"],
                "channel_username": row["channel_username"],
                "source_message_id": row["source_message_id"],
            }
            for row in cheapest_rows
        ],
    }

def count_live_cheapest_vehicles(conn: sqlite3.Connection) -> int:
    """تعداد کل مدل‌های شناخته‌شده‌ای که امروز حداقل یک آگهی قیمت‌دار دارند."""
    today = today_day_key()
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT vehicle_key) AS c
        FROM ads
        WHERE
            day_key = ?
            AND status = 'sale'
            AND price_million IS NOT NULL
            AND vehicle_key IS NOT NULL
        """,
        (today,),
    ).fetchone()
    return int(row["c"] or 0)


def get_live_cheapest_vehicles(
    conn: sqlite3.Connection,
    limit: int = 50,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """
    کمترین قیمت لحظه‌ای هر مدل خودرو برای صفحه کارت‌های سایت.

    قوانین:
    - فقط آگهی‌های امروز
    - فقط فروش
    - فقط دارای قیمت
    - فقط مدل‌های شناخته‌شده
    - یک مورد برای هر خودرو
    """

    today = today_day_key()

    return conn.execute(
        """
        WITH ranked AS (

            SELECT
                *,

                ROW_NUMBER() OVER (
                    PARTITION BY vehicle_key
                    ORDER BY
                        price_million ASC,
                        id DESC
                ) AS rn,

                COUNT(*) OVER (
                    PARTITION BY vehicle_key
                ) AS ad_count

            FROM ads

            WHERE
                day_key = ?

                AND status = 'sale'

                AND price_million IS NOT NULL

                AND vehicle_key IS NOT NULL
        )


        SELECT
            id,
            vehicle_key,
            vehicle_name,
            price_million,
            year,
            month,
            color,
            mileage_km,
            phone,
            channel_username,
            source_message_id,
            message_date,
            ad_count

        FROM ranked

        WHERE rn = 1

        ORDER BY
            price_million ASC

        LIMIT ? OFFSET ?
        """,
        (
            today,
            limit,
            offset,
        ),
    ).fetchall()
