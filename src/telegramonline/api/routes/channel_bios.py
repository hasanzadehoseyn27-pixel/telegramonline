"""شماره‌های بیوی کانال‌ها برای سایت لیست شماره‌ها (showroom-extractor).

    GET /api/channel-bios?platform=telegram|rubika   → [{username, phones, about, updatedAt}]
"""
from __future__ import annotations

from fastapi import APIRouter

from telegramonline.api.routes.blocked_channels import _is_rubika, _open
from telegramonline.bios import ensure_bio_schema, list_bios

router = APIRouter(prefix="/channel-bios", tags=["channel-bios"])


@router.get("")
def get_bios(platform: str | None = None) -> list[dict]:
    conn = _open(_is_rubika(platform))
    try:
        ensure_bio_schema(conn)
        return list_bios(conn)
    finally:
        conn.close()
