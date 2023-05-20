import json
from typing import List, Union
from aiogram.types import \
    ReplyKeyboardMarkup as Keyboard, \
    KeyboardButton as Button, \
    InlineKeyboardMarkup as IKeyboard, \
    InlineKeyboardButton as IButton

from models import TgGroup, UserbotSession

class Keyboards:
    class US_Auth:
        @staticmethod
        def sendNewCode(session_name):
            k = IKeyboard()
            k.row(IButton("🔁 Прислать новый", callback_data=f"|us_auth:send_new_code:{session_name}"))
            return k
        
    class USessions:
        @staticmethod
        def main(sessions: List[UserbotSession]):
            k = IKeyboard()
            for session in sessions:
                k.row(IButton(session.name, callback_data=f"|usessions:see:{session.id}"))
            k.row(IButton("➕ Добавить", callback_data=f"|usessions:new"))
            k.row(IButton("⬅️ Назад", callback_data=f"|main"))
            return k
        
        @staticmethod
        def showUSession(usession: UserbotSession):
            k = IKeyboard()
            k.row(IButton("♻️ Переавторизовать", callback_data=f"|usessions:reauthorize:{usession.id}"))
            k.row(IButton("🗑️ Удалить", callback_data=f"|usessions:delete_popup:{usession.id}"))
            k.row(IButton("⬅️ Назад", callback_data=f"|usessions:main"))
            return k
        
    class Groups:
        @staticmethod
        def main(groups: List[TgGroup]):
            k = IKeyboard()
            for group in groups:
                k.row(IButton(group.title, callback_data=f"|groups:see:{group.chat_id}"))
            k.row(IButton("➕ Добавить", callback_data=f"|groups:new"))
            k.row(IButton("⬅️ Назад", callback_data=f"|main"))
            return k
        
        @staticmethod
        def chooseUserbots(userbots: List[UserbotSession], selected=[], group=None):
            k = IKeyboard()
            any_selected = selected != []
            for ub in userbots:
                s = "" if ub.id not in selected else "☑️ "
                k.row(IButton(s + f"{ub.name} | {ub.login}", callback_data=f"|choose_ubots:choose:{ub.id}"))
            if any_selected:
                k.row(IButton("🏁 Завершить", callback_data=f"|choose_ubots:done"))
            if group:
                k.row(IButton("⬅️ Назад", callback_data=f"|groups:see:{group.chat_id}"))
            return k
        
        @staticmethod
        def showGroup(group):
            k = IKeyboard()
            k.row(IButton("⬅️ Назад", callback_data=f"|groups:main"))
            return k
        
        @staticmethod
        def editGroup(group: TgGroup):
            k = IKeyboard()
            
            # Я решил отказаться от изменения chat id, так как он являлся primary-key в бд коллекции
            # key = "_id"
            # k.row(IButton("ID чата", callback_data=f"|groups:change:{group.chat_id}:{key}"))
            
            key = "ubs"
            k.row(IButton("🤖 Юзерботы", callback_data=f"|groups:change_ubots:{group.chat_id}"))
            key = "title"
            k.row(IButton("🏷️ Название", callback_data=f"|groups:change:{group.chat_id}:{key}"))
            
            key = "keywords"
            k.row(IButton("Ключ-слова", callback_data=f"|groups:change:{group.chat_id}:{key}"))
            k.insert(IButton("➕", callback_data=f"|groups:add:{group.chat_id}:{key}"))
            k.insert(IButton("🗑️", callback_data=f"|groups:clear_popup:{group.chat_id}:{key}"))
            
            key = "bad_keywords"
            k.row(IButton("Минус-слова", callback_data=f"|groups:change:{group.chat_id}:{key}"))
            k.insert(IButton("➕", callback_data=f"|groups:add:{group.chat_id}:{key}"))
            k.insert(IButton("🗑️", callback_data=f"|groups:clear_popup:{group.chat_id}:{key}"))
            
            key = "blacklist_users"
            k.row(IButton("Блэк-лист пользователи", callback_data=f"|groups:change:{group.chat_id}:{key}"))
            k.insert(IButton("➕", callback_data=f"|groups:add:{group.chat_id}:{key}"))
            k.insert(IButton("🗑️", callback_data=f"|groups:clear_popup:{group.chat_id}:{key}"))
            
            k.row(IButton("🗑️ Удалить группу 🗑️", callback_data=f"|groups:delete_group_popup:{group.chat_id}"))
            k.row(IButton("⬅️ Назад", callback_data=f"|groups:main"))
            return k
                
    
    @staticmethod
    def startMenu(user):
        k = IKeyboard()
        k.row(IButton("💬 Группы", callback_data=f"|groups:main"))
        k.row(IButton("🤖 Юзерботы", callback_data=f"|usessions:main"))
        return k
            
    
    @staticmethod
    def Popup(path):
        k = IKeyboard()
        k.row(IButton("Да", callback_data=path))
        k.row(IButton("Нет", callback_data=f"cancel_popup"))
        return k
            
        
    @staticmethod
    def gotoMessage(link):
        k = IKeyboard()
        k.row(IButton("Перейти к сообщению", url=link))
        return k
        
    @staticmethod
    def inline_keyboard_to_dict(inline_keyboard_markup):
        inline_keyboard = []

        for row in inline_keyboard_markup.inline_keyboard:
            keyboard_row = []
            for button in row:
                button_dict = {
                    "text": button.text,
                }
                if button.url:
                    button_dict["url"] = button.url
                elif button.callback_data:
                    button_dict["callback_data"] = button.callback_data
                # Add other button types if needed (e.g., switch_inline_query, etc.)

                keyboard_row.append(button_dict)
            inline_keyboard.append(keyboard_row)

        return {"inline_keyboard": inline_keyboard}