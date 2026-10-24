"""ورود اکانت روبیکای جمع‌کننده و ساخت سشن (یک بار).

    $env:PYTHONPATH="src"
    venv\\Scripts\\python -m telegramonline.rubika.login

شماره از RUBIKA_PHONE در .env خوانده می‌شود (یا می‌پرسد)؛ کد پیامک و در
صورت نیاز رمز دو مرحله‌ای را می‌پرسد. سشن در RUBIKA_SESSION (+ .rp) ذخیره می‌شود.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from ..config import load_dotenv


async def _login() -> None:
    from rubpy import Client

    load_dotenv()
    session = Path(os.getenv("RUBIKA_SESSION", "data/rubika"))
    session.parent.mkdir(parents=True, exist_ok=True)
    phone = os.getenv("RUBIKA_PHONE", "").strip() or input("شماره‌ی روبیکا (مثلاً 0912...): ").strip()
    print(f"ورود اکانت روبیکا با {phone}. کد پیامک‌شده را وارد کن.")
    client = Client(name=str(session))
    await client.start(phone_number=phone)
    me = await client.get_me()
    await client.disconnect()
    user = me.user if me is not None else None
    print(f"✅ سشن ذخیره شد: {session}.rp")
    if user is not None:
        print(f"اکانت فعال: {user.first_name or ''} ({user.user_guid})")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    # rubpy در سطح INFO اطلاعات کامل سشن را چاپ می‌کند
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("rubpy").setLevel(logging.WARNING)
    asyncio.run(_login())


if __name__ == "__main__":
    main()
