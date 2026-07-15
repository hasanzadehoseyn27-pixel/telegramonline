from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.deps import get_db
from telegramonline.storage import stats, list_channels

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Connection = Depends(get_db)) -> dict[str, int]:
    return stats(db)

@router.get("/dashboard")
def dashboard_stats(
    db: Connection = Depends(get_db),
):
    result = stats(db)

    channels = list_channels(
        db,
        today_only=True
    )

    result["active_channels"] = len(
        [
            c for c in channels
            if c["active"]
        ]
    )

    return result