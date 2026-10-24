"""«پیمایش گروه‌ها» برای روبیکا — همان API تلگرام (/api/source-groups) ولی روی
دیتابیس جدای روبیکا (RUBIKA_DATABASE_PATH). جمع‌کننده‌ی روبیکا
(telegramonline.rubika.collector) در چرخه‌ی بعدی گروه را عضو و پایش می‌کند.
"""
from __future__ import annotations

import os
from collections.abc import Generator
from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.schemas import (
    SourceGroupActionResponse,
    SourceGroupAddRequest,
    SourceGroupOut,
)
from telegramonline.storage import (
    add_source_group,
    connect,
    connect_for_request,
    deactivate_source_group,
    get_source_group,
    list_source_groups,
    remove_source_group,
)

router = APIRouter(prefix="/rubika/source-groups", tags=["rubika-source-groups"])

_schema_ready = False


def _db_path() -> str:
    return os.getenv("RUBIKA_DATABASE_PATH", "data/rubikaonline.sqlite3")


def get_rubika_db() -> Generator[Connection, None, None]:
    global _schema_ready
    if not _schema_ready:
        connect(_db_path()).close()  # اسکیما را اولین بار می‌سازد
        _schema_ready = True
    conn = connect_for_request(_db_path())
    try:
        yield conn
    finally:
        conn.close()


@router.get("", response_model=list[SourceGroupOut])
def get_groups(db: Connection = Depends(get_rubika_db)) -> list[SourceGroupOut]:
    return [SourceGroupOut(**row) for row in list_source_groups(db)]


@router.post("", response_model=SourceGroupActionResponse)
def create_group(payload: SourceGroupAddRequest, db: Connection = Depends(get_rubika_db)) -> SourceGroupActionResponse:
    link = payload.username.strip()
    if "rubika.ir/" not in link.lower() and not link.lstrip("@"):
        return SourceGroupActionResponse(ok=False, message="لینک گروه روبیکا معتبر نیست.")
    group_id = add_source_group(db, link)
    if group_id is None:
        return SourceGroupActionResponse(ok=False, message="لینک گروه معتبر نیست یا قبلا ثبت شده است.")
    return SourceGroupActionResponse(
        ok=True,
        message="گروه روبیکا ثبت شد و جمع‌کننده‌ی روبیکا در چرخه‌ی بعدی آن را فعال می‌کند.",
        group_id=group_id,
    )


@router.delete("/{group_id}", response_model=SourceGroupActionResponse)
def delete_group(group_id: int, db: Connection = Depends(get_rubika_db)) -> SourceGroupActionResponse:
    group = get_source_group(db, group_id)
    if group is None:
        return SourceGroupActionResponse(ok=False, message="گروه پیدا نشد.", group_id=group_id)
    ok = remove_source_group(db, group_id) if not group["joined"] else deactivate_source_group(db, group_id)
    return SourceGroupActionResponse(
        ok=ok, message="گروه از پایش خارج شد." if ok else "حذف گروه ناموفق بود.", group_id=group_id
    )
