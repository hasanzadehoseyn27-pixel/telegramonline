from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import CheapestLiveVehicleOut
from telegramonline.storage import get_live_cheapest_vehicles


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
    )



@router.get(
    "/cheapest/live",
    response_model=list[CheapestLiveVehicleOut],
)
def cheapest_live(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    db: Connection = Depends(get_db),
):

    rows = get_live_cheapest_vehicles(
        db,
        limit=limit,
    )


    return [
        row_to_vehicle_card(row)
        for row in rows
    ]