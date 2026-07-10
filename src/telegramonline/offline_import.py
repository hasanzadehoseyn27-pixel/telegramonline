from __future__ import annotations

import argparse
from pathlib import Path

from .parser import parse_message, split_export_messages
from .storage import connect, save_ads, stats


def import_export(export_path: str | Path, db_path: str | Path) -> dict[str, int]:
    messages = split_export_messages(export_path)
    ads = [parse_message(message_id, text) for message_id, text in messages]
    conn = connect(db_path)
    inserted = save_ads(conn, ads)
    current_stats = stats(conn)
    current_stats["seen_in_export"] = len(messages)
    current_stats["inserted"] = inserted
    conn.close()
    return current_stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Telegram group export into telegramonline SQLite database.")
    parser.add_argument("--export", required=True, help="Path to group_export_*.txt")
    parser.add_argument("--db", default="data/telegramonline.sqlite3", help="SQLite database path")
    args = parser.parse_args()
    result = import_export(args.export, args.db)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

