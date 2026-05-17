from aiogram.fsm.state import State, StatesGroup

class UserMode(StatesGroup):
    chat   = State()
    draw   = State()
    search = State()
    think  = State()
    dl     = State()

class CEOState(StatesGroup):
    broadcast = State()
    ban_input = State()
