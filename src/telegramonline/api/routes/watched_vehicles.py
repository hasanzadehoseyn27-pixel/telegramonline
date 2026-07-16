from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from telegramonline.api.deps import get_db
from telegramonline.api.routes.ads import row_to_ad
from telegramonline.api.schemas import AdsPage
from telegramonline.storage import (
    add_watched_vehicle,
    count_special_ads,
    list_special_ads,
    list_watched_vehicles,
    remove_watched_vehicle,
)

router = APIRouter(prefix="/watched-vehicles", tags=["watched-vehicles"])


class WatchedVehicleOut(BaseModel):
    id: int
    vehicle_key: str
    vehicle_name: str | None
    added_at: str


class WatchedVehicleCreate(BaseModel):
    vehicle_key: str
    vehicle_name: str | None = None


def row_to_watched(row) -> WatchedVehicleOut:
    return WatchedVehicleOut(
        id=row["id"],
        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],
        added_at=row["added_at"],
    )


@router.get("", response_model=list[WatchedVehicleOut])
def get_watched_vehicles(db: Connection = Depends(get_db)):
    return [row_to_watched(row) for row in list_watched_vehicles(db)]


@router.post("", response_model=WatchedVehicleOut)
def add_watched(payload: WatchedVehicleCreate, db: Connection = Depends(get_db)):
    watched_id = add_watched_vehicle(db, payload.vehicle_key, payload.vehicle_name)
    if watched_id is None:
        raise HTTPException(status_code=400, detail="Could not add watched vehicle")
    row = next((r for r in list_watched_vehicles(db) if r["id"] == watched_id), None)
    return row_to_watched(row)


@router.delete("/{watched_id}")
def remove_watched(watched_id: int, db: Connection = Depends(get_db)):
    ok = remove_watched_vehicle(db, watched_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Watched vehicle not found")
    return {"ok": True}


@router.get("/ads", response_model=AdsPage)
def get_special_ads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db),
):
    rows = list_special_ads(db, limit=limit, offset=offset)
    total = count_special_ads(db)
    items = [row_to_ad(row) for row in rows]
    return AdsPage(items=items, limit=limit, offset=offset, count=len(items), total=total)
