"""Markaziy sozlamalar (.env orqali)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int_list(value: str) -> tuple:
    out = []
    for x in (value or "").replace(";", ",").split(","):
        x = x.strip()
        if x.lstrip("-").isdigit():
            out.append(int(x))
    return tuple(out)


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        path = os.getenv("SQLITE_PATH", "data/kino.db")
        return f"sqlite+aiosqlite:///{path}"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").strip()
    admin_ids: tuple = _int_list(os.getenv("ADMIN_ID", ""))
    database_url: str = _db_url()
    webapp_url: str = (os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
    port: int = int(os.getenv("PORT", "8080"))
    default_lang: str = os.getenv("DEFAULT_LANG", "uz")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    backup_every_hours: int = int(os.getenv("BACKUP_EVERY_HOURS", "24"))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
