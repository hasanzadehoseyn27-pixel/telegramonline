from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(
    title="TelegramOnline API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
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
