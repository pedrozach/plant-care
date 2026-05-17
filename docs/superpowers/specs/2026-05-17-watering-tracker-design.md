# Watering Tracker — Design Spec

**Date:** 2026-05-17
**Status:** Approved

## Overview

Add a watering tracker to the existing "Meu Jardim Interior" plant care page. Users open the page to see which plants need watering. A password-protected button lets the owner log "watered today" for each plant. Data is persisted in Supabase.

## Architecture

```
plant-care/
├── pyproject.toml       # UV-managed dependencies
├── .env                 # APP_SECRET, SUPABASE_URL, SUPABASE_KEY
├── main.py              # FastAPI app
├── index.html           # Existing page, extended with tracker UI
└── images/              # Existing plant photos
```

**Stack:** Python 3.12+, UV, FastAPI, uvicorn, supabase-py, python-dotenv.

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

**Supabase table: `watering_logs`**

```sql
create table watering_logs (
  id         uuid primary key default gen_random_uuid(),
  plant_id   text not null,
  watered_at timestamptz not null default now()
);
```

RLS is enabled with permissive policies for the `anon` role (reads and writes both allowed). The password gate lives in FastAPI, not in Supabase policies.

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
- Supabase unreachable → FastAPI propagates 503 → JS shows a generic "não foi possível carregar" message in place of status badges

## Out of Scope

- Watering history / log view
- Editing plant list or frequencies
- Push notifications or reminders
- Multi-user support
- Mobile app
