from __future__ import annotations

from pydantic import BaseModel


class AdOut(BaseModel):
    id: int
    channel_username: str | None
    source_message_id: str
    raw_text: str
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
    message_date: str | None
    day_key: str | None
    telegram_link: str | None


class AdsPage(BaseModel):
    items: list[AdOut]
    limit: int
    offset: int
    count: int

class ChannelOut(BaseModel):
    id: int
    username: str
    title: str | None
    active: bool
    joined: bool
    added_at: str
    message_count: int


class ChannelCreate(BaseModel):
    username: str


class ChannelDeleteOut(BaseModel):
    ok: bool
    message: str

class DashboardStats(BaseModel):
    total: int
    sale: int
    with_price: int
    without_price: int
    spam: int
    buyer: int
    live_collected: int
    saved_vehicles: int
    active_channels: int

class CheapestVehicleOut(BaseModel):
    id: int
    vehicle_key: str
    vehicle_name: str
    price_million: int
    year: int | None
    month: int | None
    color: str | None
    phone: str | None
    message_date: str | None
    channel_username: str | None
    telegram_link: str | None


class CheapestReportOut(BaseModel):
    day: str
    count: int
    items: list[CheapestVehicleOut]

class VehicleFilterOption(BaseModel):
    key: str
    name: str
    count: int


class YearFilterOption(BaseModel):
    year: int
    count: int


class ColorFilterOption(BaseModel):
    color: str
    count: int


class FilterRanges(BaseModel):
    min_price: int
    max_price: int
    min_mileage: int
    max_mileage: int


class FilterCounts(BaseModel):
    priced: int
    unpriced: int
    used: int
    buyers: int


class FilterOptionsOut(BaseModel):
    vehicles: list[VehicleFilterOption]
    years: list[YearFilterOption]
    colors: list[ColorFilterOption]
    ranges: FilterRanges
    counts: FilterCounts

class PriceAlertCreate(BaseModel):
    user_id: int
    vehicle_key: str
    vehicle_name: str | None = None
    condition: str
    min_price: int | None = None
    max_price: int | None = None


class PriceAlertOut(BaseModel):
    id: int
    user_id: int
    vehicle_key: str
    vehicle_name: str | None
    condition: str
    min_price: int | None
    max_price: int | None
    active: bool
    created_at: str


class AlertToggleOut(BaseModel):
    ok: bool
    active: bool


class AlertEventOut(BaseModel):
    id: int
    alert_id: int
    ad_id: int
    vehicle_key: str | None
    vehicle_name: str | None
    condition: str | None
    price_million: int | None
    channel_username: str | None
    source_message_id: str | None
    raw_text: str | None
    created_at: str
    telegram_link: str | None


class AlertEventCountOut(BaseModel):
    count: int

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str

class AdDetailOut(BaseModel):
    id: int
    channel_username: str | None
    source_message_id: str

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

    raw_text: str

    message_date: str | None

    telegram_link: str | None

class DashboardOut(BaseModel):
    today: dict
    channels: dict
    alerts: dict
    cheapest: list[dict]

class CheapestLiveVehicleOut(BaseModel):
    id: int

    vehicle_key: str | None
    vehicle_name: str | None

    price_million: int

    year: int | None
    month: int | None

    color: str | None
    mileage_km: int | None

    phone: str | None

    channel_username: str | None
    source_message_id: str | None

    message_date: str | None

    telegram_link: str | None

class ChannelLiveOut(BaseModel):
    id: int
    username: str
    title: str | None

    active: bool
    joined: bool

    today_messages: int

    added_at: str | None


class ChannelLiveSummary(BaseModel):
    active_channels: int
    messages_today: int


class ChannelLiveResponse(BaseModel):
    channels: list[ChannelLiveOut]
    summary: ChannelLiveSummary

class ChannelAddRequest(BaseModel):
    username: str


class ChannelActionResponse(BaseModel):
    ok: bool
    message: str
    channel_id: int | None = None


class SourceGroupOut(BaseModel):
    id: int
    username: str
    title: str | None
    active: bool
    joined: bool
    discovered_channels: int
    added_at: str


class SourceGroupAddRequest(BaseModel):
    username: str


class SourceGroupActionResponse(BaseModel):
    ok: bool
    message: str
    group_id: int | None = None

class CheapestReportItemOut(BaseModel):
    id: int

    vehicle_key: str | None
    vehicle_name: str | None

    price_million: int

    year: int | None
    month: int | None

    color: str | None

    mileage_km: int | None

    phone: str | None

    channel_username: str | None

    source_message_id: str | None

    message_date: str | None



class CheapestReportDayOut(BaseModel):
    day: str
    count: int
    items: list[CheapestReportItemOut]
    
