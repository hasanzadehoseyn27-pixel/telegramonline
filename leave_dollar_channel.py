import asyncio
import io
import sys

sys.path.insert(0, "src")

from telethon import TelegramClient
from telegramonline.config import Settings


async def main() -> None:
    settings = Settings.from_env()
    client = TelegramClient("telegramonline_user", settings.api_id, settings.api_hash)
    await client.start()

    found = []
    async for dialog in client.iter_dialogs():
        name = dialog.name or ""
        if "دلار" in name or "لحظه" in name or "قیمت" in name:
            found.append(dialog)

    with io.open("dollar_leave_result.txt", "w", encoding="utf-8") as f:
        if not found:
            f.write("هیچ کانالی با این اسم پیدا نشد.\n")
        for d in found:
            f.write(f"پیدا شد: {d.name} (id={d.id})\n")
            try:
                await client.delete_dialog(d.entity)
                f.write(f"  -> با موفقیت ترک شد.\n")
            except Exception as exc:
                f.write(f"  -> خطا در ترک کردن: {exc}\n")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
