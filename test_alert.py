from datetime import datetime, timezone

from telegramonline.storage import (
    connect,
    save_ads,
    check_price_alerts,
)

from telegramonline.config import Settings
from telegramonline.models import ParsedAd


conn = connect(Settings.from_env().database_path)


ad = ParsedAd(
    source_message_id="test_1002",
    raw_text="دنا سفید مدل 1404 قیمت 1850",
    normalized_text="دنا سفید مدل 1404 قیمت 1850",
    dedup_key="test_dena_1850_1002",
    source="live",
    message_date=datetime.now(timezone.utc),
    vehicle_key="dena",
    vehicle_name="دنا",
    trim=None,
    price_million=1850,
    year=1404,
    month=None,
    color="سفید",
    mileage_km=None,
    phone=None,
    status="sale",
    delivery=None,
    confidence=1.0,
)


saved = save_ads(
    conn,
    [ad],
)

print("saved:", [dict(x) for x in saved])


events = check_price_alerts(
    conn,
    saved,
)

print("triggered:", events)