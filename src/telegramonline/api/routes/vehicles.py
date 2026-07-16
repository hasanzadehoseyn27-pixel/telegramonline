from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query

from telegramonline.api.deps import get_db
from telegramonline.api.routes.ads import row_to_ad
from telegramonline.api.schemas import AdOut, CheapestLivePage, CheapestLiveVehicleOut
from telegramonline.storage import (
    count_live_cheapest_vehicles,
    get_live_cheapest_vehicles,
    list_ads_for_vehicle_key,
    today_day_key,
    yesterday_day_key,
)


router = APIRouter(
    prefix="/vehicles",
    tags=["vehicles"],
)


def row_to_vehicle_card(
    row,
) -> CheapestLiveVehicleOut:

    telegram_link = None

    if row["channel_username"]:

        telegram_link = (
            f"https://t.me/"
            f"{row['channel_username']}/"
            f"{row['source_message_id']}"
        )


    return CheapestLiveVehicleOut(
        id=row["id"],

        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],

        price_million=row["price_million"],

        year=row["year"],
        month=row["month"],

        color=row["color"],
        mileage_km=row["mileage_km"],

        phone=row["phone"],

        channel_username=row["channel_username"],
        source_message_id=row["source_message_id"],

        message_date=row["message_date"],

        telegram_link=telegram_link,
        ad_count=row["ad_count"],
    )



@router.get(
    "/cheapest/live",
    response_model=CheapestLivePage,
)
def cheapest_live(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    db: Connection = Depends(get_db),
):
    day_key = yesterday_day_key() if day == "yesterday" else today_day_key()

    rows = get_live_cheapest_vehicles(
        db,
        limit=limit,
        offset=offset,
        day_key=day_key,
    )

    total = count_live_cheapest_vehicles(db, day_key=day_key)

    return CheapestLivePage(
        items=[row_to_vehicle_card(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/for-model", response_model=list[AdOut])
def ads_for_model(
    vehicle_key: str = Query(...),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    db: Connection = Depends(get_db),
):
    day_key = yesterday_day_key() if day == "yesterday" else today_day_key()
    rows = list_ads_for_vehicle_key(db, vehicle_key, day_key=day_key)
    return [row_to_ad(row) for row in rows]