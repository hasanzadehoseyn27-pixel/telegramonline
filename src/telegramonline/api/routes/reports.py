from __future__ import annotations

import os
import tempfile
from sqlite3 import Connection

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from openpyxl import Workbook

from telegramonline.api.deps import get_db
from telegramonline.api.schemas import (
    CheapestReportOut,
    CheapestVehicleOut,
)

from telegramonline.storage import (
    cheapest_per_vehicle_report,
    today_day_key,
    yesterday_day_key,
)


router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)


def resolve_day_key(day: str) -> str:
    if day == "yesterday":
        return yesterday_day_key()

    return today_day_key()



def row_to_cheapest_item(
    row,
) -> CheapestVehicleOut:

    telegram_link = None

    if (
        row["channel_username"]
        and row["source_message_id"]
    ):
        telegram_link = (
            f"https://t.me/"
            f"{row['channel_username']}/"
            f"{row['source_message_id']}"
        )


    return CheapestVehicleOut(
        id=row["id"],

        vehicle_key=row["vehicle_key"],
        vehicle_name=row["vehicle_name"],

        price_million=row["price_million"],

        year=row["year"],
        month=row["month"],

        color=row["color"],

        phone=row["phone"],

        message_date=row["message_date"],

        channel_username=row["channel_username"],

        telegram_link=telegram_link,
    )



@router.get(
    "/cheapest",
    response_model=CheapestReportOut,
)
def get_cheapest_report(
    day: str = Query(
        default="today",
        pattern="^(today|yesterday)$",
    ),
    db: Connection = Depends(get_db),
) -> CheapestReportOut:


    day_key = resolve_day_key(day)


    rows = cheapest_per_vehicle_report(
        db,
        day_key=day_key,
    )


    items = [
        row_to_cheapest_item(row)
        for row in rows
    ]


    return CheapestReportOut(
        day=day,
        count=len(items),
        items=items,
    )



@router.get(
    "/cheapest/today",
    response_model=CheapestReportOut,
)
def cheapest_today(
    db: Connection = Depends(get_db),
):

    rows = cheapest_per_vehicle_report(
        db,
        day_key=today_day_key(),
    )


    items = [
        row_to_cheapest_item(row)
        for row in rows
    ]


    return CheapestReportOut(
        day="today",
        count=len(items),
        items=items,
    )



@router.get(
    "/cheapest/yesterday",
    response_model=CheapestReportOut,
)
def cheapest_yesterday(
    db: Connection = Depends(get_db),
):

    rows = cheapest_per_vehicle_report(
        db,
        day_key=yesterday_day_key(),
    )


    items = [
        row_to_cheapest_item(row)
        for row in rows
    ]


    return CheapestReportOut(
        day="yesterday",
        count=len(items),
        items=items,
    )



def build_cheapest_excel(
    rows,
    day: str,
) -> str:

    wb = Workbook()

    ws = wb.active

    ws.title = "Cheapest"

    ws.sheet_view.rightToLeft = True


    headers = [
        "ماشین",
        "کمترین قیمت (میلیون)",
        "مدل",
        "برج",
        "رنگ",
        "تماس",
        "زمان ارسال",
        "کانال",
        "لینک تلگرام",
        "متن خام",
    ]


    ws.append(headers)


    for row in rows:

        telegram_link = ""


        if (
            row["channel_username"]
            and row["source_message_id"]
        ):
            telegram_link = (
                f"https://t.me/"
                f"{row['channel_username']}/"
                f"{row['source_message_id']}"
            )


        ws.append(
            [
                row["vehicle_name"] or "",
                row["price_million"] or "",
                row["year"] or "",
                row["month"] or "",
                row["color"] or "",
                row["phone"] or "",
                row["message_date"] or "",
                row["channel_username"] or "",
                telegram_link,
                row["raw_text"] or "",
            ]
        )


    for column_cells in ws.columns:

        max_length = max(
            (
                len(str(cell.value))
                for cell in column_cells
                if cell.value is not None
            ),
            default=10,
        )


        column_letter = column_cells[0].column_letter


        ws.column_dimensions[
            column_letter
        ].width = min(
            max(max_length + 2, 12),
            60,
        )


    fd, path = tempfile.mkstemp(
        suffix=".xlsx",
        prefix=f"cheapest_{day}_",
    )


    os.close(fd)


    wb.save(path)


    return path



@router.get(
    "/cheapest.xlsx",
)
def download_cheapest_report_excel(
    day: str = Query(
        default="today",
        pattern="^(today|yesterday)$",
    ),
    db: Connection = Depends(get_db),
) -> FileResponse:


    day_key = resolve_day_key(day)


    rows = cheapest_per_vehicle_report(
        db,
        day_key=day_key,
    )


    path = build_cheapest_excel(
        rows,
        day,
    )


    filename = f"cheapest_{day}.xlsx"


    return FileResponse(
        path,

        filename=filename,

        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),

        background=BackgroundTask(
            os.remove,
            path,
        ),
    )