
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
from etc.utils import check_html_tags, download_chat_photo
from loader import *
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import *
from models import AutopostSlot, TgUser, UserbotSession
from slotsThreads import slot_updated
from states import ChangeSlotStates


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
        