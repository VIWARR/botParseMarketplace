import logging
from telegram import *
from telegram.ext import *
from wb_parser.wb_parser import parse_products
from config import TOKEN
from wb_parser.utils import *


# Логирование для получения информации о работе бота
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# Обработчик команды /start
async def start(update: Update, context: CallbackContext) -> None:
    # Отправка приветственного сообщения пользователю
    await update.message.reply_text('Привет! Я бот для парсинга информации о товаров с Маркетплейсов Беларуси.')

    #Создание клавиатуры
    keyboard = [
        ["Парсинг информации с Wildberries"],
        ["Парсинг информации с Ozon"],
        ["Сводная таблица с маркетплейсов по товару"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите действие: ", reply_markup=reply_markup)


# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text

    if text == "Парсинг информации с Wildberries":
        await update.message.reply_text(
            "Введите поисковый запрос и количество страниц через пробел (например, 'гель для стирки 2')"
        )
        context.user_data['action'] = 'wildberries'
    elif text == "Парсинг информации с Ozon":
        await update.message.reply_text("Функция в разработке.")
    elif text == "Сводная таблица":
        await update.message.reply_text("Функция в разработке")
    else:
        action = context.user_data.get('action')
        if action == 'wildberries':
            await handle_parse_request(update, context)

async def handle_parse_request(update: Update, context: CallbackContext) -> None:
    message = update.message.text
    search_term, num_pages = message.rsplit(maxsplit=1)
    num_pages = int(num_pages)

    await update.message.reply_text(f"Выполняется парсинг '{search_term}' - количество страниц '{num_pages}'")

    data = await parse_products(search_term, num_pages)

    file_path = create_excel_file(data)

    await context.bot.send_document(
        chat_id=update.effective_chat.id, document=open(file_path, 'rb')
    )

    await update.message.reply_text("Парсинг завершен. Файл с данными отправлен.")


def main() -> None:
    """Запуск бота."""
    # Создание объекта Application и передача ему токена
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))

    # Регистрация обработчиков текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()