# Plant Care — Meu Jardim Interior

A personal plant watering tracker. A FastAPI backend records watering events in SQLite; a vanilla HTML/JS frontend shows each plant's status and lets you log waterings from any device.

## Features

- Status badges per plant: **Em dia**, **Em breve**, **Atrasada**, **Nunca regada**
- Lock/unlock mechanism — watering buttons are hidden behind a password stored in `localStorage`
- 7 plants pre-configured with individual watering frequencies (7–21 days)

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)

## Local setup

```bash
# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env — set APP_SECRET to a strong password

# Run the development server
uv run uvicorn main:app --reload
```

Open `http://localhost:8000` in your browser.

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `APP_SECRET` | Password required to record waterings | *(required)* |
| `DB_PATH` | Path to the SQLite database file | `data/waterings.db` |

`APP_SECRET` must be set — the app will reject watering requests without it.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/waterings` | None | Returns all plants with last watered date and status |
| `POST` | `/api/water/{plant_id}` | `X-App-Secret` header | Records a watering event for the given plant |

### Status values

| Value | Meaning |
|---|---|
| `ok` | Watered within the frequency window |
| `due_soon` | Due within 2 days |
| `overdue` | Past the watering frequency |
| `never` | Never recorded |

## Running tests

```bash
uv run pytest
```

## Deployment

The app is configured for [Railway](https://railway.app) via `railway.toml`. Set `APP_SECRET` in the Railway environment variables panel before deploying. The database is stored at `data/waterings.db` — mount a persistent volume at `/app/data` to survive redeploys.

```
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
Health check:  /api/waterings
```
