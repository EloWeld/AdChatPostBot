import asyncio
import threading
from typing import List

from loguru import logger
from loader import dp, threads, bot, MDB
from handlers import *
from pyroProcessing import start_pyro_client


async def on_start_bot():
    from etc.utils import notify_admins
    bot_info = await bot.get_me()
    MDB.Settings.update_one(dict(id="Constants"), {"$set": dict(BotUsername=bot_info.username)})
    logger.info(f"Bot started! https://t.me/{Consts.BotUsername}")
    await notify_admins(f"🤖 Запущен!")

async def main_async():
    global threads
    all_sessions: List[UserbotSession] = UserbotSession.objects.all()
    threads.clear()

    for usession in all_sessions:
        try:
            client = userbotSessionToPyroClient(usession)
            stop_event = threading.Event()
            t = threading.Thread(target=start_pyro_client, args=(client, stop_event, usession), name=f"Usebot #{client.name}")
            t.start()
            threads[usession.id] = dict(thread=t, stop_event=stop_event, client=client)
        except Exception as e:
            loguru.logger.error(f"Can't start userbot session {usession.name}. Error: {e}, traceback: {traceback.format_exc()}")

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