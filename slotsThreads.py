import asyncio
import datetime
from functools import partial
import random
import threading
import time
import traceback
from typing import List

from loguru import logger
from etc.utils import sendMessageFromBotSync, userbotSessionToPyroClient
from models import AutopostSlot, UserbotSession
import pyrogram
import aiocron
from loader import slots_jobs


async def slot_updated(slot: AutopostSlot):
    global slots_jobs
    global threads
    for job_key in slots_jobs:
        if slot.id in job_key:
            job: aiocron.Cron = slots_jobs[job_key]
            job.stop()
    await start_slots_jobs(slot)            
            
            
def send_interval(slot, chat_id, ubot, interval):
    t = threading.Thread(target=lambda: asyncio.run(send_interval_message(slot, chat_id, ubot, interval)), name="Send interval message")
    t.start()


async def send_interval_message(slot: AutopostSlot, chat_id, ubot: UserbotSession, interval: dict):
    client = userbotSessionToPyroClient(ubot)
    cmin = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['min'].split(':')[0]), int(interval['min'].split(':')[1]), 0)
    cmax = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['max'].split(':')[0]), int(interval['max'].split(':')[1]), 59)
    w8 = random.randint(0, (cmax - datetime.datetime.now()).seconds)
    posting = random.choice(slot.postings)
    await asyncio.sleep(w8)
    try:
        async with client as c:
            await c.send_message(int(chat_id), posting.text)
            print('Message sent')
            slot = AutopostSlot.objects.get({"_id": slot.id})
            if 'sent_count' not in slot.chats[chat_id]:
                slot.chats[chat_id]['sent_count'] = 0
            slot.chats[chat_id]['sent_count'] += 1
            for x in slot.postings:
                if x.id == posting.id:
                    x.sent_count += 1
            slot.save()
            
    except Exception as e:
        sendMessageFromBotSync(slot.reports_group_id, f"⚠️ Юзербот <b>{ubot.name}</b> в слоте <code>{slot.name}</code>, группа {slot.chats[chat_id]['title']} ({chat_id}). Не смог отправить сообщение в интервал <code>{interval['min']}-{interval['max']}</code>!\n\nОшибка: <b>{e}</b>") #  ➖ {traceback.format_exc()}
            
            
async def start_slots_jobs(slot: AutopostSlot):
    global slots_jobs
    for interval in slot.schedule:
        for chat_id, chat in slot.chats.items():
            job_id = f"{slot.id}_{chat_id}_{interval}"
            ubot = random.choice(slot.ubots)
            cron_expression = f"{interval['min'].split(':')[1]} {interval['min'].split(':')[0]} * * *"
            job = aiocron.crontab(cron_expression, func=partial(send_interval, slot, chat_id, ubot, interval), start=True)
            slots_jobs[job_id] = job


def start_interval_scheduler(slots: List[AutopostSlot]):
    global slots_jobs
    for slot in slots:
        if slot.status == 'active':
            asyncio.run(start_slots_jobs(slot))