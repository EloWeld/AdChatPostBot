import asyncio
import json
from typing import List

import requests
from loader import API_HASH, API_ID, BOT_TOKEN
from etc.keyboards import Keyboards
from models import UserbotSession, TgGroup
from pyrogram import Client
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

        def checkMessage(message: pyrogram.types.Message, group: TgGroup):
            is_good_message = False
            # If channel
            if message.from_user is None and message.sender_chat is not None:
                message.from_user = message.sender_chat
            # dont Recursion pls
            if group.chat_id == message.chat.id:
                is_good_message = False
                return False
            text = message.text if message.text is not None else message.caption if message.caption is not None else None
            if text is None:
                return False
            # Check message sender
            if str(message.from_user.id) in group.blacklist_users or message.from_user.username in group.blacklist_users:
                is_good_message = False
                return False
            # Check keywords
            for keyword in group.keywords:
                if keyword in text.lower():
                    is_good_message = True
                    break
            # Check minus words
            if is_good_message:
                for bad_keyword in group.bad_keywords:
                    if bad_keyword in text.lower():
                        is_good_message = False
                        return False
            return is_good_message

        @client.on_message()
        async def handle_messages(client: pyrogram.Client, message: pyrogram.types.Message):
            import traceback
            groups: List[TgGroup] = TgGroup.objects.all()
            for group in groups:
                if usession.id not in group.ubs:
                    continue
                is_good_message = checkMessage(message, group)
                if is_good_message:
                    try:
                        if message.chat.username:
                            linkToMessage = f"https://t.me/{message.chat.username}/{message.id}"
                        else:
                            linkToMessage = f"https://t.me/c/{str(message.chat.id).replace('-100', '').replace('-', '')}/{message.id}"

                        # Send message using requests
                        text = f"В группе <b>{message.chat.title}</b> есть отобранное сообщение\n\n{message.text[:4000] if message.text else message.caption[:4000]}\n\n<b>Кто: <code>{message.from_user.id}</code>|{message.from_user.first_name}|{message.from_user.last_name}|@{message.from_user.username}</b>"
                        sendMessageFromBotSync(group.chat_id, text, Keyboards.gotoMessage(linkToMessage))

                        loguru.logger.success(
                            f"Forward message {message.id} from chat {message.chat.id}")
                        group.forwarded_msgs += [dict(from_chat=message.chat.id,
                                                      from_chat_title=message.chat.title,
                                                      message_id=message.id,
                                                      message_text=message.text,
                                                      sender_id=message.from_user.id,
                                                      sender_username=message.from_user.username)]
                        group.save()
                    except Exception as e:
                        loguru.logger.error(
                            f"Can't forward message {message.id} from chat {message.chat.id}; error: {e}, traceback: {traceback.format_exc()}")
                        # await client.send_message(group.chat_id, f"Can't forward message {message.id} from chat {message.chat.id}; error: {e}, traceback: {traceback.format_exc()}")

        # Start the client
        try:
            await client.start()
            while not stop_event.is_set():
                await asyncio.sleep(1)  # Adjust sleep time as needed

            await client.stop()
        except (AuthKeyUnregistered, AuthKeyInvalid, AuthKeyPermEmpty):
            groups: List[TgGroup] = TgGroup.objects.all()
            for gr in groups:
                if usession.id in gr.ubs:
                    sendMessageFromBotSync(gr.chat_id, f"⚠️ Привязанный к этой группе юзербот <b>{usession.name}</b> с телефоном <code>{usession.login}</code> вылетел из сессии и не может проверять сообщения в чатах! Замените юзербота или переавторизуйте его")

            usession.is_dead = True
            usession.save()
        except Exception as e:
            loguru.logger.error(f"Can't start userbot client, error: {e} {type(e)}")
                
    asyncio.run(run_client())
