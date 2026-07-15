from __future__ import annotations


_last_prices: dict[str, int] = {}


def check_price_change(
    vehicle_key: str,
    new_price: int,
) -> dict | None:
    """
    بررسی تغییر قیمت.

    فقط زمانی event می‌دهد که قیمت کاهش پیدا کند.
    """

    old_price = _last_prices.get(
        vehicle_key
    )


    _last_prices[vehicle_key] = new_price


    if old_price is None:
        return None


    if new_price >= old_price:
        return None


    return {
        "vehicle_key": vehicle_key,
        "old_price": old_price,
        "new_price": new_price,
    }