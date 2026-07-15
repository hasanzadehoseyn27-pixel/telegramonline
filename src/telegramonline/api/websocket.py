from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """
    مدیریت اتصال‌های WebSocket کاربران سایت.

    وظایف:
    - نگهداری کاربران متصل
    - اضافه کردن اتصال جدید
    - حذف اتصال قطع شده
    - ارسال پیام به یک کاربر
    - Broadcast برای همه کاربران
    """

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []


    async def connect(
        self,
        websocket: WebSocket,
    ) -> None:
        """
        قبول اتصال جدید WebSocket.
        """

        await websocket.accept()

        self.active_connections.append(
            websocket
        )


    def disconnect(
        self,
        websocket: WebSocket,
    ) -> None:
        """
        حذف اتصال قطع شده.
        """

        if websocket in self.active_connections:
            self.active_connections.remove(
                websocket
            )


    async def send_personal_message(
        self,
        message: dict[str, Any],
        websocket: WebSocket,
    ) -> None:
        """
        ارسال پیام به یک اتصال خاص.
        """

        await websocket.send_text(
            json.dumps(
                message,
                ensure_ascii=False,
            )
        )


    async def broadcast(
        self,
        message: dict[str, Any],
    ) -> None:
        """
        ارسال پیام به تمام کاربران متصل.

        مثال:

        {
            "type": "new_ad",
            "data": {
                "vehicle": "دنا",
                "price": 1800
            }
        }

        """

        disconnected: list[WebSocket] = []

        for connection in self.active_connections:

            try:

                await connection.send_text(
                    json.dumps(
                        message,
                        ensure_ascii=False,
                    )
                )

            except Exception:
                disconnected.append(
                    connection
                )


        for connection in disconnected:

            self.disconnect(
                connection
            )


    def connection_count(self) -> int:
        """
        تعداد کاربران آنلاین.
        """

        return len(
            self.active_connections
        )


# نمونه سراسری برای استفاده در کل پروژه
manager = ConnectionManager()