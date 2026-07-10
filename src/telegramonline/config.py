from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    api_id: int
    api_hash: str
    bot_token: str
    group: str
    database_path: Path
    export_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        api_id = os.getenv("TELEGRAM_API_ID", "").strip()
        if not api_id:
            raise RuntimeError("TELEGRAM_API_ID is missing.")
        api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
        if not api_hash:
            raise RuntimeError("TELEGRAM_API_HASH is missing.")
        return cls(
            api_id=int(api_id),
            api_hash=api_hash,
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            group=os.getenv("TELEGRAM_GROUP", "").strip(),
            database_path=Path(os.getenv("DATABASE_PATH", "data/telegramonline.sqlite3")),
            export_path=Path(os.getenv("EXPORT_PATH", "")),
        )

