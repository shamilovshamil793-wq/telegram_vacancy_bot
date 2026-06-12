import os
import requests
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)

def search_vacancies(keyword, pages=1):
    vacancies = []
    for page in range(pages):
        url = "https://api.hh.ru/vacancies"
        params = {"text": keyword, "area": 113, "page": page, "per_page": 5}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            for item in data.get("items", []):
                salary = item.get("salary")
                if salary:
                    frm = salary.get("from", "")
                    to = salary.get("to", "")
                    cur = salary.get("currency", "")
                    if frm and to:
                        salary_str = f"{frm} - {to} {cur}"
                    elif frm:
                        salary_str = f"от {frm} {cur}"
                    elif to:
                        salary_str = f"до {to} {cur}"
                    else:
                        salary_str = "Не указана"
                else:
                    salary_str = "Не указана"
                vacancies.append({
                    "title": item.get("name", "Не указано"),
                    "company": item.get("employer", {}).get("name", "Не указана"),
                    "salary": salary_str,
                    "link": item.get("alternate_url", "")
                })
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            continue
    return vacancies

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (f"👋 Привет, {user.first_name}!\n\n"
            "Я бот для поиска вакансий на hh.ru.\n"
            "Отправь ключевое слово: 'python', 'qa', 'тестировщик'\n\n"
            "/start - приветствие\n/help - помощь\n/popular - популярные запросы")
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("🔍 Напиши ключевое слово (python, qa, tester)\n"
            "Бот найдёт 5 свежих вакансий.\n\n/popular - популярные запросы")
    await update.message.reply_text(text)

async def popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐍 Python developer", callback_data="python developer")],
        [InlineKeyboardButton("🧪 QA / Тестировщик", callback_data="qa")],
        [InlineKeyboardButton("🤖 Java developer", callback_data="java developer")],
    ]
    await update.message.reply_text("Выбери запрос:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyword = query.data
    await query.edit_message_text(f"🔍 Ищу '{keyword}'...")
    vacancies = search_vacancies(keyword, pages=1)
    if vacancies:
        text = f"✅ Найдено: {len(vacancies)}\n\n"
        for i, v in enumerate(vacancies, 1):
            text += f"{i}. *{v['title']}*\n🏢 {v['company']}\n💰 {v['salary']}\n🔗 [Ссылка]({v['link']})\n\n"
        await query.edit_message_text(text, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await query.edit_message_text(f"❌ По запросу '{keyword}' ничего не найдено.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()
    if not keyword:
        return
    await update.message.reply_text(f"🔍 Ищу '{keyword}'...")
    vacancies = search_vacancies(keyword, pages=1)
    if vacancies:
        text = f"✅ Найдено: {len(vacancies)}\n\n"
        for i, v in enumerate(vacancies, 1):
            text += f"{i}. *{v['title']}*\n🏢 {v['company']}\n💰 {v['salary']}\n🔗 [Ссылка]({v['link']})\n\n"
        await update.message.reply_text(text, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await update.message.reply_text(f"❌ По запросу '{keyword}' ничего не найдено.")

def main():
    app = Application.builder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("popular", popular))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
