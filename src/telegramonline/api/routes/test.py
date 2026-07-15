from __future__ import annotations

from fastapi import APIRouter

from telegramonline.api.events import broadcast_price_update


router = APIRouter(
    prefix="/test",
    tags=["test"],
)


@router.post("/price-update")
async def test_price_update():

    await broadcast_price_update(
        {
            "vehicle_key": "dena",
            "old_price": 1900,
            "new_price": 1850,
        }
    )

    return {
        "status": "price update sent"
    }