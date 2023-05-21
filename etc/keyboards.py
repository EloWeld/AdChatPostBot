import json
from typing import List, Union
from aiogram.types import \
    ReplyKeyboardMarkup as Keyboard, \
    KeyboardButton as Button, \
    InlineKeyboardMarkup as IKeyboard, \
    InlineKeyboardButton as IButton

from models import AutopostSlot, UserbotSession

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
            k.row(IButton("‹ Назад", callback_data=f"|main"))
            return k
        
        @staticmethod
        def showUSession(usession: UserbotSession):
            k = IKeyboard()
            k.row(IButton("♻️ Переавторизовать", callback_data=f"|usessions:reauthorize:{usession.id}"))
            k.row(IButton("🗑️ Удалить", callback_data=f"|usessions:delete_popup:{usession.id}"))
            k.row(IButton("‹ Назад", callback_data=f"|usessions:main"))
            return k
        
    class Slots:
        @staticmethod
        def main(slots: List[AutopostSlot]):
            k = IKeyboard()
            for slot in slots:
                k.row(IButton(f"{slot.emoji} {slot.name}", callback_data=f"|slots:see:{slot.id}"))
            k.row(IButton("➕ Добавить", callback_data=f"|slots:new"))
            k.row(IButton("‹ Назад", callback_data=f"|main"))
            return k
        
        @staticmethod
        def chooseUserbots(userbots: List[UserbotSession], selected=[], slot=None):
            k = IKeyboard()
            any_selected = selected != []
            for ub in userbots:
                s = "" if ub.id not in selected else "☑️ "
                k.row(IButton(s + f"{ub.name} | {ub.login}", callback_data=f"|slot_menu:choose_ubots:{ub.id}"))
            if any_selected:
                k.row(IButton("🏁 Завершить", callback_data=f"|slot_menu:choose_ubots:done"))
            if slot:
                k.row(IButton("‹ Назад", callback_data=f"|slots:see:{slot.id}"))
            return k
        
        @staticmethod
        def showSlot(slot):
            k = IKeyboard()
            k.row(IButton("‹ Назад", callback_data=f"|groups:main"))
            return k
        
        @staticmethod
        def editSlot(slot: AutopostSlot):
            k = IKeyboard()
           
            k.row(IButton("[❌›✅] Включить слот" if slot.status=='inactive' else "[✅›❌] Вылючить слот", callback_data=f"|slot_menu:turn:{slot.id}"))
            key = "name"
            k.row(IButton("🏷️ Изменить название", callback_data=f"|slot_menu:change:{key}:{slot.id}"))
            key = "logs"
            k.insert(IButton("🪵 Изменить чат для логов", callback_data=f"|slot_menu:change:{key}:{slot.id}"))
            k.row(IButton("💬 Чаты для расслыки", callback_data=f"|slot_menu:chats:{slot.id}"))
            k.insert(IButton("💌 Контент рассылки", callback_data=f"|slot_menu:postings:{slot.id}"))
            k.row(IButton("🤖 Подключенные юзерботы", callback_data=f"|slot_menu:ubots:{slot.id}"))
            k.row(IButton("📆 Расписание", callback_data=f"|slot_menu:schedule:{slot.id}"))
           
            k.row(IButton("🗑️ Удалить слот", callback_data=f"|slot_menu:delete_slot:{slot.id}"))
            k.insert(IButton("‹ Назад", callback_data=f"|slots:main"))
            return k
                
    
    @staticmethod
    def startMenu(user):
        k = IKeyboard()
        k.row(IButton("🗃️ Слоты", callback_data=f"|slots:main"))
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
                
    
    @staticmethod
    def back(path):
        k = IKeyboard()
        k.row(IButton("‹ Назад", callback_data=path))
        return k