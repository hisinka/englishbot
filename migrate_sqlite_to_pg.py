import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import Base, User, Word, Statistics

SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///data.db")
PG_URL = os.getenv("DATABASE_URL")

src_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
dst_engine = create_engine(PG_URL, future=True)

Base.metadata.create_all(bind=dst_engine)

Dst = sessionmaker(bind=dst_engine)
dst = Dst()

try:
    with src_engine.connect() as src:
        users = src.execute(text("SELECT id, telegram_id FROM users")).mappings().all()
        words = src.execute(text("SELECT user_id, russian, english FROM words")).mappings().all()
        stats = src.execute(
            text("SELECT user_id, correct_answers, wrong_answers FROM statistics")
        ).mappings().all()

    id_map = {}
    for u in users:
        new_user = User(telegram_id=u["telegram_id"])
        dst.add(new_user)
        dst.flush()
        id_map[u["id"]] = new_user.id

    for w in words:
        if w["user_id"] not in id_map:
            continue
        dst.add(Word(user_id=id_map[w["user_id"]], russian=w["russian"], english=w["english"]))

    for s in stats:
        if s["user_id"] not in id_map:
            continue
        dst.add(Statistics(
            user_id=id_map[s["user_id"]],
            correct_answers=s["correct_answers"] or 0,
            wrong_answers=s["wrong_answers"] or 0,
        ))

    dst.commit()
    print(f"перенесено: users={len(users)}, words={len(words)}, stats={len(stats)}")
finally:
    dst.close()
