from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler

from models import TgUser

class AuthMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        from loader import MDB
        
        # Реализуйте проверку авторизации пользователя здесь
        if message.chat.type != types.ChatType.PRIVATE:
            raise CancelHandler()
        try:
            user: TgUser = TgUser.objects.get({"_id": message.from_user.id})
        except Exception as e:
            user = None
            return True
        
        if message.text == MDB.Settings.find_one()['SecretKey']:
            user.is_authenticated = True
            user.save()
            await message.answer("✅ Вы авторизированы!")
        
        if not user.is_authenticated:
            # Отменяем обработку сообщения, если пользователь не авторизован
            await message.answer("⚠️ Вы не авторизированы! Пожалуйста введите секретный ключ:")
            raise CancelHandler()