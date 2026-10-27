"""بیوی (توضیحات) کانال‌ها و شماره‌های داخلش — برای سایت لیست شماره‌ها
(showroom-extractor). شماره‌هایی که از بیو برداشته می‌شوند آنجا سبز نشان
داده می‌شوند.

جدول channel_bios در همان دیتابیس هر پیام‌رسان (تلگرام / روبیکا):
    username, about, phones (با کاما), updated_at

گرفتن بیو آرام انجام می‌شود (هر چند ثانیه یک کانال) تا اکانت‌ها محدودیت
نگیرند؛ هر بیو چند روز یک بار تازه می‌شود.
"""
from __future__ import annotations

import re
import sqlite3

BIO_SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_bios (
    username TEXT PRIMARY KEY,
    about TEXT,
    phones TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# هر بیو چند روز یک بار دوباره خوانده می‌شود
BIO_REFRESH_DAYS = 3

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# رقم‌ها با جداکننده‌های رایج بین‌شان: فاصله، خط تیره، نقطه، پرانتز، زیرخط
# (مثلاً 0912 34 34 345 / 0912-34-34-345 / 0912.490.8200 / (021) 3344-5566)
_RUN = re.compile(r"\+?\d(?:[ \t\-.()_‌]{0,3}\d){8,40}")


def to_latin_digits(text: str) -> str:
    return str(text or "").translate(_DIGITS)


def _fake(phone: str) -> bool:
    # 09120000000 / 09121111111 و مانند آن
    return bool(re.fullmatch(r"09\d{2}(\d)\1{6}", phone)) or bool(re.search(r"(\d)\1{7}", phone))


def extract_phones(text: str) -> list[str]:
    """همه‌ی شماره‌های ایرانی (موبایل و ثابت با کد شهر) به شکل ۱۱ رقمی، بدون تکرار."""
    out: list[str] = []
    for m in _RUN.finditer(to_latin_digits(text)):
        digits = re.sub(r"\D", "", m.group())
        i = 0
        while i < len(digits):
            rest = digits[i:]
            phone = None
            step = 1
            if rest.startswith("0098") and rest[4:5] == "9" and len(rest) >= 14:
                phone, step = "0" + rest[4:14], 14
            elif rest.startswith("98") and rest[2:3] == "9" and len(rest) >= 12 and (i == 0 or len(digits) == 12):
                phone, step = "0" + rest[2:12], 12
            elif rest.startswith("09") and len(rest) >= 11:
                phone, step = rest[:11], 11
            elif rest.startswith("9") and len(digits) == 10 and i == 0:
                phone, step = "0" + rest, 10
            elif re.match(r"0[1-8]\d{9}", rest) and len(digits) == 11:
                phone, step = rest[:11], 11
            if phone and not _fake(phone):
                if phone not in out:
                    out.append(phone)
                i += step
            else:
                i += 1
    return out


def ensure_bio_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(BIO_SCHEMA)


def save_bio(conn: sqlite3.Connection, username: str, about: str | None) -> list[str]:
    phones = extract_phones(about or "")
    conn.execute(
        "INSERT INTO channel_bios (username, about, phones, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(username) DO UPDATE SET about = excluded.about, phones = excluded.phones, updated_at = CURRENT_TIMESTAMP",
        (username, about or "", ",".join(phones)),
    )
    conn.commit()
    return phones


def next_channel_for_bio(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """کانالِ فعال و عضوشده‌ای که بیو ندارد یا بیوش قدیمی است (بی‌بیوها اول)."""
    return conn.execute(
        """
        SELECT c.* FROM channels c
        LEFT JOIN channel_bios b ON lower(b.username) = lower(c.username)
        WHERE c.active = 1 AND c.joined = 1
          AND (b.username IS NULL OR b.updated_at < datetime('now', ?))
        ORDER BY b.updated_at IS NOT NULL, b.updated_at, c.id
        LIMIT 1
        """,
        (f"-{BIO_REFRESH_DAYS} days",),
    ).fetchone()


def list_bios(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT username, about, phones, updated_at FROM channel_bios WHERE phones IS NOT NULL AND phones != ''"
    ).fetchall()
    return [
        {"username": r["username"], "phones": [p for p in (r["phones"] or "").split(",") if p], "about": r["about"] or "", "updatedAt": r["updated_at"]}
        for r in rows
    ]
