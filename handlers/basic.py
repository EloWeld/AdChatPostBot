import asyncio
from typing import List
from aiogram import Bot, Dispatcher, types
from etc.keyboards import Keyboards
from loader import *
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import *
from models import AutopostSlot, TgUser
from states import AuthSessionState


@dp.callback_query_handler(text_contains="|main", state="*")
async def _(c: CallbackQuery, state: FSMContext):
    # Send welcome
    user = TgUser.objects.get({'_id': c.from_user.id})
    await c.message.edit_text("🏠 Главное меню", reply_markup=Keyboards.startMenu(user))


@dp.callback_query_handler(text_contains="cancel_popup", state="*")
async def _(c: CallbackQuery, state: FSMContext):
    await c.message.delete()


# Start command
@dp.message_handler(commands=["start"], state="*")
async def start_command(message: types.Message, state: FSMContext=None):
    if state:
        await state.finish()
        
    if message.chat.type in [types.ChatType.SUPERGROUP, types.ChatType.GROUP]:
        await message.answer(f"ℹ️ ChatID этой группы: <code>{message.chat.id}</code>")
        return
    try:
        user = TgUser.objects.get({'_id': message.from_user.id})
    except TgUser.DoesNotExist:
        user = TgUser(message.from_user.id)

    # User exists already
    user.first_name = message.from_user.first_name
    user.last_name = message.from_user.last_name
    user.username = message.from_user.username
    user.save()

    # Send welcome
    await bot.send_message(chat_id=message.chat.id, text="🏠 Главное меню", reply_markup=Keyboards.startMenu(user))

    # Set bot commands
    await bot.set_my_commands([])
    await bot.set_my_commands([
        BotCommand("start", "Презапуск бота"),
        BotCommand("stats", "Статистика"),
        BotCommand("help", "Помощь")
    ], scope=BotCommandScopeAllPrivateChats())


# Get statistics
@dp.message_handler(commands=["stats"], chat_type=ChatType.PRIVATE)
async def get_stats(message: types.Message):
    chat_id = message.chat.id

    groups: List[AutopostSlot] = AutopostSlot.objects.all()
    sender_groups = {}
    fwded_messages_count = 0
    for gr in groups:
        for fwd in gr.forwarded_msgs:
            if fwd['from_chat'] not in sender_groups:
                sender_groups[fwd['from_chat']] = dict(title=fwd['from_chat_title'], id=fwd['from_chat'], msgs=[])
                
            sender_groups[fwd['from_chat']]['msgs'] += [fwd]
            fwded_messages_count += 1
            
    stats_text = ""
    for x in sender_groups:
        stats_text += f"Из группы <a href='https://t.me/c/{str(x).replace('-100','').replace('-','')}'>{sender_groups[x]['title']}</a> переслано {len(sender_groups[x]['msgs'])} сообщений\n"
    
    await message.reply(f"Статистика: Переслано {fwded_messages_count:,} сообщений.\n\n" + stats_text)

# Get help


@dp.message_handler(commands=["help"], chat_type=ChatType.PRIVATE)
async def help_command(message: types.Message):
    help_text = """
Команды для управления ботом:

/start - Перезапуск бота
/stats - Получить статистику
/auth_ub - Добавить юзербота
/ping - Проверить работает ли бот
/help - Отобразить эту справочную информацию
"""

    await message.reply(help_text)

# Ping pong for check bot available


@dp.message_handler(commands=["ping"])
async def ping(message: types.Message):
    await message.reply("pong")
