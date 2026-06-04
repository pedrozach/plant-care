import os
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row

load_dotenv()

PLANTS: dict[str, dict] = {
    "hedera":      {"name": "Hedera (Hera)",        "frequency_days": 7},
    "begonia":     {"name": "Begônia Rex",           "frequency_days": 8},
    "jiboia":      {"name": "Jibóia",               "frequency_days": 10},
    "ficus":       {"name": "Ficus Tineke",          "frequency_days": 10},
    "espada":      {"name": "Espada de São Jorge",   "frequency_days": 14},
    "haworthia":   {"name": "Haworthia",             "frequency_days": 17},
    "sansevieria": {"name": "Sansevieria",           "frequency_days": 21},
}


def compute_status(
    frequency_days: int,
    last_watered: str | None,
    now: datetime | None = None,
) -> str:
    if last_watered is None:
        return "never"
    if now is None:
        now = datetime.now(timezone.utc)
    last_dt = datetime.fromisoformat(last_watered)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    days_since = (now - last_dt).days
    if days_since >= frequency_days:
        return "overdue"
    if days_since >= frequency_days - 2:
        return "due_soon"
    return "ok"


def _db_url() -> str:
    return os.getenv("DATABASE_URL", "")


@contextmanager
def get_db():
    with psycopg.connect(_db_url(), row_factory=dict_row) as conn:
        yield conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watering_logs (
                id         SERIAL PRIMARY KEY,
                plant_id   TEXT NOT NULL,
                watered_at TIMESTAMPTZ NOT NULL
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/waterings")
def get_waterings():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT plant_id, MAX(watered_at) AS watered_at "
            "FROM watering_logs GROUP BY plant_id"
        ).fetchall()
    last_by_plant = {
        row["plant_id"]: row["watered_at"].isoformat() if row["watered_at"] else None
        for row in rows
    }
    return [
        {
            "plant_id": pid,
            "last_watered": last_by_plant.get(pid),
            "status": compute_status(plant["frequency_days"], last_by_plant.get(pid)),
        }
        for pid, plant in PLANTS.items()
    ]


@app.post("/api/water/{plant_id}", status_code=201)
def water_plant(
    plant_id: str,
    x_app_secret: str | None = Header(default=None),
):
    secret = os.getenv("APP_SECRET")
    if not secret or x_app_secret != secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if plant_id not in PLANTS:
        raise HTTPException(status_code=404, detail="Plant not found")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO watering_logs (plant_id, watered_at) VALUES (%s, %s)",
            (plant_id, datetime.now(timezone.utc)),
        )
    return {"ok": True}


@app.get("/")
def serve_index():
    return FileResponse("index.html")


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    return FileResponse("images/fav-icon.png", media_type="image/png")


app.mount("/images", StaticFiles(directory="images"), name="images")
