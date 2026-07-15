from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import (
    ChannelCreate,
    ChannelDeleteOut,
    ChannelOut,
    ChannelAddRequest,
    ChannelActionResponse,
)

from telegramonline.storage import (
    add_channel,
    deactivate_channel,
    get_channel,
    list_channels,
)


router = APIRouter(
    prefix="/channels",
    tags=["channels"],
)


@router.get(
    "",
    response_model=list[ChannelOut],
)
def get_channels(
    db: Connection = Depends(get_db),
) -> list[ChannelOut]:

    channels = list_channels(
        db,
        today_only=True,
    )

    return [
        ChannelOut(**channel)
        for channel in channels
    ]



@router.post(
    "",
    response_model=ChannelActionResponse,
)
def create_channel(
    payload: ChannelAddRequest,
    db: Connection = Depends(get_db),
):

    channel_id = add_channel(
        db,
        payload.username,
    )


    if channel_id is None:

        return ChannelActionResponse(
            ok=False,
            message="این کانال قبلاً ثبت شده یا یوزرنیم معتبر نیست.",
        )


    return ChannelActionResponse(
        ok=True,
        message="کانال اضافه شد و در صف فعال‌سازی قرار گرفت.",
        channel_id=channel_id,
    )



@router.delete(
    "/{channel_id}",
    response_model=ChannelActionResponse,
)
def delete_channel(
    channel_id: int,
    db: Connection = Depends(get_db),
):

    channel = get_channel(
        db,
        channel_id,
    )


    if channel is None:

        return ChannelActionResponse(
            ok=False,
            message="کانال پیدا نشد.",
            channel_id=channel_id,
        )


    ok = deactivate_channel(
        db,
        channel_id,
    )


    return ChannelActionResponse(
        ok=ok,
        message=(
            "کانال برای حذف علامت‌گذاری شد."
            if ok
            else
            "غیرفعال کردن کانال ناموفق بود."
        ),
        channel_id=channel_id,
    )