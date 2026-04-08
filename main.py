from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TOKEN = "8763198603:AAGfXly0jo29YlOgKvEiGesn36CgKCHd9-k"

async def start(update, context):
    keyboard = [
        [KeyboardButton("Кнопка 1"), KeyboardButton("Кнопка 2")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Клавиатура внизу:", reply_markup=reply_markup)

async def handle_message(update, context):
    pass

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.run_polling()