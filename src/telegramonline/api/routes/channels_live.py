from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import ChannelLiveResponse
from telegramonline.storage import get_live_channel_stats


router = APIRouter(
    prefix="/channels",
    tags=["channels"],
)


@router.get(
    "/live",
    response_model=ChannelLiveResponse,
)
def live_channels(
    db: Connection = Depends(get_db),
):

    data = get_live_channel_stats(
        db
    )

    return ChannelLiveResponse(
        channels=data["channels"],
        summary=data["summary"],
    )