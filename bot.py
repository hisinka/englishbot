from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from deep_translator import GoogleTranslator

TOKEN = "8763198603:AAGfXly0jo29YlOgKvEiGesn36CgKCHd9-k"

dictionary = {}


async def start(update, context):
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("ИЗУЧАТЬ СЛОВА")],
        [KeyboardButton("МОЙ СЛОВАРЬ")]
    ], resize_keyboard=True)
    await update.message.reply_text("выбери действие:", reply_markup=keyboard)


async def handle_message(update, context):
    text = update.message.text
    user = update.effective_user.id

    if text == "ИЗУЧАТЬ СЛОВА":
        await update.message.reply_text("напишите слово:")
        context.user_data['mode'] = 'translate'

    elif text == "МОЙ СЛОВАРЬ":
        if user in dictionary and dictionary[user]:
            result = ""
            for rus, eng in dictionary[user].items():
                result += f"{rus} - {eng}\n"
            await update.message.reply_text(result)
        else:
            await update.message.reply_text("Словарь пуст")

    elif context.user_data.get('mode') == 'translate':
        translation = GoogleTranslator(source='ru', target='en').translate(text)
        context.user_data['last_word'] = text
        context.user_data['last_trans'] = translation

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить в словарь", callback_data="add")]
        ])

        await update.message.reply_text(f"{text} - {translation}", reply_markup=keyboard)

    else:
        await start(update, context)


async def button(update, context):
    query = update.callback_query
    await query.answer()

    user = query.from_user.id
    word = context.user_data.get('last_word')
    trans = context.user_data.get('last_trans')

    if user not in dictionary:
        dictionary[user] = {}

    dictionary[user][word] = trans

    await query.edit_message_text(f"{word} добавлено в словарь")


app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()