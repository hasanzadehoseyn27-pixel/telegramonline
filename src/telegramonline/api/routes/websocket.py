from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from telegramonline.api.websocket import manager


router = APIRouter(
    tags=["websocket"]
)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    اتصال WebSocket سایت.

    فعلاً برای تست:
    هر پیام دریافتی را به همان کاربر برمی‌گرداند.
    بعداً collector از همین manager برای broadcast استفاده می‌کند.
    """

    await manager.connect(
        websocket
    )

    try:

        while True:

            data = await websocket.receive_text()

            await manager.send_personal_message(
                {
                    "type": "pong",
                    "message": data,
                },
                websocket,
            )

    except WebSocketDisconnect:

        manager.disconnect(
            websocket
        )