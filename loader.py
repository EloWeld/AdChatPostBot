from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from loguru import logger
from middlewares.user_middleware import TgUserMiddleware
from pymodm.connection import connect
from dotenv import load_dotenv
import os
import pymongo

# Environment variables
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGODB_CONNECTION_URI = os.getenv("MONGODB_CONNECTION_URI")

# MongoDB and ORM initialization
MDB = pymongo.MongoClient(MONGODB_CONNECTION_URI).get_database("AdChatPostBot")
connect(MONGODB_CONNECTION_URI, alias="pymodm-conn")

# Constants class
class ConstantsMetaClass(type):
    def __getattr__(cls, key):
        doc = MDB.Settings.find_one(dict(id="Constants"))
        if not doc:
            MDB.Settings.insert_one(dict(id="Constants"))
            doc = MDB.Settings.find_one(dict(id="Constants"))
        # If key in constants
        if key in doc:
            return doc[key]

        raise AttributeError(key)

    def __str__(cls):
        return 'Const %s' % (cls.__name__,)


class Consts(metaclass=ConstantsMetaClass):
    pass


# Инициализация Aiogram бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
ms = MemoryStorage()
dp:Dispatcher = Dispatcher(bot, storage=ms)
dp.middleware.setup(LoggingMiddleware())
dp.middleware.setup(TgUserMiddleware())

# Logging initialization
logger.add("logs/botlog.log", rotation="500 MB", enqueue=True)  # Запись в файл "app.log", поворот каждые 500 МБ

# Global Variables
threads = []
pyrogram_clients = []