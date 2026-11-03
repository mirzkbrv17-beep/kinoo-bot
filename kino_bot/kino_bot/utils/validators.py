"""Tekshiruvlar: URL, kod, yil, WebApp initData imzosi."""
import hashlib
import hmac
import json
import re
import time
from typing import Optional
from urllib.parse import parse_qsl

CODE_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


def is_url(text: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+\.[^\s]+$", (text or "").strip(), re.I))


def valid_code(text: str) -> bool:
    return bool(CODE_RE.match((text or "").strip()))


def parse_year(text: str) -> Optional[int]:
    t = (text or "").strip()
    if t.isdigit() and 1888 <= int(t) <= 2100:
        return int(t)
    return None


def parse_duration(text: str) -> Optional[int]:
    t = (text or "").strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}", t):
        return int(t)
    m = re.fullmatch(r"(\d{1,2})[:.](\d{1,2})", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def parse_imdb(text: str) -> Optional[float]:
    try:
        v = float((text or "").strip().replace(",", "."))
    except ValueError:
        return None
    return round(v, 1) if 0 <= v <= 10 else None


def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> Optional[dict]:
    """Telegram WebApp initData HMAC tekshiruvi. To'g'ri bo'lsa user dict qaytaradi."""
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            return None
        check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, received_hash):
            return None
        if time.time() - int(pairs.get("auth_date", "0")) > max_age:
            return None
        user = json.loads(pairs.get("user", "{}"))
        return user if user.get("id") else None
    except Exception:
        return None


def sign_poster(kind: str, item_id: int, bot_token: str) -> str:
    return hmac.new(bot_token.encode(), f"poster:{kind}:{item_id}".encode(), hashlib.sha256).hexdigest()[:20]
