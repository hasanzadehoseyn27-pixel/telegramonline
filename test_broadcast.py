import asyncio

from telegramonline.api.events import broadcast_new_ad


async def main():
    await broadcast_new_ad(
        {
            "vehicle_name": "دنا",
            "price_million": 1850,
            "color": "سفید",
        }
    )


asyncio.run(main())