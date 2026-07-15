from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import (
    AlertToggleOut,
    PriceAlertCreate,
    PriceAlertOut,
)
from telegramonline.storage import (
    create_price_alert,
    delete_price_alert,
    get_price_alert,
    list_price_alerts,
    toggle_price_alert,
    list_alert_events,
    count_alert_events,
)

from telegramonline.api.schemas import (
    AlertEventCountOut,
    AlertEventOut,
)

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
)


def row_to_alert(row) -> PriceAlertOut:
    return PriceAlertOut(
        id=row["id"],
        user_id=row["user_id"],
        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],
        condition=row["condition"],
        min_price=row["min_price"],
        max_price=row["max_price"],
        active=bool(row["active"]),
        created_at=row["created_at"],
    )

def row_to_event(row) -> AlertEventOut:

    telegram_link = None

    if row["channel_username"] and row["source_message_id"]:
        telegram_link = (
            f"https://t.me/"
            f"{row['channel_username']}/"
            f"{row['source_message_id']}"
        )

    return AlertEventOut(
        id=row["id"],
        alert_id=row["alert_id"],
        ad_id=row["ad_id"],
        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],
        condition=row["condition"],
        price_million=row["price_million"],
        channel_username=row["channel_username"],
        source_message_id=row["source_message_id"],
        raw_text=row["raw_text"],
        created_at=row["created_at"],
        telegram_link=telegram_link,
    )


@router.get("", response_model=list[PriceAlertOut])
def get_alerts(
    user_id: int,
    db: Connection = Depends(get_db),
):
    rows = list_price_alerts(db, user_id)

    return [
        row_to_alert(row)
        for row in rows
    ]


@router.post("", response_model=PriceAlertOut)
def add_alert(
    payload: PriceAlertCreate,
    db: Connection = Depends(get_db),
):
    alert_id = create_price_alert(
        db,
        payload.user_id,
        payload.vehicle_key,
        payload.vehicle_name,
        payload.condition,
        payload.min_price,
        payload.max_price,
    )

    row = get_price_alert(
        db,
        alert_id,
    )

    return row_to_alert(row)


@router.delete("/{alert_id}")
def remove_alert(
    alert_id: int,
    db: Connection = Depends(get_db),
):
    ok = delete_price_alert(
        db,
        alert_id,
    )

    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    return {
        "ok": True
    }


@router.patch("/{alert_id}/toggle", response_model=AlertToggleOut)
def toggle_alert(
    alert_id: int,
    db: Connection = Depends(get_db),
):
    alert = get_price_alert(
        db,
        alert_id,
    )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    toggle_price_alert(
        db,
        alert_id,
    )

    updated = get_price_alert(
        db,
        alert_id,
    )

    return AlertToggleOut(
        ok=True,
        active=bool(updated["active"]),
    )

@router.get("/events", response_model=list[AlertEventOut])
def get_alert_events(
    limit: int = 50,
    offset: int = 0,
    db: Connection = Depends(get_db),
):

    rows = list_alert_events(
        db,
        limit=limit,
        offset=offset,
    )

    return [
        row_to_event(row)
        for row in rows
    ]


@router.get(
    "/events/count",
    response_model=AlertEventCountOut,
)
def get_alert_events_count(
    db: Connection = Depends(get_db),
):

    return AlertEventCountOut(
        count=count_alert_events(db)
    )