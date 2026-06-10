from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from deep_translator import GoogleTranslator
from database import SessionLocal
from models import User, Word, Statistics

TOKEN = "8763198603:AAGJN96DYeSZ1pymUzq0mXQpf_1-JjSo1AQ"



async def start(update, context):
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("ПЕРЕВЕСТИ СЛОВО")],
        [KeyboardButton("ИЗУЧАТЬ СЛОВА")],
        [KeyboardButton("МОЙ СЛОВАРЬ")]
    ], resize_keyboard=True)
    await update.message.reply_text("выбери действие:", reply_markup=keyboard)


async def handle_message(update, context):
    text = update.message.text
    user = update.effective_user.id

    if text == "ПЕРЕВЕСТИ СЛОВО":
        context.user_data["mode"] = "translate"

        await update.message.reply_text(
            "Напиши русское слово для перевода"
        )
        return

    if text == "ИЗУЧАТЬ СЛОВА":
        context.user_data['mode'] = 'learn'

        db = SessionLocal()
        user_obj = db.query(User).filter(User.telegram_id == user).first()

        if not user_obj:
            await update.message.reply_text("Словарь пуст")
            db.close()
            return

        word = db.query(Word).filter(Word.user_id == user_obj.id).first()

        db.close()

        if not word:
            await update.message.reply_text("Словарь пуст")
            return

        context.user_data['learn_word_id'] = word.id

        await update.message.reply_text(
            f"Переведи слово:\n\n{word.russian}"
        )
        return


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

            keyboard = []

            for w in words:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{w.russian} - {w.english} ❌",
                        callback_data=f"delete_{w.id}"
                    )
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text("Твой словарь:", reply_markup=reply_markup)

        db.close()

    elif context.user_data.get('mode') == 'translate':

        translation = GoogleTranslator(source='ru', target='en').translate(text)
        context.user_data['last_word'] = text
        context.user_data['last_trans'] = translation

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить в словарь", callback_data="add")]
        ])

        await update.message.reply_text(f"{text} - {translation}", reply_markup=keyboard)


    elif context.user_data.get('mode') == 'learn':

        word_id = context.user_data.get('learn_word_id')

        db = SessionLocal()

        word = db.query(Word).filter(

            Word.id == word_id

        ).first()

        if not word:
            db.close()

            await update.message.reply_text("Ошибка")

            return

        user_obj = db.query(User).filter(

            User.telegram_id == user

        ).first()

        stat = db.query(Statistics).filter(

            Statistics.user_id == user_obj.id

        ).first()

        if not stat:
            stat = Statistics(user_id=user_obj.id)

            db.add(stat)

            db.commit()

        if text.lower().strip() == word.english.lower().strip():

            stat.correct_answers += 1

            await update.message.reply_text(

                "✅ правильно!"

            )


        else:

            stat.wrong_answers += 1

            await update.message.reply_text(

                f"❌ неправильно\nПравильный ответ: {word.english}"

            )

        db.commit()

        db.close()

        context.user_data['mode'] = None

        return


    else:

        await start(update, context)
async def button(update, context):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("delete_"):
        word_id = int(data.split("_")[1])

        db = SessionLocal()
        word = db.query(Word).filter(Word.id == word_id).first()

        if word:
            db.delete(word)
            db.commit()

        db.close()

        await query.edit_message_text("Слово удалено")
        return

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