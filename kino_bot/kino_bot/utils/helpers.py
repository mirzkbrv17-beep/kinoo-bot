"""Umumiy yordamchi funksiyalar."""
import html
import re
from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    """Naive UTC vaqt (bazada shu formatda saqlanadi)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def fmt_dt(dt) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else "—"


def fmt_date(dt) -> str:
    return dt.strftime("%d.%m.%Y") if dt else "—"


def search_key(*parts) -> str:
    return " ".join(str(p).lower() for p in parts if p).strip()


def norm_code(code: str) -> str:
    return (code or "").strip().upper()


def period_start(period: str):
    now = utcnow()
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    return None


def fmt_duration(minutes) -> str:
    if not minutes:
        return ""
    h, m = divmod(int(minutes), 60)
    return f"{h} soat {m} daq" if h else f"{m} daq"


def chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def clean_text(text: str, limit: int = 4000) -> str:
    return re.sub(r"\s+\n", "\n", (text or "").strip())[:limit]
