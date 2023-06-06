
import asyncio
import json
import random
import traceback
from uuid import uuid4
from aiogram import Bot, Dispatcher, types
import aiogram
import loguru
import pyrogram
from etc.keyboards import Keyboards
from etc.utils import check_html_tags, download_chat_photo, userbotSessionToPyroClient
from loader import *
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import *
from models import AutopostSlot, TgUser, UserbotSession
from slotsThreads import slot_updated
from states import ChangeSlotStates
from pyrogram.client import Client
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid

# Обработчик callback-запросов для работы с чатами слотов
@dp.callback_query_handler(text_contains="|chats", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    global threads
    actions = c.data.split(":")[1:]
    slot: AutopostSlot = AutopostSlot.objects.get({"_id": actions[1]})

    if actions[0] == "delete_slot_chat":
        if actions[-1] == "!":
            chat_id = actions[2]
            del slot.chats[chat_id]
            
            func = c.message.edit_caption if c.message.photo else c.message.edit_text
            await func(f"🗑️ Чат удалён из рассылки")
            slot.save()
            return
        

@dp.message_handler(state=ChangeSlotStates.chats)
async def _(message: types.Message, state: FSMContext):
    global threads
    chat_ids = [x.strip() for x in message.text.replace('\n', ' ').replace(';', ' ').replace(',', ' ').split()]
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    counter = 0
    if len(slot.ubots) == 0:
            await message.answer('⚠️ Подключите юзерботов к слоту, чтобы они вошли в группы! Сейчас юзерботы не подключены и добавить чат не получиться')
    else:
        for chat_identifier in chat_ids:
            for slot_chat_id, slot_chat in slot.chats.items():
                if chat_identifier.replace('@', '') in [str(slot_chat['username'])]:
                    await message.answer(f"⚠️ Чат <code>{chat_identifier}</code> был уже добавлен в список чатов" )
                    continue
            if '-100' in chat_identifier:
                chat_identifier = int(chat_identifier)
            for ubot in slot.ubots:
                ubot: UserbotSession = ubot
                client: Client = userbotSessionToPyroClient(ubot)
                
                await client.start()
                try:
                    chat = await client.get_chat(chat_identifier)
                except Exception as e:
                    loguru.logger.error(e)
                    chat = None
                if chat is None or isinstance(chat, pyrogram.types.ChatPreview):
                    # If chat is None - try to join
                    try:
                        chat = await client.get_chat(chat_identifier)
                        await message.answer(f"✅ Юзербот <code>{ubot.id}</code> зашёл в чат <code>{chat_identifier}</code>")
                    except PeerIdInvalid:
                        await message.answer(f"⚠️ Юзербот <code>{ubot.id}</code> не смог зайти в чат <code>{chat_identifier}</code> так как используемый идентификатор чата некорректен. Проверьте что такой чат существует")
                    except Exception as e:
                        print(f"Failed to join the group: {e}")
                        await message.answer(f"⚠️ Юзербот <code>{ubot.id}</code> не смог зайти в чат <code>{chat_identifier}</code>. Ошибка: <b>{e}</b")
                await client.stop()
                # If it is still None - error
                if chat is None:
                    await message.answer(f"⚠️ Чат <code>{chat_identifier}</code> не добавлен у юзербота <code>{ubot.name}</code> | <code>{ubot.login}</code>, чат не добавлен")
                    continue
                if chat is None:
                    await message.answer(f"⚠️ В чате <code>{chat_identifier}</code> юзербот <code>{ubot.name}</code> | <code>{ubot.login}</code> не может писать сообщения, чат не добавлен")
                    continue
                slot.chats[str(chat.id)] = json.loads(json.dumps(chat.__dict__, ensure_ascii=False, default=str))
                counter += 1
            
    await message.answer(f"✅ Добавлено {counter} чатов!")
    slot.save()
            
    await message.answer("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.SlotChats.seeSlotChats(slot))
    await state.finish()
    await slot_updated(slot)
