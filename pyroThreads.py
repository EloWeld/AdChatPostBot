import asyncio
import json
import threading
import traceback
from typing import List

import requests
from etc.utils import sendMessageFromBotSync, userbotSessionToPyroClient
from loader import API_HASH, API_ID, BOT_TOKEN
from etc.keyboards import Keyboards
from models import UserbotSession, AutopostSlot
from pyrogram import Client
from pyrogram.types import Dialog, Chat
import pyrogram
from pyrogram.errors.exceptions.unauthorized_401 import *
import loguru
from loader import dp

async def send_message(chat_id, text):
    await dp.bot.send_message(chat_id, text, parse_mode="HTML")

def start_pyro_client(stop_event: threading.Event(), usession: UserbotSession):
    async def run_client():
        client = userbotSessionToPyroClient(usession)


        @client.on_message()
        async def handle_messages(c: pyrogram.Client, message: pyrogram.types.Message):
            if str(message.chat.id) not in usession.chats:
                n_chat = await c.get_chat(message.chat.id)
                usession.chats[str(message.chat.id)] = json.loads(json.dumps(n_chat.__dict__, ensure_ascii=False, default=str))
                usession.save()
            
        #Start the client
        try:
            await client.start()
            dialogs = client.get_dialogs()
            async for dialog in dialogs:
                dialog: Dialog = dialog
                chat: Chat = dialog.chat
                chat_id = chat.id
                if chat.type not in [pyrogram.enums.ChatType.GROUP, pyrogram.enums.ChatType.SUPERGROUP]:
                    continue
                usession.chats[str(chat_id)] = json.loads(json.dumps(chat.__dict__, ensure_ascii=False, default=str))
            usession.save()
            while not stop_event.is_set():
                await asyncio.sleep(2)  # Adjust sleep time as needed
                

            await client.stop()
        except (AuthKeyUnregistered, AuthKeyInvalid, AuthKeyPermEmpty):
            slots: List[AutopostSlot] = AutopostSlot.objects.all()
            for slot in slots:
                if usession.id in slot.ubots:
                    sendMessageFromBotSync(slot.reports_group_id, f"⚠️ Привязанный к этой слоту #{slot.id} юзербот <b>{usession.name}</b> с телефоном <code>{usession.login}</code> вылетел из сессии и не может проверять сообщения в чатах! Замените юзербота или переавторизуйте его")

            usession.is_dead = True
            usession.save()
        except pyrogram.errors.exceptions.not_acceptable_406.AuthKeyDuplicated:
            slots: List[AutopostSlot] = AutopostSlot.objects.all()
            for slot in slots:
                if usession.id in slot.ubots:
                    sendMessageFromBotSync(slot.reports_group_id, f"⚠️ Привязанный к этой слоту #{slot.id} юзербот <b>{usession.name}</b> с телефоном <code>{usession.login}</code> авторизирован в двух местах одновременно! Замените юзербота или переавторизуйте его")

            usession.is_dead = True
            usession.save()
        except Exception as e:
            loguru.logger.error(f"Can't start userbot client, error: {e} {type(e)} {traceback.format_exc()}")
                
    asyncio.run(run_client())
    pass
