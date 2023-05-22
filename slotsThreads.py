

import asyncio
import datetime
from functools import partial
import random
import threading
import time
import traceback
from typing import List

from loguru import logger
import schedule
from etc.utils import sendMessageFromBotSync, userbotSessionToPyroClient
from models import AutopostSlot, UserbotSession
import pyrogram
from loader import slots_jobs, threads


async def slot_updated(slot: AutopostSlot):
    global slots_jobs
    global threads
    for job_key in slots_jobs:
        if slot.id in job_key:
            job: schedule.Job = slots_jobs[job_key]
            schedule.cancel_job(job)
    start_slots_jobs(slot)            
            
            
def send_interval(slot, chat_id, ubot, interval):
    t = threading.Thread(target=lambda: asyncio.run(send_interval_message(slot, chat_id, ubot, interval)), name="Send interval message")
    t.start()


async def send_interval_message(slot: AutopostSlot, chat_id, ubot: UserbotSession, interval: dict):
    client = userbotSessionToPyroClient(ubot)
    cmin = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['min'].split(':')[0]), int(interval['min'].split(':')[1]), 0)
    cmax = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['max'].split(':')[0]), int(interval['max'].split(':')[1]), 59)
    w8 = random.randint(0, (cmax - datetime.datetime.now()).seconds)
        
    await asyncio.sleep(w8)
    try:
        async with client as c:
            await c.send_message(int(chat_id), random.choice(slot.postings).text)
            print('Message sent')
    except Exception as e:
        sendMessageFromBotSync(slot.reports_group_id, f"⚠️ Юзербот <b>{ubot.name}</b> в слоте <code>{slot.name}</code> не смог отправить сообщение в интервал <code>{interval['min']}-{interval['max']}</code>!\n\nОшибка: <b>{e} ➖ {traceback.format_exc()}</b>")
            
            
def start_slots_jobs(slot: AutopostSlot):
    global slots_jobs
    for interval in slot.schedule:
        for chat_id, chat in slot.chats.items():
            job_id = f"{slot.id}_{chat_id}_{interval}"
            ubot = random.choice(slot.ubots)
            job = schedule.every().day.at(interval['min']).do(send_interval, slot, chat_id, ubot, interval)
            slots_jobs[job_id] = job


def start_interval_scheduler(slots: List[AutopostSlot]):
    global slots_jobs
    for slot in slots:
        if slot.status == 'active':
            start_slots_jobs(slot)
                    
    # Бесконечный цикл для выполнения расписания
    while True:
        schedule.run_pending()
        time.sleep(1)
        print("Alljobs")
        print([(x.next_run) for x in schedule.get_jobs()])