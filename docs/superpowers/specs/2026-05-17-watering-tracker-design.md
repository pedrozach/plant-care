# Watering Tracker — Design Spec

**Date:** 2026-05-17
**Status:** Approved

## Overview

Add a watering tracker to the existing "Meu Jardim Interior" plant care page. Users open the page to see which plants need watering. A password-protected button lets the owner log "watered today" for each plant. Data is persisted in a local SQLite file.

## Architecture

```
plant-care/
├── pyproject.toml       # UV-managed dependencies
├── .env                 # APP_SECRET only
├── main.py              # FastAPI app
├── railway.toml         # Railway deployment config (points volume at /data)
├── index.html           # Existing page, extended with tracker UI
├── images/              # Existing plant photos
└── data/                # SQLite file lives here (mounted as Railway volume)
    └── .gitkeep
```

**Stack:** Python 3.12+, UV, FastAPI, uvicorn, python-dotenv. No external database service.

**Hosting:** Railway runs the FastAPI process. A Railway persistent volume is mounted at `/data` so `data/waterings.db` survives container restarts and redeploys.

FastAPI serves two roles:
1. Static file server for `index.html` and `images/`
2. REST API for watering log reads and writes

The frontend remains a single HTML file with vanilla JS. On page load, JS fetches `/api/waterings` and renders status badges. The password is stored in `localStorage` and sent as an `X-App-Secret` header on write requests. The secret is validated server-side in FastAPI — it never appears in client-side source.

## API Endpoints

### `GET /api/waterings`
Returns the latest watering date and computed status for all plants. Public, no auth required.

**Response:**
```json
[
  {
    "plant_id": "hedera",
    "last_watered": "2026-05-15T10:00:00Z",
    "status": "due_soon"
  },
  ...
]
```

**Status values:**
- `ok` — last watered within the expected frequency window
- `due_soon` — within 2 days of the frequency threshold
- `overdue` — past the frequency threshold
- `never` — no watering record exists

### `POST /api/water/{plant_id}`
Logs "watered today" for the given plant. Requires `X-App-Secret` header matching `APP_SECRET` env var. Returns `401` on wrong secret, `404` on unknown `plant_id`.

## Data Model

**SQLite table: `watering_logs`** — created automatically on startup if it doesn't exist.

```sql
CREATE TABLE IF NOT EXISTS watering_logs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  plant_id   TEXT NOT NULL,
  watered_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

`watered_at` is stored as an ISO 8601 string in UTC. The file path is `data/waterings.db`, configurable via `DB_PATH` env var so it can be overridden to `/data/waterings.db` in the Railway environment.

## Plant Registry

Hardcoded in `main.py`. The `plant_id` values match the slugs used in `index.html`.

| plant_id    | Name                  | Frequency (days) |
|-------------|----------------------|------------------|
| hedera      | Hedera (Hera)        | 7                |
| begonia     | Begônia Rex          | 8                |
| jiboia      | Jibóia               | 10               |
| ficus       | Ficus Tineke         | 10               |
| espada      | Espada de São Jorge  | 14               |
| haworthia   | Haworthia            | 17               |
| sansevieria | Sansevieria          | 21               |

## UI Changes to index.html

Each plant card is extended with:

1. **Status badge** — positioned top-left on the card image. A small colored pill:
   - Green (`ok`)
   - Amber (`due_soon`)
   - Red (`overdue`)
   - Grey (`never`)

2. **"Reguei hoje" button** — added at the bottom of `.card-body`. Hidden when the page is locked. On click, sends `POST /api/water/{plant_id}` with the stored secret header. On success, refreshes the card's status badge. On 401, clears the stored password and shows an error.

3. **Lock icon in the header** — clicking it prompts for the password (browser `prompt()`). The entered value is stored immediately in `localStorage` and the "Reguei hoje" buttons become visible. No server round-trip on unlock — the password is validated lazily when the first write is attempted. If the page is already unlocked, clicking the icon locks it (clears `localStorage` and hides the buttons).

## Error Handling

- Wrong password → FastAPI returns 401 → JS clears localStorage, shows brief error message on the card
- Unknown plant_id → FastAPI returns 404 → JS shows console warning (silent to user)
- DB unavailable → FastAPI returns 503 → JS shows a generic "não foi possível carregar" message in place of status badges

## Deployment (Railway)

- `railway.toml` sets the start command (`uvicorn main:app --host 0.0.0.0 --port $PORT`) and declares the `/data` volume mount
- `APP_SECRET` and `DB_PATH=/data/waterings.db` are set as Railway environment variables
- Every push to `main` on GitHub triggers an automatic redeploy; the SQLite file on the volume is unaffected

## Out of Scope

- Watering history / log view
- Editing plant list or frequencies
- Push notifications or reminders
- Multi-user support
- Mobile app
