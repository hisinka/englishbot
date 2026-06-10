from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

import sqlite3

conn = sqlite3.connect("data.db")

engine = create_engine("sqlite:///data.db")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base.metadata.create_all(bind=engine)