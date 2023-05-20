from aiogram.dispatcher.filters.state import State, StatesGroup

class AuthSessionState(StatesGroup):
    session_name = State()
    login = State()
    code = State()
    password = State()
    
class AddGroupState(StatesGroup):
    name = State()
    chatID = State()
    keywords = State()
    bad_keywords = State()
    ubs = State()
    blacklist = State()
    
class ChangeGroupStates(StatesGroup):
    Add = State()
    Change = State()
    Clear = State()
    ubs = State()
    