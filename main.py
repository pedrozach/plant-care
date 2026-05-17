import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()


def _db_path() -> str:
    return os.getenv("DB_PATH", "data/waterings.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    db_dir = os.path.dirname(_db_path())
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watering_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id   TEXT NOT NULL,
                watered_at TEXT NOT NULL
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
