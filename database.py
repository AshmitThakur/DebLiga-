import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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


def migrate_existing_schema(bind) -> None:
    """Add columns that ``create_all`` cannot add to existing SQLite databases."""
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    with bind.begin() as connection:
        if "debates" in table_names:
            debate_columns = {
                column["name"] for column in inspector.get_columns("debates")
            }
            debate_additions = {
                "government_reply_score": "FLOAT",
                "opposition_reply_score": "FLOAT",
            }
            for column_name, column_type in debate_additions.items():
                if column_name not in debate_columns:
                    connection.execute(text(
                        f"ALTER TABLE debates ADD COLUMN {column_name} {column_type}"
                    ))

        if "speaker_performances" in table_names:
            performance_columns = {
                column["name"]
                for column in inspector.get_columns("speaker_performances")
            }
            if "is_swing" not in performance_columns:
                connection.execute(text(
                    "ALTER TABLE speaker_performances "
                    "ADD COLUMN is_swing BOOLEAN NOT NULL DEFAULT 0"
                ))


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
