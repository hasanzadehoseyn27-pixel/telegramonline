"""«بلاک کانال‌ها» برای پنل ادمین سایت — تلگرام و روبیکا.

    GET    /api/blocked-channels?platform=telegram|rubika        فهرست بلاک‌شده‌ها
    POST   /api/blocked-channels?platform=...   {username}       بلاک
    DELETE /api/blocked-channels/{username}?platform=...         آزاد کردن
    POST   /api/blocked-channels/suggest                         شروع بررسی مشکوک‌های روبیکا
    GET    /api/blocked-channels/suggest                         وضعیت/نتیجه‌ی بررسی

بلاک یعنی همان کاری که tools/remove_channel.py (تلگرام) و
telegramonline.rubika.block (روبیکا) می‌کنند: کانال در blocked_channels ثبت
می‌شود (دیگر خودکار اضافه نمی‌شود)، آگهی‌هایش از دیتابیس پاک می‌شود و کانال
غیرفعال می‌شود تا جمع‌کننده در دور بعد از آن خارج شود. آگهی‌های خودِ سایت
(Redis) را بک‌اند سایت پاک می‌کند.
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from telegramonline.api.deps import get_settings
from telegramonline.storage import (
    _clean_username,
    block_channel,
    connect,
    connect_for_request,
    unblock_channel,
)

router = APIRouter(prefix="/blocked-channels", tags=["blocked-channels"])

SUSPECTS_FILE = Path("data/rubika_suspects.txt")
_ready: set[str] = set()
_suggest_proc: subprocess.Popen | None = None
_suggest_started: str | None = None


class BlockRequest(BaseModel):
    username: str
    title: str | None = None


def _is_rubika(platform: str | None) -> bool:
    return (platform or "").strip().lower() == "rubika"


def _db_path(rubika: bool) -> str:
    if rubika:
        return os.getenv("RUBIKA_DATABASE_PATH", "data/rubikaonline.sqlite3")
    return str(get_settings().database_path)


def _open(rubika: bool) -> sqlite3.Connection:
    path = _db_path(rubika)
    if path not in _ready:
        conn = connect(path)  # اسکیما را اولین بار می‌سازد
        try:
            conn.execute("ALTER TABLE blocked_channels ADD COLUMN title TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ستون از قبل هست
        conn.close()
        _ready.add(path)
    return connect_for_request(path)


def get_db(platform: str | None = Query(None)) -> Generator[sqlite3.Connection, None, None]:
    conn = _open(_is_rubika(platform))
    try:
        yield conn
    finally:
        conn.close()


def _norm(raw: str, rubika: bool) -> str:
    value = (raw or "").strip()
    if rubika:
        m = re.search(r"rubika\.ir/([A-Za-z0-9_]+)", value, re.IGNORECASE)
        if m and m.group(1).lower() not in ("joing", "joinc"):
            value = m.group(1)
        return value.lstrip("@").strip().strip("/")
    return _clean_username(value).lstrip("@")


def _find_channel(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM channels WHERE lower(username) = lower(?)", (username,)
    ).fetchone()


@router.get("")
def list_blocked(platform: str | None = None, db: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        "SELECT username, reason, blocked_at, title FROM blocked_channels ORDER BY blocked_at DESC"
    ).fetchall()
    return [
        {
            "username": r["username"],
            "title": r["title"] or "",
            "reason": r["reason"] or "",
            "blockedAt": r["blocked_at"],
        }
        for r in rows
    ]


@router.post("")
def block(payload: BlockRequest, platform: str | None = None, db: sqlite3.Connection = Depends(get_db)) -> dict:
    rubika = _is_rubika(platform)
    username = _norm(payload.username, rubika)
    if not username or "/" in username or " " in username:
        return {"ok": False, "message": "یوزرنیم یا لینک کانال معتبر نیست."}
    channel = _find_channel(db, username)
    # در سایت، آگهی‌ها با یوزرنیمِ ثبت‌شده‌ی کانال ذخیره شده‌اند (با همان بزرگ/کوچکی)
    site_username = channel["username"] if channel is not None else username
    title = (payload.title or "").strip() or (channel["title"] if channel is not None and channel["title"] else "")
    block_channel(db, username, "پنل ادمین")
    db.execute("UPDATE blocked_channels SET title = ? WHERE username = ?", (title or None, username.lower()))
    deleted = 0
    if channel is not None:
        before = db.total_changes
        db.execute("DELETE FROM ads WHERE channel_id = ?", (channel["id"],))
        deleted = db.total_changes - before
        if channel["joined"]:
            # جمع‌کننده در دور بعد با همان اکانت از کانال خارج می‌شود و ردیف را پاک می‌کند
            db.execute("UPDATE channels SET active = 0 WHERE id = ?", (channel["id"],))
        else:
            db.execute("DELETE FROM channels WHERE id = ?", (channel["id"],))
    db.commit()
    where = "روبیکا" if rubika else "تلگرام"
    msg = f"کانال {title or username} در {where} بلاک شد"
    msg += f" و {deleted} آگهی‌اش پاک شد." if channel is not None else " (در لیست پایش نبود)."
    return {
        "ok": True,
        "message": msg,
        "username": username,
        "siteUsername": site_username,
        "title": title,
        "deletedAds": deleted,
        "wasWatched": channel is not None,
    }


@router.delete("/{username}")
def unblock(username: str, platform: str | None = None, db: sqlite3.Connection = Depends(get_db)) -> dict:
    clean = _norm(username, _is_rubika(platform))
    exists = db.execute("SELECT 1 FROM blocked_channels WHERE username = ?", (clean.lower(),)).fetchone()
    if not exists:
        return {"ok": False, "message": "این کانال در لیست بلاک نیست."}
    unblock_channel(db, clean)
    return {"ok": True, "message": f"{clean} از بلاک خارج شد. برای پایش دوباره، دوباره اضافه‌اش کن.", "username": clean}


# ------------------------------------------------------- پیشنهاد مشکوک‌های روبیکا


def _running() -> bool:
    return _suggest_proc is not None and _suggest_proc.poll() is None


def _read_suspects(conn: sqlite3.Connection) -> list[dict]:
    if not SUSPECTS_FILE.exists():
        return []
    blocked = {r["username"] for r in conn.execute("SELECT username FROM blocked_channels")}
    out = []
    for line in SUSPECTS_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, comment = line.partition("#")
        name = name.strip().split()[0] if name.strip() else ""
        if not name or name.lower() in blocked:
            continue
        title, _, count = comment.strip().rpartition("—")
        m = re.search(r"\d+", count)
        out.append({
            "username": name,
            "title": title.strip() or name,
            "carAds": int(m.group()) if m else 0,
        })
    return out


@router.post("/suggest")
def start_suggest() -> dict:
    global _suggest_proc, _suggest_started
    if _running():
        return {"ok": True, "running": True, "message": "بررسی از قبل در حال اجراست."}
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    log = open(Path("data/rubika_suggest.log"), "w", encoding="utf-8")
    _suggest_proc = subprocess.Popen(
        [sys.executable, "-m", "telegramonline.rubika.block", "--suggest"],
        cwd=os.getcwd(), env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    _suggest_started = datetime.now().isoformat(timespec="seconds")
    return {"ok": True, "running": True, "message": "بررسی کانال‌های روبیکا شروع شد؛ چند دقیقه طول می‌کشد."}


@router.get("/suggest")
def suggest_status() -> dict:
    conn = _open(True)
    try:
        suspects = _read_suspects(conn)
    finally:
        conn.close()
    progress = ""
    log = Path("data/rubika_suggest.log")
    if _running() and log.exists():
        try:
            lines = [l for l in log.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
            progress = lines[-1].strip() if lines else ""
        except OSError:
            pass
    updated = (
        datetime.fromtimestamp(SUSPECTS_FILE.stat().st_mtime).isoformat(timespec="seconds")
        if SUSPECTS_FILE.exists() else None
    )
    return {
        "running": _running(),
        "startedAt": _suggest_started,
        "progress": progress,
        "updatedAt": updated,
        "suspects": suspects,
    }
