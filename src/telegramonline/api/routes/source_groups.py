from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import (
    SourceGroupActionResponse,
    SourceGroupAddRequest,
    SourceGroupOut,
)
from telegramonline.storage import (
    add_source_group,
    deactivate_source_group,
    get_source_group,
    list_source_groups,
)


router = APIRouter(
    prefix="/source-groups",
    tags=["source-groups"],
)


@router.get("", response_model=list[SourceGroupOut])
def get_source_groups(
    db: Connection = Depends(get_db),
) -> list[SourceGroupOut]:
    return [SourceGroupOut(**row) for row in list_source_groups(db)]


@router.post("", response_model=SourceGroupActionResponse)
def create_source_group(
    payload: SourceGroupAddRequest,
    db: Connection = Depends(get_db),
) -> SourceGroupActionResponse:
    group_id = add_source_group(db, payload.username)
    if group_id is None:
        return SourceGroupActionResponse(
            ok=False,
            message="لینک گروه معتبر نیست یا قبلا ثبت شده است.",
        )
    return SourceGroupActionResponse(
        ok=True,
        message="گروه ثبت شد و collector در چرخه بعدی آن را فعال می‌کند.",
        group_id=group_id,
    )


@router.delete("/{group_id}", response_model=SourceGroupActionResponse)
def delete_source_group(
    group_id: int,
    db: Connection = Depends(get_db),
) -> SourceGroupActionResponse:
    group = get_source_group(db, group_id)
    if group is None:
        return SourceGroupActionResponse(
            ok=False,
            message="گروه پیدا نشد.",
            group_id=group_id,
        )
    ok = deactivate_source_group(db, group_id)
    return SourceGroupActionResponse(
        ok=ok,
        message="گروه برای حذف از پایش علامت‌گذاری شد." if ok else "حذف گروه ناموفق بود.",
        group_id=group_id,
    )
