from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from deep_translator import GoogleTranslator
from database import SessionLocal
from models import User, Word

TOKEN = "8763198603:AAGfXly0jo29YlOgKvEiGesn36CgKCHd9-k"



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

        db = SessionLocal()

        user_obj = db.query(User).filter(User.telegram_id == user).first()

        if not user_obj:
            await update.message.reply_text("Словарь пуст")

            db.close()

            return

        words = db.query(Word).filter(Word.user_id == user_obj.id).all()

        if not words:

            await update.message.reply_text("Словарь пуст")

        else:

            result = ""

            for w in words:
                result += f"{w.russian} - {w.english}\n"

            await update.message.reply_text(result)

        db.close()

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

    user_id = query.from_user.id
    word = context.user_data.get('last_word')
    trans = context.user_data.get('last_trans')

    if not word or not trans:
        await query.edit_message_text("Ошибка: сначала отправь слово")
        return

    db = SessionLocal()

    user = db.query(User).filter(User.telegram_id == user_id).first()

    if not user:
        user = User(telegram_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    existing = db.query(Word).filter(
        Word.user_id == user.id,
        Word.russian == word
    ).first()

    if not existing:
        new_word = Word(
            user_id=user.id,
            russian=word,
            english=trans
        )
        db.add(new_word)
        db.commit()
        db.close()

    await query.edit_message_text(f"{word} добавлено в словарь")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()