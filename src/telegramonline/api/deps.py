from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from sqlite3 import Connection

from telegramonline.config import Settings
from telegramonline.storage import connect


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def get_db() -> Generator[Connection, None, None]:
    settings = get_settings()
    conn = connect(settings.database_path)
    try:
        yield conn
    finally:
        conn.close()