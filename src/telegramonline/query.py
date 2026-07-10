from __future__ import annotations

import argparse
import sys

from .storage import connect, lowest_by_vehicle


def format_price(value: int | None) -> str:
    if value is None:
        return "نامشخص"
    return f"{value:,} میلیون".replace(",", "/")


def format_row(row) -> str:
    details = []
    if row["year"]:
        details.append(f"مدل {row['year']}")
    if row["month"]:
        details.append(f"برج {row['month']}")
    if row["color"]:
        details.append(row["color"])
    if row["phone"]:
        details.append(row["phone"])
    suffix = " | ".join(details)
    if suffix:
        suffix = " | " + suffix
    return f"{row['vehicle_name']}: {format_price(row['price_million'])}{suffix}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Show lowest valid prices.")
    parser.add_argument("--db", default="data/telegramonline.sqlite3")
    parser.add_argument("--days", type=int)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--vehicle")
    args = parser.parse_args()

    conn = connect(args.db)
    rows = lowest_by_vehicle(conn, days=args.days, limit=args.limit, vehicle_query=args.vehicle)
    if not rows:
        print("No valid ads found.")
        return
    for index, row in enumerate(rows, start=1):
        print(f"{index}. {format_row(row)}")
        print(row["raw_text"][:500].strip())
        print("-" * 60)


if __name__ == "__main__":
    main()
