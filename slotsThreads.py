

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
from models import AutopostSlot
import pyrogram
from loader import slots_jobs, threads

async def d(slot: AutopostSlot, chat_id, interval, stop_event: threading.Event(), ubot):
    client = userbotSessionToPyroClient(ubot)
    while not stop_event.is_set():
        cmin = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['min'].split(':')[0]), int(interval['min'].split(':')[1]), 0)
        cmax = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().day, int(interval['max'].split(':')[0]), int(interval['max'].split(':')[1]), 59)
        if cmin > datetime.datetime.now():
            need8time = (cmin - datetime.datetime.now()).seconds
            print(f"Wait for interval start - {need8time}")
            time.sleep(need8time)
        
        if cmax > datetime.datetime.now():
            w8time = random.randint(0, (cmax - datetime.datetime.now()).seconds)
            print(f"In interval, w8time - {w8time}")
            time.sleep(w8time)
        else:
            # w8time = int((cmin - datetime.datetime.now()).seconds * 0.9)
            # print(f"Skipping interval, wait for {w8time}")
            time.sleep(60)
            w8time = int((cmin - datetime.datetime.now()).seconds * 0.9)
            continue
        try:
            async with client as c:
                await c.send_message(int(chat_id), random.choice(slot.postings).text)
                print('Message sent')
                w8time = int((cmin - datetime.datetime.now()).seconds * 0.9)
                time.sleep(w8time)
        except Exception as e:
            sendMessageFromBotSync(slot.reports_group_id, f"⚠️ Юзербот <b>{ubot.name}</b> в слоте <code>{slot.name}</code> не смог отправить сообщение в интервал <code>{interval['min']}-{interval['max']}</code>!\n\nОшибка: <b>{e} ➖ {traceback.format_exc()}</b>")
        time.sleep(60)

def send_slot_message(slot, chat_id, interval, stop_event, ubot):
    asyncio.run(d(slot, chat_id, interval, stop_event, ubot))


async def slot_updated(slot: AutopostSlot):
    global slots_jobs
    global threads
    for job_key in slots_jobs:
        if slot.id in job_key:
            slots_jobs[job_key]['stop_event'].set()
            
    for interval in slot.schedule:
        for chat_id in slot.chats:
            ubot = random.choice(slot.ubots)
            ubot_id = ubot.id
            stop_event = threading.Event()
            job_id = f"{slot.id}_{interval['min']}_{interval['max']}_{chat_id}_{ubot_id}"
            t = threading.Thread(target=send_slot_message, args=(slot, chat_id, interval, stop_event, ubot), name=f"Slot #{slot.name} {interval['min']}-{interval['max']} {chat_id}")
            slots_jobs[job_id] = dict(thread=t, stop_event=stop_event)
            t.start()