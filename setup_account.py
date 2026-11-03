"""ساختن session یک اکانت تلگرام تازه برای جمع‌کننده (اکانت ۳، ۴، ...).

    venv\\Scripts\\python setup_account.py 3

شماره‌ی تلفن (با +98)، کد تأیید تلگرام و اگر دارد رمز دومرحله‌ای را می‌پرسد و
فایل telegramonline_user_<شماره>.session را می‌سازد. بعد از آن با
pm2 restart telegramonline-collector، جمع‌کننده این اکانت را خودش وصل می‌کند و
کانال‌های تازه اول روی همین اکانت عضو می‌شوند.
"""
import asyncio
import sys

sys.path.insert(0, "src")

from telethon import TelegramClient

from telegramonline.config import Settings


async def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit() or int(sys.argv[1]) < 2:
        print("استفاده: venv\\Scripts\\python setup_account.py 3")
        sys.exit(1)
    n = int(sys.argv[1])
    settings = Settings.from_env()
    client = TelegramClient(f"telegramonline_user_{n}", settings.api_id, settings.api_hash)
    await client.start()
    me = await client.get_me()
    dialogs = 0
    async for d in client.iter_dialogs():
        if getattr(d.entity, "broadcast", False) or getattr(d.entity, "megagroup", False):
            dialogs += 1
    print(f"✅ اکانت {n} وصل شد: {me.phone} (@{me.username}) — الان عضو {dialogs} کانال/گروه است.")
    await client.disconnect()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    asyncio.run(main())
