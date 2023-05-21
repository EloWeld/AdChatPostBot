from aiogram.dispatcher.filters.state import State, StatesGroup

class AuthSessionState(StatesGroup):
    session_name = State()
    login = State()
    code = State()
    password = State()
    
class ChangeSlotStates(StatesGroup):
    name = State()
    schedule = State()
    postings = State()
    logsChat = State()
    posting_chats = State()