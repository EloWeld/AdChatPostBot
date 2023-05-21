
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
from states import ChangeSlotStates


# Функция для отправки информации о слоте
async def sendSlot(msg: Message, slot: AutopostSlot, edit=False):
    func = msg.answer if not edit else msg.edit_text

    schdeule_text = "❌ Не установлено" if len(slot.schedule) == 0 else '\n'.join(f"<code>{x['min']}-{x['max']}</code>" for x in slot.schedule)
    postings_text = "❌ Не установлено" if len(slot.postings) == 0 else '\n'.join(f"Сообщение #{i}: отправлено <code>{x.sent_count}</code> раз" for i, x in enumerate(slot.postings))

    await func(f"{slot.emoji} Слот <b>{slot.name}</b> <code>#{slot.id}</code>\n\n"
               f"<b>📝 Информация:</b>\n"
               f"▫️ Юзерботов подключено: <code>{len(slot.ubots)}</code> шт.\n"
               f"▫️ Чатов добавлено: <code>{len(slot.chats)}</code> шт.\n"
               f"▫️ Сообщений для рассылки: <code>{len(slot.postings)}</code> шт.\n"
               f"▫️ Статус работы: <code>{slot.get_verbose_status()}</code>\n\n"
               f"<b>📆 Расписание:</b>\n"
               f"{schdeule_text}\n\n"
               f"<b>💌 Контент рассылки:</b>\n"
               f"{postings_text}\n\n", 
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
        chat = slot.chats[str(chat_id)]
        photopath = f"chat_photos/{chat_id}.jpg"
        contains_photo = True

        if not os.path.exists(photopath):
            client: pyrogram.Client = threads[slot.ubots[0].id]['client']
            async with client:
                contains_photo = await download_chat_photo(client, chat_id, photopath)

        msg_text = f"💬 Чат <b>{chat['title']}</b>\n" \
                   f"🔗 Ссылка: <b>{'@'+chat['username'] if chat['username'] else 'Отсутствует'}</b>\n" \
                   f"🪪 ID: <code>{chat['id']}</code>\n" \
                   f"📃 Описание: <code>{chat['bio'] if chat['bio'] else 'Отсутствует'}</code>\n" \
                   f"👥 Участников: <code>{chat['members_count']}</code>\n" \
                   f"🗯️ Отправлено реклам в чат: <code>{chat.get('sent_count', 0)}</code>\n"

        if contains_photo:
            await c.message.answer_photo(InputFile(photopath), caption=msg_text,
                                         reply_markup=Keyboards.hide())
        else:
            await c.message.answer(msg_text, reply_markup=Keyboards.hide())

    
    if actions[0] == "add_chat_from_ubot":
        suffix = "" if len(slot.ubots) > 0 else "\n\n⚠️ К слоту не привязаны юзерботы"
        await c.message.edit_text("💬 Выберите юзербота для выбора чатов рассылки" + suffix,
                                  reply_markup=Keyboards.SlotChats.chooseUserbotForSelectChats(slot))
        
    if actions[0] == "select_ubot_chats":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        ubot = UserbotSession.objects.get({"_id": actions[2]})
        await c.message.edit_text("💬 Выберите чаты для добавления", reply_markup=Keyboards.SlotChats.chooseChatsFromUbot(slot, ubot, {}))
        await state.update_data(suc={})
        
    if actions[0] == "add_chats_with_text":
        await c.message.edit_text("💬 Введите все CHAT ID чатов которые хотите включить в рассылку, разделяя их <b>\",\"</b>,<b>\";\"</b>,<b>\" \"</b> или переносом строки",
                                  reply_markup=Keyboards.back(f"|slot_menu:chats:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id)
        await ChangeSlotStates.posting_chats.set()
        
    if actions[0] == "suc":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        ubot = UserbotSession.objects.get({"_id": actions[2]})
        chat = ubot.chats[actions[3]]
        suc = (await state.get_data()).get('suc', {})
        if str(chat['id']) not in suc:
            suc[str(chat['id'])] = chat
        else:
            del suc[chat['id']]
        #slot.chats[chat['id']] = chat
        await state.update_data(suc=suc)
        await c.message.edit_text("💬 Выберите чаты для добавления", reply_markup=Keyboards.SlotChats.chooseChatsFromUbot(slot, ubot, suc))
        
    if actions[0] == "apply_suc":
        suc = (await state.get_data())['suc']
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        slot.chats.update(suc)
        slot.save()
        await c.message.edit_text("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.Slots.seeSlotChats(slot))

 
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
        ub_id = c.data.split(':')[2]
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
        slot: AutopostSlot = AutopostSlot.objects.get({'_id': actions[2]})
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
        
    if actions[0] == "schedule":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        xm = await c.message.edit_text("Введите расписание для рассылки в виде временных интервалов с разделением через <b>\";\"</b> или <b>\" \"</b>\n\nПример: <code>10:00-12:00;14:35-15:40;21:00-23:00</code>",
                                  reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id, xm=xm)
        await ChangeSlotStates.schedule.set()
        
    if actions[0] == "chats":
        if state:
            await state.finish()
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        await c.message.edit_text("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.SlotChats.seeSlotChats(slot))
        
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
            slot.postings = [x for x in slot.postings if x.id != message_id]
            slot.save()
            await c.message.answer([x for x in slot.postings if x.id == message_id][0].text, Keyboards.hide())
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
        await c.message.edit_text("🤖 Выберите юзерботов которые будут работать в этом слоте",
                                  reply_markup=Keyboards.Slots.chooseUserbots(all_userbots, slot.ubots, slot))
        await state.update_data(slot_id=slot.id, ubots=slot.ubots)
        await ChangeSlotStates.schedule.set()
                
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
                            owner_id=user.id,
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
    messages_for_adding = [dict(id=str(i + last_id + 1), text=msg_text, sent_count=0) for i, msg_text in enumerate(val.split('#####'))]
    slot.postings = slot.postings + messages_for_adding
    slot.postings = slot.postings[:Consts.MAX_POSTINGS_IN_SLOT]
    slot.save()

    await message.answer("✅ Сообщения добавлены!")
    await message.answer("💌 Меню сообщений для рассылки", reply_markup=Keyboards.Slots.postingsMenu(slot))
    await state.finish()
    await stateData['xm'].delete()



@dp.message_handler(state=ChangeSlotStates.schedule)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    
    slot.schedule = [dict(min=x.split('-')[0], max=x.split('-')[1]) for x in val.replace(';', ' ').replace('  ', ' ').strip().split()]
    slot.save()

    await stateData['xm'].edit_text(f"✅ Расписание изменено на <code>{val}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()



@dp.message_handler(state=ChangeSlotStates.posting_chats)
async def _(message: types.Message, state: FSMContext):
    global threads
    chat_ids = message.text.replace('\n', ' ').replace(';', ' ').replace(',', ' ').replace('  ', ' ').split()
    stateData = await state.get_data()
    
    slot: AutopostSlot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    counter = 0
    for chat_id in chat_ids:
        if chat_id in slot.chats:
            await message.answer(f"⚠️ Чат <code>{chat_id}</code> был уже добавлен в список чатов" )
            continue
        for ubot in slot.ubots:
            ubot: UserbotSession = ubot
            client: pyrogram.Client = threads[ubot.id]['client']
            chat = await client.get_chat(chat_id)
            if chat is None:
                await message.answer(f"⚠️ Чат <code>{chat_id}</code> не добавлен у юзербота <code>{ubot.name}</code> | <code>{ubot.login}</code>, чат не добавлен")
                continue
            if chat is None:
                await message.answer(f"⚠️ В чате <code>{chat_id}</code> юзербот <code>{ubot.name}</code> | <code>{ubot.login}</code> не может писать сообщения, чат не добавлен")
                continue
            slot.chats[str(chat.id)] = json.loads(json.dumps(chat.__dict__, ensure_ascii=False, default=str))
            counter += 1
    await message.answer(f"✅ Добавлено {counter} чатов!")
    slot.save()
            
    await message.answer("💬 Меню подключённых чатов для рассылки",
                                  reply_markup=Keyboards.Slots.seeSlotChats(slot))
    await state.finish()
