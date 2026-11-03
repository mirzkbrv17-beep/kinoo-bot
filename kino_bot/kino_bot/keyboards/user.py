"""Asosiy menyu (Reply keyboard) — premium emoji ikonkalari bilan."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from services.emoji_service import emoji_service
from utils.texts import MENU, menu_label


def main_menu(lang: str, use_icons: bool = True) -> ReplyKeyboardMarkup:
    buttons = []
    for key, fb in MENU:
        label = menu_label(lang, key)
        icon = emoji_service.icon(key) if use_icons else None
        if icon:
            buttons.append(KeyboardButton(text=label, icon_custom_emoji_id=icon))
        else:
            buttons.append(KeyboardButton(text=f"{fb} {label}"))
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]  # 3 tadan yonma-yon
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)
