"""یک کانال را کامل از telegramonline حذف و بلاک می‌کند.

    $env:PYTHONPATH="src"
    python tools/remove_channel.py akhbar1khatii

- کانال بلاک می‌شود → اگر دوباره کسی از آن فوروارد کند، خودکار اضافه نمی‌شود.
- همه‌ی آگهی‌هایش از دیتابیس telegramonline پاک می‌شود.
- کانال «غیرفعال» می‌شود؛ collector در دور بعدیِ sync با همان اکانتی که عضو شده
  از کانال خارج می‌شود و ردیف کانال را حذف می‌کند (فقط او می‌تواند Leave بزند).
آگهی‌های خودِ سایت (Redis) با tools/delete_site_channel.lua پاک می‌شوند.
"""

from __future__ import annotations

import sys

from telegramonline.config import Settings
from telegramonline.storage import (
    _clean_username,
    block_channel,
    connect,
    deactivate_channel,
    delete_ads_for_channel,
)


def main() -> None:
    if len(sys.argv) != 2:
        print("استفاده: python tools/remove_channel.py <username>")
        sys.exit(1)
    username = _clean_username(sys.argv[1])
    settings = Settings.from_env()
    conn = connect(settings.database_path)

    block_channel(conn, username, "manual")
    print(f"⛔ «{username}» بلاک شد (دیگر خودکار اضافه نمی‌شود).")

    rows = conn.execute(
        "SELECT * FROM channels WHERE lower(username) = lower(?)", (username,)
    ).fetchall()
    if not rows:
        print("این کانال در لیست کانال‌های telegramonline نبود.")
        return

    for row in rows:
        deleted = delete_ads_for_channel(conn, row["id"])
        if row["joined"]:
            deactivate_channel(conn, row["id"])
            print(
                f"🗑 {deleted} آگهی از «{row['username']}» پاک شد. "
                "collector در دور بعد از کانال خارج می‌شود."
            )
        else:
            conn.execute("DELETE FROM channels WHERE id = ?", (row["id"],))
            conn.commit()
            print(f"🗑 {deleted} آگهی و خود کانال «{row['username']}» پاک شد.")


if __name__ == "__main__":
    main()
