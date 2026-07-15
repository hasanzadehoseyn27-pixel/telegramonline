from __future__ import annotations

from sqlite3 import Connection

from fastapi import APIRouter, Depends

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import FilterOptionsOut
from telegramonline.storage import get_filter_options_for_web

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("/options", response_model=FilterOptionsOut)
def get_filter_options(
    db: Connection = Depends(get_db),
) -> FilterOptionsOut:
    return FilterOptionsOut(**get_filter_options_for_web(db))