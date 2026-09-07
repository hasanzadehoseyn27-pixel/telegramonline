import asyncio
import sys

sys.path.insert(0, "src")

from telethon import TelegramClient
from telegramonline.config import Settings


async def main() -> None:
    settings = Settings.from_env()
    # این یه Session کاملاً جدا و جدیده — اسمش با اکانت اول (telegramonline_user) فرق داره
    client = TelegramClient("telegramonline_user_2", settings.api_id, settings.api_hash)
    await client.start()
    me = await client.get_me()
    print(f"✅ با موفقیت وصل شد به: {me.phone} (@{me.username})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
