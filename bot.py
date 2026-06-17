import logging
import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import func
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)
from deep_translator import GoogleTranslator

from database import SessionLocal
from models import User, Word, Statistics

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("englishbot")
logging.getLogger("httpx").setLevel(logging.WARNING)

TOKEN = os.getenv("TOKEN")


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("ПЕРЕВЕСТИ СЛОВО")],
            [KeyboardButton("ИЗУЧАТЬ СЛОВА")],
            [KeyboardButton("МОЙ СЛОВАРЬ")],
            [KeyboardButton("СТАТИСТИКА")],
        ],
        resize_keyboard=True,
    )


def learn_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("СТОП")]],
        resize_keyboard=True,
    )


def pick_word(db, user_id, exclude_ids):
    return (
        db.query(Word)
        .filter(Word.user_id == user_id, Word.id.notin_(exclude_ids))
        .order_by(func.random())
        .first()
    )


def get_or_create_user(db, telegram_id):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.flush()
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    with session_scope() as db:
        is_new = db.query(User).filter(User.telegram_id == telegram_user_id).first() is None
        if is_new:
            get_or_create_user(db, telegram_user_id)

    if is_new:
        await update.message.reply_text(
            "Привет! 👋 Я помогу тебе учить английские слова.\n\n"
            "Вот что я умею:\n"
            "- ПЕРЕВЕСТИ СЛОВО - переведу слово с русского на английский и предложу добавить его в твой словарь\n"
            "- ИЗУЧАТЬ СЛОВА - буду давать слова из твоего словаря, а ты пишешь перевод\n"
            "- МОЙ СЛОВАРЬ - покажу все твои слова, ненужные можно удалить\n"
            "- СТАТИСТИКА - сколько ответов правильных, а сколько с ошибкой\n\n"
            "Начни с кнопки ПЕРЕВЕСТИ СЛОВО — добавь несколько слов, а потом тренируйся через ИЗУЧАТЬ СЛОВА.",
            reply_markup=main_keyboard(),
        )
    else:
        await update.message.reply_text("С возвращением! Выбери действие:", reply_markup=main_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "что умею:\n"
        "— ПЕРЕВЕСТИ СЛОВО — переведу с русского на английский и предложу добавить в словарь\n"
        "— ИЗУЧАТЬ СЛОВА — дам случайное слово из твоего словаря, ты пишешь перевод\n"
        "— МОЙ СЛОВАРЬ — список слов, можно удалять\n"
        "— СТАТИСТИКА — счётчик правильных и ошибок\n\n"
        "команды: /start /help /stats"
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with session_scope() as db:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("статистика пустая, ты ещё ничего не учил")
            return
        stat = db.query(Statistics).filter(Statistics.user_id == user.id).first()
        if not stat:
            await update.message.reply_text("статистика пустая, ты ещё ничего не учил")
            return
        await update.message.reply_text(
            f"✅ Правильных ответов: {stat.correct_answers}\n"
            f"❌ Ошибок: {stat.wrong_answers}"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    telegram_user_id = update.effective_user.id
    mode = context.user_data.get("mode")

    if text == "ПЕРЕВЕСТИ СЛОВО":
        context.user_data["mode"] = "translate"
        await update.message.reply_text("напиши русское слово для перевода")
        return

    if text == "СТАТИСТИКА":
        await show_stats(update, context)
        return

    if text == "СТОП":
        context.user_data["mode"] = None
        context.user_data["learn_word_id"] = None
        context.user_data["learn_seen"] = []
        await update.message.reply_text("остановил. выбери действие:", reply_markup=main_keyboard())
        return

    if text == "ИЗУЧАТЬ СЛОВА":
        with session_scope() as db:
            user = db.query(User).filter(User.telegram_id == telegram_user_id).first()
            if not user:
                await update.message.reply_text("словарь пуст, добавь слова через ПЕРЕВЕСТИ СЛОВО")
                return
            word = pick_word(db, user.id, [])
            if not word:
                await update.message.reply_text("словарь пуст, добавь слова через ПЕРЕВЕСТИ СЛОВО")
                return
            context.user_data["mode"] = "learn"
            context.user_data["learn_word_id"] = word.id
            context.user_data["learn_seen"] = [word.id]
            await update.message.reply_text(f"переведи слово:\n\n{word.russian}", reply_markup=learn_keyboard())
        return

    if text == "МОЙ СЛОВАРЬ":
        with session_scope() as db:
            user = db.query(User).filter(User.telegram_id == telegram_user_id).first()
            if not user:
                await update.message.reply_text("словарь пуст")
                return
            words = db.query(Word).filter(Word.user_id == user.id).all()
            if not words:
                await update.message.reply_text("словарь пуст")
                return
            keyboard = [
                [InlineKeyboardButton(f"{w.russian} - {w.english} ❌", callback_data=f"delete_{w.id}")]
                for w in words
            ]
            await update.message.reply_text("твой словарь:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if mode == "translate":
        try:
            translation = GoogleTranslator(source="ru", target="en").translate(text)
        except Exception as e:
            logger.exception("translator failed: %s", e)
            await update.message.reply_text("не получилось перевести, попробуй ещё раз")
            return
        if not translation:
            await update.message.reply_text("пустой перевод, попробуй другое слово")
            return
        context.user_data["last_word"] = text
        context.user_data["last_trans"] = translation
        await update.message.reply_text(
            f"{text} - {translation}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Добавить в словарь", callback_data="add")]]
            ),
        )
        return

    if mode == "learn":
        word_id = context.user_data.get("learn_word_id")
        if not word_id:
            await update.message.reply_text("что-то сломалось, начни заново через ИЗУЧАТЬ СЛОВА")
            context.user_data["mode"] = None
            return
        with session_scope() as db:
            word = db.query(Word).filter(Word.id == word_id).first()
            if not word:
                await update.message.reply_text("слово куда-то делось, начни заново")
                context.user_data["mode"] = None
                return
            user = get_or_create_user(db, telegram_user_id)
            stat = db.query(Statistics).filter(Statistics.user_id == user.id).first()
            if not stat:
                stat = Statistics(user_id=user.id, correct_answers=0, wrong_answers=0)
                db.add(stat)
                db.flush()
            if text.lower().strip() == word.english.lower().strip():
                stat.correct_answers += 1
                await update.message.reply_text("✅ правильно!")
            else:
                stat.wrong_answers += 1
                await update.message.reply_text(f"❌ неправильно\nПравильный ответ: {word.english}")

            seen = context.user_data.get("learn_seen", [])
            next_word = pick_word(db, user.id, seen)
            if not next_word:
                context.user_data["mode"] = None
                context.user_data["learn_word_id"] = None
                context.user_data["learn_seen"] = []
                await update.message.reply_text(
                    "ты прошёл весь словарь 🎉 выбери действие:",
                    reply_markup=main_keyboard(),
                )
                return
            seen.append(next_word.id)
            context.user_data["learn_seen"] = seen
            context.user_data["learn_word_id"] = next_word.id
            await update.message.reply_text(
                f"переведи слово:\n\n{next_word.russian}",
                reply_markup=learn_keyboard(),
            )
        return

    await start(update, context)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("delete_"):
        try:
            word_id = int(data.split("_", 1)[1])
        except ValueError:
            await query.edit_message_text("ошибка: некорректный id")
            return
        with session_scope() as db:
            word = db.query(Word).filter(Word.id == word_id).first()
            if word:
                db.delete(word)
                await query.edit_message_text("слово удалено")
            else:
                await query.edit_message_text("слово уже удалено")
        return

    if data == "add":
        telegram_user_id = query.from_user.id
        word_ru = context.user_data.get("last_word")
        word_en = context.user_data.get("last_trans")
        if not word_ru or not word_en:
            await query.edit_message_text("сначала отправь слово через ПЕРЕВЕСТИ СЛОВО")
            return
        with session_scope() as db:
            user = get_or_create_user(db, telegram_user_id)
            existing = (
                db.query(Word)
                .filter(Word.user_id == user.id, Word.russian == word_ru)
                .first()
            )
            if existing:
                await query.edit_message_text(f"«{word_ru}» уже в словаре")
                return
            db.add(Word(user_id=user.id, russian=word_ru, english=word_en))
        await query.edit_message_text(f"{word_ru} добавлено в словарь")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("unhandled exception", exc_info=context.error)


def build_app():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))
    app.add_error_handler(error_handler)
    return app


if __name__ == "__main__":
    logger.info("englishbot starting in polling mode")
    build_app().run_polling()
