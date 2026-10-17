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
# Невидимый fallback (word joiner \u2060).
# Если у получателя есть Telegram Premium — показывается ПРЕМИУМ-эмодзи.
# Если нет — отображается пустота, а НЕ обычный эмодзи.
NW = "\u2060"

E_METRO   = f'<tg-emoji emoji-id="5357432498680767940">{NW}</tg-emoji>'
E_REVIEWS = f'<tg-emoji emoji-id="5458908492687497206">{NW}</tg-emoji>'
E_YOUTUBE = f'<tg-emoji emoji-id="5334681713316479679">{NW}</tg-emoji>'
E_TIKTOK  = f'<tg-emoji emoji-id="5327982530702359565">{NW}</tg-emoji>'
E_POINT   = f'<tg-emoji emoji-id="5460795821576443427">{NW}</tg-emoji>'
E_LS      = f'<tg-emoji emoji-id="5456327792868220208">{NW}</tg-emoji>'
# ====================================================


MESSAGE_TEXT = (
    f'{E_METRO} МЕТРО ШОП — @NAPOLEONPUBGM\n\n'

    f'{E_REVIEWS} ОТЗЫВЫ — @KrastuReviews\n\n'

    f'{E_YOUTUBE} ЮТУБ — '
    f'<a href="https://youtube.com/@napoleonpubg?si=VONw4qi1wNvpjTqP">ТЫК</a>'
    f'{E_POINT}\n\n'

    f'{E_TIKTOK} ТИК ТОК — '
    f'<a href="https://www.tiktok.com/@krastu_legend">ТЫК</a>'
    f'{E_POINT}\n\n'

    f'{E_LS} ЛС — @managernapoleona\n\n'

    f'{E_LS} МЕНЕДЖЕР — @managernapoleona'
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
