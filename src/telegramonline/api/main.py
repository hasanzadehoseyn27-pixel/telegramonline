from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from telegramonline.api.deps import get_settings
from telegramonline.api.routes import (
    ads,
    alerts,
    auth,
    channels,
    channels_live,
    dashboard,
    filters,
    reports,
    stats,
    source_groups,
    test,
    vehicles,
    websocket,
)
from telegramonline.storage import ensure_schema

app = FastAPI(
    title="TelegramOnline API",
    version="0.1.0",
)


@app.on_event("startup")
def _ensure_db_schema() -> None:
    ensure_schema(get_settings().database_path)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# دامنه‌های واقعی سایت (پروداکشن) باید توی متغیر محیطی CORS_ALLOWED_ORIGINS
# با کاما جدا بشن، مثلا:
#   CORS_ALLOWED_ORIGINS=https://telegramonline.ir,https://www.telegramonline.ir
# اگر ست نشه، فقط لوکال‌هاست (برای توسعه) مجاز می‌مونه و در نتیجه سایت واقعی
# با خطای CORS مواجه می‌شه — پس روی سرور حتما این متغیر رو ست کن.
_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_extra_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# اگر می‌خوای موقتا (فقط برای عیب‌یابی) همه‌ی دامنه‌ها مجاز باشن، این رو ست کن:
#   CORS_ALLOW_ALL=1
_allow_all = os.getenv("CORS_ALLOW_ALL", "").strip() == "1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else [*_DEFAULT_DEV_ORIGINS, *_extra_origins],
    allow_credentials=not _allow_all,  # allow_credentials با allow_origins=["*"] با هم سازگار نیستن
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(stats.router, prefix="/api")
app.include_router(ads.router, prefix="/api")
app.include_router(channels.router, prefix="/api")
app.include_router(source_groups.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(filters.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(
    websocket.router
)
app.include_router(
    auth.router,
    prefix="/api"
)
app.include_router(
    dashboard.router,
    prefix="/api"
)
app.include_router(
    vehicles.router,
    prefix="/api"
)
app.include_router(
    test.router,
    prefix="/api"
)
app.include_router(
    channels_live.router,
    prefix="/api"
)
