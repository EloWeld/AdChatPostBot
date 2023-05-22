import asyncio
from functools import partial
import threading
from typing import List
import aiocron
from loguru import logger
from loader import dp, threads, bot, MDB, slots_jobs
from handlers import *
from pyroThreads import start_pyro_client
from slotsThreads import send_slot_message


async def on_start_bot():
    from etc.utils import notify_admins
    bot_info = await bot.get_me()
    MDB.Settings.update_one(dict(id="Constants"), {"$set": dict(BotUsername=bot_info.username)})
    logger.info(f"Bot started! https://t.me/{Consts.BotUsername}")
    await notify_admins(f"🤖 Запущен!")

async def main_async():
    global threads
    global slots_jobs
    all_sessions: List[UserbotSession] = UserbotSession.objects.all()
    all_slots: List[AutopostSlot] = AutopostSlot.objects.all()
    threads.clear()

    logger.info("Starting userbots threads...")
    for usession in all_sessions:
        try:
            stop_event = threading.Event()
            t = threading.Thread(target=start_pyro_client, args=(stop_event, usession), name=f"Usebot #{usession.name}")
            t.start()
            threads[usession.id] = dict(thread=t, stop_event=stop_event)
        except Exception as e:
            loguru.logger.error(f"Can't start userbot session {usession.name}. Error: {e}, traceback: {traceback.format_exc()}")
            
    logger.info("Starting slots threads...")
    for slot in all_slots:
        if slot.status == 'active':
            for interval in slot.schedule:
                for posting in slot.postings:
                    ubot = random.choice(slot.ubots)
                    ubot_id = ubot.id
                    stop_event = threading.Event()
                    job_id = f"{slot.id}_{interval['min']}_{interval['max']}_{posting.id}_{ubot_id}"
                    t = threading.Thread(target=send_slot_message, args=(slot, list(slot.chats.keys())[0], interval, posting, stop_event, ubot), name=f"Slot #{slot.name} {interval['min']}-{interval['max']} {posting.id}")
                    slots_jobs[job_id] = dict(thread=t, stop_event=stop_event)
                    t.start()
        elif slot.status == 'inactive':
            for job_key in slots_jobs:
                if slot.id in job_key:
                    slots_jobs[job_key]['stop_event'].set()

    await on_start_bot()
    await dp.start_polling()

    for t in threads:
        t.join()


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_async())


if __name__ == "__main__":
    main()