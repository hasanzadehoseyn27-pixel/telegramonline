import asyncio

from telegramonline.api.events import broadcast_price_update


async def main():

    await broadcast_price_update(
        {
            "vehicle_key": "dena",
            "old_price": 1900,
            "new_price": 1850,
        }
    )


asyncio.run(main())