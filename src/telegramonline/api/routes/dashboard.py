from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import DashboardOut
from telegramonline.storage import get_dashboard_summary


router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
)


@router.get(
    "",
    response_model=DashboardOut,
)
def dashboard(
    db: Connection = Depends(get_db),
):

    return get_dashboard_summary(db)