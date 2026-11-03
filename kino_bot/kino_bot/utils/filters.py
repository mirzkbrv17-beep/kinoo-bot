from aiogram import F

from utils.texts import is_menu_text, menu_key


def menu(key: str):
    return F.text.func(lambda txt: menu_key(txt) == key)


NOT_MENU = ~F.text.func(is_menu_text)
NOT_CMD = ~F.text.startswith("/")
