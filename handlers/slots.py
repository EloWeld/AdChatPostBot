
import asyncio
import random
import traceback
from uuid import uuid4
from aiogram import Bot, Dispatcher, types
import aiogram
import loguru
from etc.keyboards import Keyboards
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
    postings_text = "❌ Не установлено" if len(slot.postings) == 0 else '\n'.join(f"Сообщение #{i}: отправлено <code>{x['sent_count']}</code> раз" for i, x in enumerate(slot.postings))

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
                
    if actions[0] == "change":
        slot = AutopostSlot.objects.get({"_id": actions[2]})
        if actions[1] == "name":
            await c.answer()
            xm = await c.message.edit_text(f"✏️ Введите новое название слота:", reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
            await state.update_data(editing_slot_id=slot.id, xm=xm)
            await ChangeSlotStates.name.set()
        
    if actions[0] == "schedule":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        xm = await c.message.edit_text("Введите расписание для рассылки в виде временных интервалов с разделением через <b>\";\"</b> или <b>\" \"</b>\n\nПример: <code>10:00-12:00;14:35-15:40;21:00-23:00</code>",
                                  reply_markup=Keyboards.back(f"|slots:see:{slot.id}"))
        await state.update_data(editing_slot_id=slot.id, xm=xm)
        await ChangeSlotStates.schedule.set()
        
        
    if actions[0] == "postings":
        await c.answer("Разработка")
        
    if actions[0] == "ubots":
        slot = AutopostSlot.objects.get({"_id": actions[1]})
        all_userbots = UserbotSession.objects.all()
        await c.message.edit_text("🤖 Выберите юзерботов которые будут работать в этом слоте",
                                  reply_markup=Keyboards.Slots.chooseUserbots(all_userbots, slot.ubots, slot))
        await state.update_data(slot_id=slot.id, ubots=slot.ubots)
        await ChangeSlotStates.schedule.set()
        
    ####################
    if actions[0] == "choose_ubots":
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
    
    slot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    setattr(slot, 'name', val)
    slot.save()

    await stateData['xm'].edit_text(f"✅ Значение имени изменено на <code>{message.text}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()



@dp.message_handler(state=ChangeSlotStates.schedule)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    
    slot = AutopostSlot.objects.raw(
        {"_id": stateData['editing_slot_id']}).first()
    
    slot.schedule = [dict(min=x.split('-')[0], max=x.split('-')[1]) for x in val.replace(';', ' ').replace('  ', ' ').strip().split()]
    slot.save()

    await stateData['xm'].edit_text(f"✅ Расписание изменено на <code>{val}</code>!")
    await message.delete()

    await sendSlot(message, slot)
    await state.finish()
