from typing import List

from loguru import logger
from models import TgUser
from loader import bot

async def notify_admins(text: str):
    admins: List[TgUser] = TgUser.objects.raw({"is_admin": True})
    
    for admin in admins:
        try:
            await bot.send_message(admin.id, text)
        except Exception as e:
            logger.error(f"Can't send message to admin: {e}")