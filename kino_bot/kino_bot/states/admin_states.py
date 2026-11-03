from aiogram.fsm.state import State, StatesGroup


class ContentForm(StatesGroup):
    fill = State()        # kino / serial / qism qo'shish (bosqichma-bosqich)


class EditForm(StatesGroup):
    code = State()
    value = State()


class DelForm(StatesGroup):
    code = State()


class GenreForm(StatesGroup):
    add = State()


class UserMgmt(StatesGroup):
    wait_id = State()
    wait_days = State()


class BroadcastForm(StatesGroup):
    content = State()
    confirm = State()


class PromoForm(StatesGroup):
    create = State()


class StaffForm(StatesGroup):
    wait_id = State()


class ChannelForm(StatesGroup):
    add = State()


class EmojiForm(StatesGroup):
    wait = State()


class SettingForm(StatesGroup):
    value = State()


class ReplyForm(StatesGroup):
    text = State()
