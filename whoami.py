import asyncio
import sys

sys.path.insert(0, "src")

from telethon import TelegramClient

from telegramonline.config import Settings
from telegramonline.net import parse_proxy_from_env


async def main():
    settings = Settings.from_env()
    proxy = parse_proxy_from_env()
    client = TelegramClient(
        "telegramonline_user", settings.api_id, settings.api_hash, proxy=proxy
    )
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ این session لاگین نیست.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"شماره‌تلفن: {me.phone}")
    print(f"یوزرنیم: @{me.username}" if me.username else "یوزرنیم: (نداره)")
    print(f"اسم: {me.first_name or ''} {me.last_name or ''}".strip())
    print(f"آیدی عددی: {me.id}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
