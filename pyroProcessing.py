import asyncio
import json
import traceback
from typing import List

import requests
from loader import API_HASH, API_ID, BOT_TOKEN
from etc.keyboards import Keyboards
from models import UserbotSession, AutopostSlot
from pyrogram import Client
from pyrogram.types import Dialog, Chat
import pyrogram
from pyrogram.errors.exceptions.unauthorized_401 import *
import loguru
from loader import dp

def sendMessageFromBotSync(chat_id, text, reply_markup=None):
    if reply_markup is not None:
        reply_markup = json.dumps({'inline_keyboard': [[{'text': button.text, 'callback_data': button.callback_data, 'url': button.url} for button in row] for row in reply_markup.inline_keyboard]}, ensure_ascii=False, indent=4)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": "HTML",
    }

    response = requests.post(url, data=payload)

    return response.status_code == 200

def userbotSessionToPyroClient(session: UserbotSession) -> Client:
    return Client(
        name=session.name,
        session_string=session.string_session,
        api_id=API_ID,
        api_hash=API_HASH,
    )

async def send_message(chat_id, text):
    await dp.bot.send_message(chat_id, text, parse_mode="HTML")

def start_pyro_client(_, stop_event, usession: UserbotSession):
    async def run_client():
        client = userbotSessionToPyroClient(usession)


        @client.on_message()
        async def handle_messages(client: pyrogram.Client, message: pyrogram.types.Message):
            import traceback
            groups: List[AutopostSlot] = AutopostSlot.objects.all()
            
        # Start the client
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
                await asyncio.sleep(1)  # Adjust sleep time as needed

            await client.stop()
        except (AuthKeyUnregistered, AuthKeyInvalid, AuthKeyPermEmpty):
            groups: List[AutopostSlot] = AutopostSlot.objects.all()
            for gr in groups:
                if usession.id in gr.ubs:
                    sendMessageFromBotSync(gr.chat_id, f"⚠️ Привязанный к этой группе юзербот <b>{usession.name}</b> с телефоном <code>{usession.login}</code> вылетел из сессии и не может проверять сообщения в чатах! Замените юзербота или переавторизуйте его")

            usession.is_dead = True
            usession.save()
        except Exception as e:
            loguru.logger.error(f"Can't start userbot client, error: {e} {type(e)} {traceback.format_exc()}")
                
    asyncio.run(run_client())
