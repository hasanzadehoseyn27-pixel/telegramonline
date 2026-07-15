from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon import TelegramClient

from .config import Settings
from .net import parse_proxy_from_env
from .parser import parse_message_group
from .storage import _compute_day_key


def _normalize_group(value: str) -> str:
    value = value.strip()
    if value.startswith("https://t.me/"):
        return value.removeprefix("https://t.me/").strip("/")
    if value.startswith("t.me/"):
        return value.removeprefix("t.me/").strip("/")
    return value.lstrip("@")


async def discover(
    group: str,
    days: int,
    output: Path,
    use_proxy: bool = True,
) -> dict:
    settings = Settings.from_env()
    client = TelegramClient(
        "telegramonline_user",
        settings.api_id,
        settings.api_hash,
        proxy=parse_proxy_from_env() if use_proxy else None,
        timeout=20,
        connection_retries=1,
        request_retries=1,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counter: Counter[tuple[str, str]] = Counter()
    examples: dict[str, dict] = {}
    total_messages = 0
    parsed_ads = 0

    print(f"connecting group={group} days={days} proxy={'on' if use_proxy else 'off'}", flush=True)
    await asyncio.wait_for(client.start(), timeout=40)
    async with client:
        async for message in client.iter_messages(_normalize_group(group)):
            message_date = message.date
            if message_date and message_date.tzinfo is None:
                message_date = message_date.replace(tzinfo=timezone.utc)
            if message_date and message_date < cutoff:
                break
            if not message.message:
                continue
            total_messages += 1
            if total_messages % 250 == 0:
                print(f"seen={total_messages} parsed_ads={parsed_ads}", flush=True)
            ads = parse_message_group(
                str(message.id),
                message.message,
                message_date,
                source="discover",
            )
            parsed_ads += len(ads)
            for ad in ads:
                if not ad.vehicle_key or not ad.vehicle_name:
                    continue
                key = (ad.vehicle_key, ad.vehicle_name)
                counter[key] += 1
                examples.setdefault(
                    ad.vehicle_key,
                    {
                        "vehicle_key": ad.vehicle_key,
                        "vehicle_name": ad.vehicle_name,
                        "example": ad.raw_text[:500],
                        "message_id": ad.source_message_id,
                        "day_key": _compute_day_key(ad.message_date),
                    },
                )

    items = [
        {
            "vehicle_key": key,
            "vehicle_name": name,
            "count": count,
            "example": examples.get(key, {}).get("example"),
            "message_id": examples.get(key, {}).get("message_id"),
            "day_key": examples.get(key, {}).get("day_key"),
        }
        for (key, name), count in counter.most_common()
    ]
    result = {
        "group": group,
        "days": days,
        "total_messages": total_messages,
        "parsed_ads": parsed_ads,
        "unique_vehicle_names": len(items),
        "items": items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("group")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/discovered_vehicles_week.json"),
    )
    parser.add_argument("--no-proxy", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(discover(args.group, args.days, args.output, use_proxy=not args.no_proxy))
    print(
        f"messages={result['total_messages']} parsed_ads={result['parsed_ads']} "
        f"unique_vehicle_names={result['unique_vehicle_names']} output={args.output}"
    )


if __name__ == "__main__":
    main()
