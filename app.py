import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8912094394:AAE7myoYE7CbVWFWRljAbrKDG-mxEVfitK4"
CHANNEL_ID = -1004365521482  # @NapoleonBiography
# ================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ================== ПРЕМИУМ-ЭМОДЗИ ==================
# Формат: <tg-emoji emoji-id="ID">ОБЫЧНЫЙ_ЭМОДЗИ</tg-emoji>
# Если у бота/получателя есть Premium — покажется ПРЕМИУМ-эмодзи.
# Если нет — покажется обычный эмодзи (fallback), сообщение не будет пустым.
# ====================================================

MESSAGE_TEXT = (
    '<tg-emoji emoji-id="5357432498680767940">🛒</tg-emoji> МЕТРО ШОП — @NAPOLEONPUBGM\n\n'

    '<tg-emoji emoji-id="5458908492687497206">💬</tg-emoji> ОТЗЫВЫ — @KrastuReviews\n\n'

    '<tg-emoji emoji-id="5334681713316479679">▶️</tg-emoji> ЮТУБ — '
    '<a href="https://youtube.com/@napoleonpubg?si=VONw4qi1wNvpjTqP">ТЫК</a>'
    '<tg-emoji emoji-id="5460795821576443427">👆</tg-emoji>\n\n'

    '<tg-emoji emoji-id="5327982530702359565">🎵</tg-emoji> ТИК ТОК — '
    '<a href="https://www.tiktok.com/@krastu_legend">ТЫК</a>'
    '<tg-emoji emoji-id="5460795821576443427">👆</tg-emoji>\n\n'

    '<tg-emoji emoji-id="5456327792868220208">📩</tg-emoji> ЛС — @managernapoleona\n\n'

    '<tg-emoji emoji-id="5456327792868220208">👤</tg-emoji> МЕНЕДЖЕР — @managernapoleona'
)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Отправляет сообщение в канал при нажатии /start."""
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=MESSAGE_TEXT,
            disable_web_page_preview=False
        )
        await message.answer("✅ Сообщение успешно отправлено в канал @NapoleonBiography")
        logger.info(f"Сообщение отправлено в канал {CHANNEL_ID} по запросу {message.from_user.id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке:\n<code>{e}</code>")
        logger.exception("Ошибка при отправке сообщения")


async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
