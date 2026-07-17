from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from telegramonline.api.deps import get_db
from telegramonline.storage import list_channel_activity, today_day_key, yesterday_day_key

router = APIRouter(prefix="/channels", tags=["channels"])


class ChannelActivityOut(BaseModel):
    username: str
    title: str | None
    type: str
    active: bool
    car_ads: int


@router.get("/activity", response_model=list[ChannelActivityOut])
def get_channel_activity(
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    vehicle_keys: list[str] | None = Query(default=None),
    db: Connection = Depends(get_db),
):
    day_key = yesterday_day_key() if day == "yesterday" else today_day_key()
    rows = list_channel_activity(db, day_key=day_key, vehicle_keys=vehicle_keys)
    return [ChannelActivityOut(**row) for row in rows]
