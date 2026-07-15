from __future__ import annotations

from typing import Any

from telegramonline.api.websocket import manager


async def broadcast_event(
    event_type: str,
    data: dict[str, Any],
) -> None:
    """
    ارسال event عمومی به تمام کاربران WebSocket.

    مثال:

    {
        "type": "new_ad",
        "data": {
            "vehicle": "دنا",
            "price": 1850
        }
    }
    """

    await manager.broadcast(
        {
            "type": event_type,
            "data": data,
        }
    )


async def broadcast_new_ad(
    ad: dict[str, Any],
) -> None:
    """
    ارسال آگهی جدید.
    """

    await broadcast_event(
        "new_ad",
        ad,
    )


async def broadcast_price_alert(
    alert: dict[str, Any],
) -> None:
    """
    ارسال هشدار قیمت.
    """

    await broadcast_event(
        "price_alert",
        alert,
    )

async def broadcast_price_update(
    data: dict,
) -> None:
    """
    ارسال تغییر قیمت خودرو به کلاینت‌های متصل.
    """

    await broadcast_event(
        "price_update",
        data,
    )