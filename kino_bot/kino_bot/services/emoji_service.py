"""Premium (animatsiyali) custom emoji ID'lari: keshlash va tugma yasash.

Bot API 9.4+: KeyboardButton/InlineKeyboardButton.icon_custom_emoji_id.
ID yo'q yoki Telegram rad etsa — oddiy emoji fallback ishlaydi.
"""
import logging

from sqlalchemy import select

from database.models import CustomEmoji
from utils.helpers import utcnow
from utils.texts import MENU_FALLBACK

log = logging.getLogger(__name__)


class EmojiService:
    def __init__(self):
        self.ids: dict = {}
        self.disabled: bool = False  # Telegram rad etsa avtomatik True bo'ladi

    async def load(self, s) -> None:
        rows = (await s.execute(select(CustomEmoji))).scalars().all()
        self.ids = {r.key: r.emoji_id for r in rows if r.emoji_id}

    async def set_id(self, s, key: str, emoji_id) -> None:
        row = await s.get(CustomEmoji, key)
        if row is None:
            row = CustomEmoji(key=key, fallback=MENU_FALLBACK.get(key, ""))
            s.add(row)
        row.emoji_id = emoji_id or None
        row.updated_at = utcnow()
        await s.flush()
        await self.load(s)

    def icon(self, key: str):
        return None if self.disabled else self.ids.get(key)

    def has_any(self) -> bool:
        return bool(self.ids) and not self.disabled


emoji_service = EmojiService()
