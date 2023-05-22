import json
import re
from typing import List
from loader import bot
from loguru import logger
import pyrogram
from models import TgUser, UserbotSession

async def notify_admins(text: str):
    admins: List[TgUser] = TgUser.objects.raw({"is_admin": True})
    
    for admin in admins:
        try:
            await bot.send_message(admin.id, text)
        except Exception as e:
            logger.error(f"Can't send message to admin: {e}")
            
            
def cutText(text:str, limit=30):
    return text if len(text) < limit else text[:limit]+ "..."

def check_html_tags(html_text):
    # Регулярное выражение для поиска открывающих и закрывающих HTML-тегов
    tag_pattern = r'<\/?[a-zA-Z]+\s*\/?>'

    # Разделяем html_text на кусочки по последовательности символов "#####"
    chunks = html_text.split("#####")

    for chunk in chunks:
        # Ищем все HTML-теги в текущем кусочке
        tags = re.findall(tag_pattern, chunk)

        stack = []
        for tag in tags:
            if tag.startswith("</"):
                # Если встретился закрывающий тег, проверяем соответствие с последним открывающим
                if len(stack) > 0 and stack[-1] == tag[2:-1]:
                    stack.pop()
                else:
                    return False
            elif tag.endswith("/>"):
                # Пропускаем самозакрывающиеся теги
                continue
            else:
                # Добавляем открывающие теги в стек
                stack.append(tag[1:-1])

        # Если после обработки всех тегов остались открытые теги, возвращаем False
        if len(stack) > 0:
            return False

    return True

def remove_html_tags(html_text):
    # Регулярное выражение для удаления HTML-тегов
    tag_pattern = re.compile(r'<.*?>')
    # Удаляем все HTML-теги из текста
    plain_text = re.sub(tag_pattern, '', html_text)
    return plain_text

# Функция для загрузки фото чата
async def download_chat_photo(client: pyrogram.Client, chat_id: int, photopath: str) -> bool:
    try:
        chat_ubot = await client.get_chat(chat_id)
        photo: pyrogram.types.ChatPhoto = chat_ubot.photo
        if photo:
            await client.download_media(photo.big_file_id, file_name=photopath)
            return True
        else:
            logger.error("Chat with no photo available")
    except Exception as e:
        logger.error(f"Error downloading photo: {e}")
    return False

# Синхронная отправка сообщений бота
def sendMessageFromBotSync(chat_id, text, reply_markup=None):
    from loader import BOT_TOKEN, bot
    import requests
    if reply_markup is not None:
        reply_markup = json.dumps({'inline_keyboard': [[{'text': button.text, 'callback_data': button.callback_data, 'url': button.url} for button in row] for row in reply_markup.inline_keyboard]}, ensure_ascii=False, indent=4)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup,
        "parse_mode": "HTML",
    }

    response = requests.post(url, data=payload)

    return response.status_code == 200

def userbotSessionToPyroClient(session: UserbotSession) -> pyrogram.Client:
    from loader import API_ID, API_HASH
    return pyrogram.Client(
        name=session.name,
        session_string=session.string_session,
        api_id=API_ID,
        api_hash=API_HASH,
    )