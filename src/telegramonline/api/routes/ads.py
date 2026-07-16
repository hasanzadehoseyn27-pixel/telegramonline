from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query, HTTPException
from telegramonline.api.schemas import (
    AdOut,
    AdsPage,
    AdDetailOut,
)
from telegramonline.api.deps import get_db
from telegramonline.api.schemas import AdOut, AdsPage

from telegramonline.storage import (
    count_buyer_ads_for_web,
    count_priced_ads_for_web,
    count_unpriced_ads_for_web,
    count_used_ads_for_web,
    list_buyer_ads_for_web,
    list_priced_ads_for_web,
    list_unpriced_ads_for_web,
    list_used_ads_for_web,
    today_day_key,
    yesterday_day_key,
)

from telegramonline.storage import get_ad_by_id

router = APIRouter(prefix="/ads", tags=["ads"])


def _resolve_day_key(day: str) -> str:
    return yesterday_day_key() if day == "yesterday" else today_day_key()


def row_to_ad(row) -> AdOut:
    telegram_link = None
    if row["source"] == "live" and row["channel_username"]:
        telegram_link = f"https://t.me/{row['channel_username']}/{row['source_message_id']}"

    return AdOut(
        id=row["id"],
        channel_username=row["channel_username"],
        source_message_id=row["source_message_id"],
        raw_text=row["raw_text"],
        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],
        trim=row["trim"],
        price_million=row["price_million"],
        year=row["year"],
        month=row["month"],
        color=row["color"],
        mileage_km=row["mileage_km"],
        phone=row["phone"],
        status=row["status"],
        delivery=row["delivery"],
        confidence=row["confidence"],
        message_date=row["message_date"],
        day_key=row["day_key"],
        telegram_link=telegram_link,
    )


@router.get("/priced", response_model=AdsPage)
def get_priced_ads(
    query: str | None = Query(default=None),
    vehicle_keys: list[str] | None = Query(default=None),
    years: list[int] | None = Query(default=None),
    colors: list[str] | None = Query(default=None),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    min_mileage: int | None = Query(default=None, ge=0),
    max_mileage: int | None = Query(default=None, ge=0),
    sort: str = Query(
        default="newest",
        pattern="^(newest|oldest|price_asc|price_desc|year_desc|year_asc|mileage_asc|mileage_desc)$",
    ),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db),
) -> AdsPage:
    day_key = _resolve_day_key(day)
    rows = list_priced_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
        sort=sort,
        limit=limit,
        offset=offset,
        day_key=day_key,
    )

    items = [row_to_ad(row) for row in rows]

    total = count_priced_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
        day_key=day_key,
    )

    return AdsPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
        total=total,
    )

@router.get("/unpriced", response_model=AdsPage)
def get_unpriced_ads(
    query: str | None = Query(default=None),
    vehicle_keys: list[str] | None = Query(default=None),
    years: list[int] | None = Query(default=None),
    colors: list[str] | None = Query(default=None),
    sort: str = Query(
        default="newest",
        pattern="^(newest|oldest|year_desc|year_asc)$",
    ),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db),
) -> AdsPage:
    day_key = _resolve_day_key(day)

    rows = list_unpriced_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        sort=sort,
        limit=limit,
        offset=offset,
        day_key=day_key,
    )

    items = [row_to_ad(row) for row in rows]

    total = count_unpriced_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        day_key=day_key,
    )

    return AdsPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
        total=total,
    )

@router.get("/used", response_model=AdsPage)
def get_used_ads(
    query: str | None = Query(default=None),
    vehicle_keys: list[str] | None = Query(default=None),
    years: list[int] | None = Query(default=None),
    colors: list[str] | None = Query(default=None),
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    min_mileage: int | None = Query(default=None, ge=0),
    max_mileage: int | None = Query(default=None, ge=0),
    sort: str = Query(
        default="newest",
        pattern="^(newest|oldest|price_asc|price_desc|mileage_asc|mileage_desc|year_desc|year_asc)$",
    ),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db),
) -> AdsPage:
    day_key = _resolve_day_key(day)

    rows = list_used_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
        sort=sort,
        limit=limit,
        offset=offset,
        day_key=day_key,
    )

    items = [row_to_ad(row) for row in rows]

    total = count_used_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        min_price=min_price,
        max_price=max_price,
        min_mileage=min_mileage,
        max_mileage=max_mileage,
        day_key=day_key,
    )

    return AdsPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
        total=total,
    )


@router.get("/buyers", response_model=AdsPage)
def get_buyer_ads(
    query: str | None = Query(default=None),
    vehicle_keys: list[str] | None = Query(default=None),
    years: list[int] | None = Query(default=None),
    colors: list[str] | None = Query(default=None),
    sort: str = Query(
        default="newest",
        pattern="^(newest|oldest|year_desc|year_asc)$",
    ),
    day: str = Query(default="today", pattern="^(today|yesterday)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db),
) -> AdsPage:
    day_key = _resolve_day_key(day)

    rows = list_buyer_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        sort=sort,
        limit=limit,
        offset=offset,
        day_key=day_key,
    )

    items = [row_to_ad(row) for row in rows]

    total = count_buyer_ads_for_web(
        db,
        query=query,
        vehicle_keys=vehicle_keys,
        years=years,
        colors=colors,
        day_key=day_key,
    )

    return AdsPage(
        items=items,
        limit=limit,
        offset=offset,
        count=len(items),
        total=total,
    )

@router.get("/{ad_id}", response_model=AdDetailOut)
def get_ad_detail(
    ad_id: int,
    db: Connection = Depends(get_db),
):

    row = get_ad_by_id(
        db,
        ad_id,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="آگهی پیدا نشد",
        )

    telegram_link = None

    if row["channel_username"]:
        telegram_link = (
            f"https://t.me/"
            f"{row['channel_username']}/"
            f"{row['source_message_id']}"
        )

    return AdDetailOut(
        id=row["id"],
        channel_username=row["channel_username"],
        source_message_id=row["source_message_id"],

        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],
        trim=row["trim"],

        price_million=row["price_million"],

        year=row["year"],
        month=row["month"],

        color=row["color"],
        mileage_km=row["mileage_km"],

        phone=row["phone"],

        status=row["status"],

        raw_text=row["raw_text"],

        message_date=row["message_date"],

        telegram_link=telegram_link,
    )