from aiogram.dispatcher.filters.state import State, StatesGroup

class AuthSessionState(StatesGroup):
    session_name = State()
    login = State()
    code = State()
    password = State()
    change_name = State()
    
class ChangeSlotStates(StatesGroup):
    name = State()
    schedule = State()
    postings = State()
    logsChat = State()
    chats = State()
    date_schedule = State()