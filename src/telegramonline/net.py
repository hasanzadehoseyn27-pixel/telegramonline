from __future__ import annotations

import os
from urllib.parse import urlparse


def resolve_chat_id(group: str) -> int | str:
    """اگر شناسه گروه عددی باشد (مثل -1002027760235)، به int تبدیل می‌شود.

    وگرنه Telethon آن را به‌اشتباه به‌عنوان یوزرنیم/شماره تلفن می‌بیند.
    """
    group = group.strip()
    try:
        return int(group)
    except ValueError:
        return group


def parse_proxy_from_env():
    raw = os.getenv("TELEGRAM_PROXY", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme not in {"socks5", "socks4", "http"}:
        raise RuntimeError("TELEGRAM_PROXY must start with socks5://, socks4://, or http://")
    if not parsed.hostname or not parsed.port:
        raise RuntimeError("TELEGRAM_PROXY must include host and port, like socks5://127.0.0.1:10808")
    import socks
    proxy_type = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4, "http": socks.HTTP}[scheme]
    return (proxy_type, parsed.hostname, parsed.port, True, parsed.username, parsed.password)