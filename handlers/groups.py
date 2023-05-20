
import asyncio
import traceback
from aiogram import Bot, Dispatcher, types
import aiogram
import loguru
from etc.keyboards import Keyboards
from loader import *
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.types import *
from models import TgGroup, TgUser, UserbotSession
from states import AddGroupState, ChangeGroupStates


# Функция для отправки информации о группе
async def sendGroup(msg: Message, group: TgGroup, edit=False):
    func = msg.answer if not edit else msg.edit_text
    ubs_logins = [x.login for x in UserbotSession.objects.all() if x.id in group.ubs]
    try:
        invite = await bot.create_chat_invite_link(group.chat_id)
    except aiogram.utils.exceptions.MigrateToChat as e:
        group.chat_id = e.migrate_to_chat_id
        group.title = group.title + " (Migrated)"
        group.save()
        invite = await bot.create_chat_invite_link(group.chat_id)
        
    await func(f"Группа-фильтр <a href='{invite.invite_link}'>{group.title}</a>\n"
                f"Ключ-слова: <code>{'</code>; <code>'.join(group.keywords)}</code>\n"
                f"Минус-слова: <code>{'</code>; <code>'.join(group.bad_keywords) if group.bad_keywords else '➖'}</code>\n"
                f"Блэк-лист отправители: <code>{'</code>; <code>'.join(group.blacklist_users) if group.blacklist_users else '➖'}</code>\n\n"
                f"Подключённые юзерботы: <code>{'</code>; <code>'.join(ubs_logins)}</code>\n\n", disable_web_page_preview=True,
                reply_markup=Keyboards.Groups.editGroup(group))


# Обработчик callback-запросов для работы с группами
@dp.callback_query_handler(text_contains="|groups", state="*")
async def _(c: CallbackQuery, state: FSMContext, user: TgUser):
    action = c.data.split(":")[1]
    
    if action == "main":
        groups: TgGroup = TgGroup.objects.all()
        await c.message.edit_text("Выберите группу или добавьте новую", reply_markup=Keyboards.Groups.main(groups))

    if action == "new":
        await c.answer()
        await c.message.answer("✏️ Введите имя группы:\n\n<i>Пример: OnlyCars</i>")
        await AddGroupState.name.set()

    if action == "see":
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        await sendGroup(c.message, group, True)

    # Добавление значения в список
    if action == "add":
        await c.answer()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        key = c.data.split(':')[3]
        await c.message.answer(f"✏️ Введите значение которое хотите добавить в список <b>{key}</b>")
        await state.update_data(editing_group_id=group.chat_id, editing_key=key)
        await ChangeGroupStates.Add.set()
    # Изменение значения
    if action == "change":
        await c.answer()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        key = c.data.split(':')[3]
        await c.message.answer(f"✏️ Введите новое значение <b>{key}</b>. Учтите что предыдущее значение перезапишется!")
        await state.update_data(editing_group_id=group.chat_id, editing_key=key)
        await ChangeGroupStates.Change.set()
    # Предупреждение об очистке списка
    if action == "clear_popup":
        await c.answer()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        key = c.data.split(':')[3]
        await c.message.answer(f"Очистить список <b>{key}</b>❔", reply_markup=Keyboards.Popup(f"|groups:clear:{group.chat_id}:{key}"))
        await state.update_data(editing_group_id=group.chat_id, editing_key=key)
        await ChangeGroupStates.Clear.set()
    # Очистка списка
    if action == "clear":
        await c.answer()
        await c.message.delete()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        
        key = c.data.split(':')[3]
        setattr(group, key, [])
        group.save()
        
        await sendGroup(c.message, group)
        await state.finish()
    # Изменить юзерботов
    if action == "change_ubots":
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        all_userbots = UserbotSession.objects.all()
        await c.message.edit_text("Выберите юзерботов чаты из которых будут фильтроваться", 
                                  reply_markup=Keyboards.Groups.chooseUserbots(all_userbots, group.ubs, group))
        await state.update_data(chat_id=group.chat_id, ubs=group.ubs)
        await ChangeGroupStates.ubs.set()
        
    if action == "delete_group_popup":
        await c.answer()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        await c.message.answer(f"Удлаить группу <b>{group.title}</b>❔", reply_markup=Keyboards.Popup(f"|groups:delete_group:{group.chat_id}"))
    if action == "delete_group":
        await c.answer()
        group: TgGroup = TgGroup.objects.get({'_id': int(c.data.split(':')[2])})
        await c.message.answer(f"🗑️ Группа <b>{group.title}</b> удалена")
        group.delete()
        
    

# Обработка ввода имени группы
@dp.message_handler(state=AddGroupState.name)
async def handle_group_name_input(message: types.Message, state: FSMContext):
    val = message.text
    await state.update_data(name=val)
    await message.answer("✏️ Введите CHAT ID группы в которую будут приходить отфильтрованные сообщения:\n\n<i>Пример: -1001477582245</i>")
    await AddGroupState.chatID.set()  

# Обработка ввода CHAT ID группы
@dp.message_handler(state=AddGroupState.chatID)
async def _(message: types.Message, state: FSMContext):
    val = message.text[:25]
    try:
        await state.update_data(chatID=int(val))
    except Exception as e:
        await message.answer("⚠️ Некорректный chatID, введите ещё раз:")
        loguru.logger.error(f"Error adding group: {e}, {traceback.format_exc()}")
        return
    await message.answer("✏️ Слова или словосочетания по котороым юзербот будет сравнивать сообщения разделяя переносом строк:\n\n<i>Пример: Машина\nсмета\nкуплю</i>")
    await AddGroupState.keywords.set()

# Обработка ввода ключевых слов
@dp.message_handler(state=AddGroupState.keywords)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    try:
        await state.update_data(keywords=[x.lower() for x in val.replace(';', '\n').split('\n')])
    except Exception as e:
        await message.answer("⚠️ Некорректный ввод, введите ещё раз:")
        loguru.logger.error(f"Error adding group: {e}, {traceback.format_exc()}")
        return
    await message.answer("✏️ Слова или словосочетания встретив которые юзербот не будет учитывать сообщения:\n\n0 - для пропуска\n\n<i>Пример: Бракованная\nбез торга\nдля детей</i>")
    await AddGroupState.bad_keywords.set()
    
# Обработка ввода минус-слов
@dp.message_handler(state=AddGroupState.bad_keywords)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    try:
        if val == "0":
            await state.update_data(bad_keywords=[])
        else:
            await state.update_data(bad_keywords=[x.lower() for x in val.replace(';', '\n').split('\n')])
    except Exception as e:
        await message.answer("⚠️ Некорректный ввод, введите ещё раз:")
        loguru.logger.error(f"Error adding group: {e}, {traceback.format_exc()}")
        return
    await message.answer("✏️ ID или username'ы пользователей от которых сообщения пересылаться не будут:\n\n0 - для пропуска\n\n<i>Пример: 2114499242\nHacker213\n609517172</i>")
    await AddGroupState.blacklist.set()

# Обработка ввода черного списка пользователей
@dp.message_handler(state=AddGroupState.blacklist)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    try:
        if val == "0":
            await state.update_data(blacklist=[])
        else:
            await state.update_data(blacklist=[x.lower() for x in val.replace(';', '\n').split('\n')])
    except Exception as e:
        await message.answer("⚠️ Некорректный ввод, введите ещё раз:")
        loguru.logger.error(f"Error adding group: {e}, {traceback.format_exc()}")
        return
    
    userbots = UserbotSession.objects.all()
    
    await message.answer("✏️ Выберите юзерботов которые будут смотреть за сообщениями", reply_markup=Keyboards.Groups.chooseUserbots(userbots))
    await AddGroupState.ubs.set()


# Обработка выбора юзерботов
@dp.callback_query_handler(text_contains="|choose_ubots", state=[AddGroupState.ubs, ChangeGroupStates.ubs])
async def _(c: CallbackQuery, state: FSMContext):
    action = c.data.split(':')[1]
    stateData = await state.get_data()
    ubs: list = stateData.get('ubs', [])
    
    if action == "choose":
        ub_id = c.data.split(':')[2]
        group = None
        print(await state.get_state(), ChangeGroupStates.ubs.state)
        if 'chat_id' in stateData and await state.get_state() == ChangeGroupStates.ubs.state:
            group = TgGroup.objects.get({"_id": stateData['chat_id']})
        if ub_id in ubs:
            ubs.remove(ub_id)
        else:
            ubs.append(ub_id)
        
        await state.update_data(ubs=ubs)
        
        userbots = UserbotSession.objects.all()
        await c.message.edit_reply_markup(Keyboards.Groups.chooseUserbots(userbots, ubs, group))
    if action == "done" and await state.get_state() == AddGroupState.ubs.state:
        await c.answer()
        await c.message.answer("✅ Группа добавлена")
        
        group = TgGroup(stateData['chatID'], 
        title=stateData['name'], 
        owner_id=c.from_user.id, 
        keywords=stateData['keywords'], 
        bad_keywords=stateData['bad_keywords'], 
        blacklist_users=stateData['blacklist'],
        forwarded_msgs=[],
        ubs=ubs).save()
        
        await sendGroup(c.message, group)
        await c.message.delete()
        await state.finish()
    
    if action == "done" and await state.get_state() == ChangeGroupStates.ubs.state:
        await c.answer()
        
        group: TgGroup = TgGroup.objects.get({"_id": stateData['chat_id']})
        group.ubs = ubs
        group.save()
        
        await sendGroup(c.message, group, True)
        await state.finish()
        
# Изменение значений группы (добавление, изменение, очистка итд)
@dp.message_handler(state=ChangeGroupStates.Add)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    group = TgGroup.objects.get({"_id": stateData['editing_group_id']})
    editing_key = stateData['editing_key']
    
    current_values = getattr(group, editing_key)
    new_values = current_values + [val.lower()]
    setattr(group, editing_key, new_values)
    
    group.save()
          
    await sendGroup(message, group)
    await state.finish()

@dp.message_handler(state=ChangeGroupStates.Change)
async def _(message: types.Message, state: FSMContext):
    val = message.text
    stateData = await state.get_data()
    group = TgGroup.objects.raw({"_id": stateData['editing_group_id']}).first()
    editing_key = stateData['editing_key']
    if editing_key  in ['keywords', 'bad_keywords', 'blacklist_users']:
        setattr(group, editing_key, [x.lower() for x in val.replace(';', '\n').split('\n')] if val != "0" else [])
    else:
        setattr(group, editing_key, val)
        
    group.save()
          
    await sendGroup(message, group)
    await state.finish()
