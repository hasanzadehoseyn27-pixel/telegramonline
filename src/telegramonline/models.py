from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ParsedAd:
    source_message_id: str
    raw_text: str
    normalized_text: str
    dedup_key: str
    source: str
    message_date: datetime | None
    vehicle_key: str | None
    vehicle_name: str | None
    trim: str | None
    price_million: int | None
    year: int | None
    month: int | None
    color: str | None
    mileage_km: int | None
    phone: str | None
    status: str
    delivery: str | None
    confidence: float

@dataclass(slots=True)
class PriceAlert:
    id: int | None
    user_id: int
    vehicle_key: str
    vehicle_name: str | None
    condition: str
    min_price: int | None
    max_price: int | None
    active: bool