from aiogram.fsm.state import State, StatesGroup


class UserForm(StatesGroup):
    request = State()
    support = State()
    promo = State()
