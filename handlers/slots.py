
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
import datetime
from etc.utils import cutText, remove_html_tags
from pyrogram.errors.exceptions.unauthorized_401 import AuthKeyUnregistered
from pyrogram.errors.exceptions.not_acceptable_406 import AuthKeyDuplicated


# Функция для отправки информации о слоте
async def sendSlot(msg: Message, slot: AutopostSlot, edit=False):
    func = msg.answer if not edit else msg.edit_text

    schdeule_text = "❌ Не установлено" if len(slot.schedule) == 0 else '\n'.join(f"▫️ <code>{x['min']}-{x['max']}</code>" for x in slot.schedule)
    postings_text = "❌ Не установлено" if len(slot.postings) == 0 else '\n'.join(f"▫️ {x.name if x.name else cutText(remove_html_tags(x.text), 10)}: отправлено <code>{x.sent_count}</code> раз" for i, x in enumerate(slot.postings))
    chats_text = "❌ Нет чатов" if len(slot.chats) == 0 else f"▫️ Подключено {len(slot.chats)} чатов, отправлено <code>{sum([x['sent_count'] if 'sent_count' in x else 0 for x in slot.chats.values()])}</code> сообщений"
    date_schedule_text = "❌ Даты рассылки не выбраны\n" if len(slot.date_schedule) == 0 else '▫️ ' + ', '.join(f"<code>{x['min'].strftime('%d.%m.%Y')}-{x['max'].strftime('%d.%m.%Y')}</code>" for x in slot.date_schedule) + "\n"

    await func(f"{slot.emoji} Слот <b>{slot.name}</b> <code>#{slot.id}</code>\n\n"
               f"<b>📝 Информация:</b>\n"
               f"▫️ Юзерботов подключено: <code>{len(slot.ubots)}</code> шт.\n"
               f"▫️ Чатов добавлено: <code>{len(slot.chats)}</code> шт.\n"
               f"▫️ Сообщений для рассылки: <code>{len(slot.postings)}</code> шт.\n"
               f"▫️ Статус работы: <code>{slot.get_verbose_status()}</code>\n"
               f"▫️ Чат для отчётов: <code>{slot.reports_group_id if slot.reports_group_id else '❌ Не задан'}</code>\n\n"
               f"<b>📆 Расписание:</b>\n"
               f"{date_schedule_text}{schdeule_text}\n\n"
               f"<b>💌 Контент рассылки:</b>\n"
               f"{postings_text}\n\n"
               f"<b>💬 Чаты:</b>\n"
               f"{chats_text}\n\n", 
               reply_markup=Keyboards.Slots.editSlot(slot))

async def sendSlotsMenu(msg: Message, edit=False):
    func = msg.answer if not edit else msg.edit_text
    slots: AutopostSlot = AutopostSlot.objects.all()
    await func("🗃️ Меню слотов", reply_markup=Keyboards.Slots.main(slots))



        
        
# Обработчик callback-запросов для работы с чатами слотов
@dp.callback_query_handler(text_contains="|slot_chats", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    global threads
    actions = c.data.split(":")[1:]
    slot: AutopostSlot = AutopostSlot.objects.get({"_id": actions[1]})

    if actions[0] == "see_chat":
        await c.answer("Отправляю чат")
        chat_id = int(actions[2])
        chat: dict = slot.chats[str(chat_id)]

        msg_text = f"💬 Чат <b>{chat['title']}</b>\n" \
                   f"🔗 Ссылка: <b>{'@'+chat['username'] if chat['username'] else 'Отсутствует'}</b>\n" \
                   f"🪪 ID: <code>{chat['id']}</code>\n" \
                   f"📃 Описание: <code>{chat['bio'] if chat['bio'] else 'Отсутствует'}</code>\n" \
                   f"👥 Участников: <code>{chat['members_count'] if chat['members_count'] else 'Данные отсутствуют'}</code>\n" \
                   f"🗯️ Отправлено реклам в чат: <code>{chat.get('sent_count', 0)}</code>\n"

        await c.message.edit_text(msg_text, reply_markup=Keyboards.Chats.menu(slot, chat))

    
    if actions[0] == "add_chat_from_ubot":
        suffix = "" if len(slot.ubots) > 0 else "\n\n⚠️ К слоту не привязаны юзерботы"
        await c.message.edit_text("💬 Выберите юзербота для выбора чатов рассылки" + suffix,
                                  reply_markup=Keyboards.SlotChats.chooseUserbotForSelectChats(slot))
        
    if actions[0] == "select_ubot_chats":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        ubot = UserbotSession.objects.get({"_id": actions[2]})
        client = userbotSessionToPyroClient(ubot)
        start = int(actions[-1])
        stateData = await state.get_data()
        suc = stateData.get("suc", {})
        if 'ubot_chats' not in stateData:
            await c.answer('ℹ️ Загружаю чаты... Это может занять время')
            try:
                await client.start()
                dialogs = client.get_dialogs()
                async for dialog in dialogs:
                    dialog: pyrogram.types.Dialog = dialog
                    chat: Chat = dialog.chat
                    chat_id = chat.id
                    if chat.type not in [pyrogram.enums.ChatType.GROUP, pyrogram.enums.ChatType.SUPERGROUP]:
                        continue
                    ubot.chats[str(chat_id)] = json.loads(json.dumps(chat.__dict__, ensure_ascii=False, default=str))
                ubot.save()
                await state.update_data(ubot_chats=ubot.chats)
            
            except AuthKeyUnregistered:
                await c.message.answer('ℹ️ Пожалуйста, переавторизируйте юзербота, не удаётся получить список чатов')
                return
            except AuthKeyDuplicated:
                await c.message.answer('ℹ️ Пожалуйста, переавторизируйте юзербота, не удаётся получить список чатов')
                return
            await state.update_data(suc={})
        else:
            await c.answer()
        await c.message.edit_text("💬 Выберите чаты для добавления", reply_markup=Keyboards.SlotChats.chooseChatsFromUbot(slot, ubot, suc, start))
        
        
    if actions[0] == "add_chats_with_text":
        await c.message.edit_text("💬 Введите все CHAT ID/JoinLink/Username чатов которые хотите включить в рассылку, разделяя их <b>\",\"</b>,<b>\";\"</b>,<b>\" \"</b> или переносом строки",
                                  reply_markup=Keyboards.back(f"|slot_menu:chats:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id)
        await ChangeSlotStates.chats.set()
        
    if actions[0] == "suc":
        await c.answer()
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        ubot = UserbotSession.objects.get({"_id": actions[2]})
        chat = ubot.chats[actions[3]]
        start = int(actions[-1])
        suc = (await state.get_data()).get('suc', {})
        if str(chat['id']) not in slot.chats:
            if str(chat['id']) not in suc:
                suc[str(chat['id'])] = chat
            else:
                del suc[str(chat['id'])]
        #slot.chats[chat['id']] = chat
        await state.update_data(suc=suc)
        await c.message.edit_text("💬 Выберите чаты для добавления", reply_markup=Keyboards.SlotChats.chooseChatsFromUbot(slot, ubot, suc, start))
        
    if actions[0] == "apply_suc":
        suc = (await state.get_data())['suc']
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        slot.chats.update(suc)
        slot.save()
        await c.message.edit_text("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.SlotChats.seeSlotChats(slot))

 
# Обработчик callback-запросов для работы с выбором юзерботов
@dp.callback_query_handler(text_contains="|choose_ubots", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    actions = c.data.split(":")     
    stateData = await state.get_data()
    ubots: list = stateData.get('ubots', [])
    
    if actions[1] == 'done':
        await c.answer()
            
        slot: AutopostSlot = AutopostSlot.objects.get({"_id": stateData['slot_id']})
        slot.ubots = ubots
        slot.save()
        
        await sendSlot(c.message, slot, True)
        await state.finish()
            
        await c.answer()
    else:
        ub_id = c.data.split(':')[1]
        slot: AutopostSlot = None
        if 'slot_id' in stateData:
            slot: AutopostSlot = AutopostSlot.objects.get({"_id": stateData['slot_id']})
        if ub_id in ubots:
            ubots.remove(ub_id)
        else:
            ubots.append(ub_id)
        await state.update_data(ubots=ubots)
        
        userbots = UserbotSession.objects.all()
        await c.message.edit_reply_markup(Keyboards.Slots.chooseUserbots(userbots, ubots, slot))
            
            
# Обработчик callback-запросов для работы с слотами
@dp.callback_query_handler(text_contains="|slot_menu", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    actions = c.data.split(":")[1:]

    if actions[0] == "delete_slot":
        await c.answer()
        slot: AutopostSlot = AutopostSlot.objects.get({'_id': actions[1]})
        if actions[-1] == "!":
            await c.message.answer(f"🗑️ Слот <b>{slot.name}</b> <code>#{slot.id}</code> удалён")
            slot.delete()
            await sendSlotsMenu(c.message)
            return
        await c.message.answer(f"Удлаить слот <b>{slot.name}</b>❔", reply_markup=Keyboards.Popup(f"|slot_menu:delete_slot:{slot.id}:!"))
        
    if actions[0] == "turn":
        slot: AutopostSlot = AutopostSlot.objects.get({'_id': actions[1]})
        if slot.status != 'banned':
            if slot.status == 'inactive' and len(slot.ubots) == 0:
                await c.answer("😢 Не подключено ни одного юзербота", show_alert=True)
                return
            if slot.status == 'inactive' and len(slot.postings) == 0:
                await c.answer("😢 Не установлено ни одного сообщения для рассылки", show_alert=True)
                return
            if slot.status == 'inactive' and len(slot.schedule) == 0:
                await c.answer("😢 Не установлено расписания для рассылки", show_alert=True)
                return
            slot.status = 'inactive' if slot.status == 'active' else 'active'
            slot.save()
            await sendSlot(c.message, slot, edit=True)
            await slot_updated(slot)
        else:
            await c.answer("😢 Невозможно включить слот", show_alert=True)
        
    if actions[0] == "schedule":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        xm = await c.message.edit_text("Введите расписание для рассылки в виде временных интервалов с разделением через <b>\";\"</b> или <b>\" \"</b>\n\nПример: <code>10:00-12:00;14:35-15:40;21:00-23:00</code>",
                                  reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id, xm=xm)
        await ChangeSlotStates.schedule.set()
        
    if actions[0] == "date_schedule":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        xm = await c.message.edit_text("Введите даты(от и до включительно) по которым будет осуществлятся рассылка с разделением через <b>\";\"</b> или <b>\" \"</b>\n\nПример: <code>10.06.2023-20.06.2023 22.06.2023-30.06.2023</code>",
                                  reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id, xm=xm)
        await ChangeSlotStates.date_schedule.set()
        
    if actions[0] == "chats":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        start = int(actions[-1]) if actions[-1].isdigit() else 0
        if start < 0:
            await c.answer('Вы уже в начале списка')
            return
        if start > len(slot.chats):
            await c.answer('Вы уже в конце списка')
            return
        if state:
            await state.finish()
        await c.message.edit_text("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.SlotChats.seeSlotChats(slot, start))
        
    if actions[0] == "postings":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        if actions[-1] == "main":
            await c.message.edit_text("💌 Меню сообщений для рассылки", reply_markup=Keyboards.Slots.postingsMenu(slot))
        if actions[-1] == "add_messages":
            xm = await c.message.edit_text(f"💌 Введите сообщения для добавления, разделяя их с помощью <b>\"#####\"</b>\n"
                                      f"Максимально сообщений: <code>{Consts.MAX_POSTINGS_IN_SLOT}</code>\n\n"
                                      f"Пример:\n"
                                      f"<i>Привет, это первое сообщение для рассылки!\n"
                                      f"#####\n"
                                      f"Привет, это второе сообщение для рассылки!\n"
                                      f"#####\n"
                                      f"Привет, это третье сообщение для рассылки!\n</i>", reply_markup=Keyboards.Slots.addPostings(slot))
            await state.update_data(editing_slot_id=slot.id, xm=xm)
            await ChangeSlotStates.postings.set()
        if actions[-1] == "see_message":
            message_id = actions[-2]
            posting = [x for x in slot.postings if x.id == message_id][0]
            await c.message.answer(f"ID: <code>{posting.id}</code>\nНазвание: <code>{posting.name if posting.name else 'Нет'}</code>\n\nТекст: {posting.text}", reply_markup=Keyboards.hide())
        if actions[-1] == "del_message":
            message_id = actions[-2]
            slot.postings = [x for x in slot.postings if x.id != message_id]
            slot.save()
            await c.message.edit_text("💌 Меню сообщений для рассылки", reply_markup=Keyboards.Slots.postingsMenu(slot))
        if actions[-1] == "preview_messages":
            await c.answer("💌 Выводятся все сообщения...")
            for posting in slot.postings:
                await c.message.answer(posting.text, reply_markup=Keyboards.hide())
                await asyncio.sleep(0.1)
            
        
    if actions[0] == "ubots":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        all_userbots = UserbotSession.objects.all()
        ubots = [x.id for x in slot.ubots]
        await c.message.edit_text("🤖 Выберите юзерботов которые будут работать в этом слоте",
                                  reply_markup=Keyboards.Slots.chooseUserbots(all_userbots, ubots, slot))
        await state.update_data(slot_id=slot.id, ubots=ubots)
                
    if actions[0] == "change":
        slot = AutopostSlot.objects.get({"_id": actions[2]})
        if actions[1] == "name":
            await c.answer()
            xm = await c.message.edit_text(f"✏️ Введите новое название слота:", reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
            await state.update_data(editing_slot_id=slot.id, xm=xm)
            await ChangeSlotStates.name.set()
        if actions[1] == "logs":
            await c.answer()
            xm = await c.message.edit_text(f"✏️ Введите CHAT ID чата для выводи ошибок:", reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
            await state.update_data(editing_slot_id=slot.id, xm=xm)
            await ChangeSlotStates.logsChat.set()
            
            
# Обработчик callback-запросов для работы с слотами
@dp.callback_query_handler(text_contains="|slots", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    action = c.data.split(":")[1]

    if action == "main":
        if state:
            await state.finish()
        await sendSlotsMenu(c.message, edit=True)

    if action == "new":
        await c.answer()
        slot = AutopostSlot(id=str(uuid4())[:15],
                            owner_id=user.user_id,
                            name=f"{fake.word().capitalize()}_{fake.word()}",
                            emoji=random.choice(
                                ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪", "🟠"])
                            )
        slot.save()

        slots: AutopostSlot = AutopostSlot.objects.all()
        await c.message.edit_text("🗃️ Меню слотов", reply_markup=Keyboards.Slots.main(slots))

    if action == "see":
        if state:
            await state.finish()
        slot: AutopostSlot = AutopostSlot.objects.get(
            {'_id': c.data.split(':')[2]})
        await sendSlot(c.message, slot, True)


@dp.message_handler(state=ChangeSlotStates.name)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    slot.name = val
    slot.save()

    await stateData['xm'].edit_text(f"✅ Значение имени изменено на <code>{message.text}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()


@dp.message_handler(state=ChangeSlotStates.logsChat)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    
    
    if not val.replace('-', '').isdigit():
        await message.answer("❗ Некорректное значение")
        return
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    slot.reports_group_id = int(val)
    slot.save()

    await stateData['xm'].edit_text(f"✅ CHAT ID установлен на <code>{message.text}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()



@dp.message_handler(state=ChangeSlotStates.postings)
async def _(message: types.Message, state: FSMContext):
    val = message.html_text
    stateData = await state.get_data()
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    
    if not check_html_tags(val):
        await message.answer("❗ Внимание! Нарушены теги в тексте. Ни одно сообщение не было добавлено", reply_markup=Keyboards.back(f"|slot_menu:postings:{slot.id}:main"))
        return
    last_id = int(slot.postings[-1].id) if slot.postings else -1
    messages_for_adding = [dict(id=str(i + last_id + 1), 
                                name=msg_text.split("%%%")[0].strip() if "%%%" in msg_text else cutText(remove_html_tags(msg_text), 10).strip(), 
                                text=msg_text.split("%%%")[-1].strip(), sent_count=0) for i, msg_text in enumerate(val.split('#####'))]
    slot.postings = slot.postings + messages_for_adding
    slot.postings = slot.postings[:Consts.MAX_POSTINGS_IN_SLOT]
    slot.save()

    await message.answer("✅ Сообщения добавлены!")
    await message.answer("💌 Меню сообщений для рассылки", reply_markup=Keyboards.Slots.postingsMenu(slot))
    await state.finish()
    await stateData['xm'].delete()
    await slot_updated(slot)



@dp.message_handler(state=ChangeSlotStates.schedule)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    
    schedule = [dict(min=x.split('-')[0], max=x.split('-')[1]) for x in val.replace(';', ' ').replace('  ', ' ').strip().split()]
    for x in schedule:
        if 0 <= int(x['min'].split(':')[0]) <= 24 and 0 <= int(x['max'].split(':')[0]) <= 24 and 0 <= int(x['min'].split(':')[1]) <= 60 and 0 <= int(x['max'].split(':')[1]) <= 60:
            pass
        else:
            await message.answer(f"❌ Недопустимое время в интервале: <code>{x['min']}-{x['max']}</code>. Введите интервалы заново")
            return
    
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    
    slot.schedule = schedule
    slot.save()

    await stateData['xm'].edit_text(f"✅ Расписание изменено на <code>{val}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()
    asyncio.create_task(slot_updated(slot))


@dp.message_handler(state=ChangeSlotStates.date_schedule)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    
    try:
        schedule = [dict(min=datetime.datetime.strptime(x.split('-')[0], "%d.%m.%Y"), 
                        max=datetime.datetime.strptime(x.split('-')[1], "%d.%m.%Y")) for x in val.replace(';', ' ').replace('  ', ' ').strip().split()]
    except Exception as e:
        loguru.logger.error(f"Error on formating date: {e}")
        await message.answer(f"❌ Недопустимая дата. Введите заново")
        return
    
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw({"_id": stateData['editing_slot_id']}).first()
    
    slot.date_schedule = schedule
    slot.save()

    await stateData['xm'].edit_text(f"✅ Расписание дат изменено на <code>{val}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()
    asyncio.create_task(slot_updated(slot))


