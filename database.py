import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.getenv("DATABASE_PATH")

if DATABASE_PATH:
    database_file = Path(DATABASE_PATH)
else:
    database_file = BASE_DIR / "debliga.db"

# Ensure the parent directory exists for the SQLite file.
database_file.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{database_file}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()