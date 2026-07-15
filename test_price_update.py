import asyncio

from telegramonline.api.price_tracker import check_price_change
from telegramonline.api.events import broadcast_price_update


async def main():

    # قیمت اولیه
    print(
        check_price_change(
            "dena",
            1900
        )
    )


    # کاهش قیمت
    event = check_price_change(
        "dena",
        1850
    )


    print(event)


    if event:
        await broadcast_price_update(
            event
        )


asyncio.run(main())