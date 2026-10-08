"""چک می‌کنه هر ربات توی گروه مقصد عضوه و می‌تونه بنویسه (بدون فرستادن پیام).

    $env:PYTHONPATH="src"; py -m telegramonline.check_forward_bots
"""
from __future__ import annotations

import httpx

from .bot_forwarder import _normalize_chat, _short
from .config import Settings, load_dotenv, load_bot_tokens


def main() -> None:
    load_dotenv()
    import os

    tokens = load_bot_tokens()
    chat = _normalize_chat(os.getenv("FORWARD_TARGET_GROUP", ""))
    if not tokens:
        print("هیچ توکنی پیدا نشد (FORWARD_BOT_TOKEN / FORWARD_BOT_TOKENS / bot_tokens.txt).")
        return
    if not chat:
        print("FORWARD_TARGET_GROUP تنظیم نشده.")
        return
    ok = bad = 0
    with httpx.Client(timeout=20) as http:
        for token in tokens:
            tag = _short(token)
            try:
                me = http.get(f"https://api.telegram.org/bot{token}/getMe").json()
                if not me.get("ok"):
                    print(f"❌ {tag}: توکن نامعتبر ({me.get('description')})")
                    bad += 1
                    continue
                name = "@" + me["result"].get("username", "?")
                act = http.post(
                    f"https://api.telegram.org/bot{token}/sendChatAction",
                    json={"chat_id": chat, "action": "typing"},
                ).json()
                if act.get("ok"):
                    print(f"✅ {name} ({tag}) در {chat} عضو است و می‌تواند بنویسد.")
                    ok += 1
                else:
                    print(f"❌ {name} ({tag}): {act.get('description')}")
                    bad += 1
            except Exception as exc:  # noqa: BLE001
                print(f"❌ {tag}: {type(exc).__name__}: {exc}")
                bad += 1
    print(f"\nجمع: {ok} سالم، {bad} مشکل‌دار، از {len(tokens)} توکن.")


if __name__ == "__main__":
    main()
