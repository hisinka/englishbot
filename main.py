from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from deep_translator import GoogleTranslator

TOKEN = "8763198603:AAGfXly0jo29YlOgKvEiGesn36CgKCHd9-k"


async def start(update, context):
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("ИЗУЧАТЬ СЛОВА")],
        [KeyboardButton("МОЙ СЛОВАРЬ")]
    ], resize_keyboard=True)
    await update.message.reply_text("Выбери действие:", reply_markup=keyboard)


async def handle_message(update, context):
    text = update.message.text

    if text == "ИЗУЧАТЬ СЛОВА":
        await update.message.reply_text("Напиши слово:")
        context.user_data['mode'] = 'translate'

    elif text == "МОЙ СЛОВАРЬ":
        await update.message.reply_text("Словарь пока пустой")

    elif context.user_data.get('mode') == 'translate':
        translation = GoogleTranslator(source='ru', target='en').translate(text)
        await update.message.reply_text(f"{text} - {translation}")
        context.user_data['mode'] = None

    else:
        await start(update, context)


app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
