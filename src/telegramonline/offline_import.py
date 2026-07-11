from __future__ import annotations

import argparse

from .config import Settings
from .parser import parse_message_group, split_export_messages
from .storage import connect, save_ads, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ads from an exported group text file.")
    parser.add_argument("--export", required=True, help="Path to the exported .txt file.")
    parser.add_argument("--db", help="Path to sqlite database (defaults to DATABASE_PATH in .env).")
    args = parser.parse_args()

    settings = Settings.from_env()
    db_path = args.db or str(settings.database_path)

    messages = split_export_messages(args.export)
    conn = connect(db_path)

    ads = []
    for message_id, body in messages:
        ads.extend(parse_message_group(message_id, body, source="import"))

    inserted = save_ads(conn, ads)

    for key, value in stats(conn).items():
        print(f"{key}: {value}")
    print(f"seen_in_export: {len(messages)}")
    print(f"inserted: {inserted}")


if __name__ == "__main__":
    main()