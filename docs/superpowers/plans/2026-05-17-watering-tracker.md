# Watering Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a watering tracker to the existing "Meu Jardim Interior" page — plant cards show a colour-coded status badge, and a password-protected "Reguei hoje" button logs today's watering to a local SQLite database.

**Architecture:** FastAPI serves the existing `index.html` and `images/` as static files and exposes two API endpoints (`GET /api/waterings`, `POST /api/water/{plant_id}`). The password secret is validated server-side; the frontend stores it in `localStorage` and sends it as a request header. SQLite stores watering logs in `data/waterings.db`, mounted as a Railway persistent volume in production.

**Tech Stack:** Python 3.12+, UV, FastAPI, uvicorn, python-dotenv, pytest, httpx (via TestClient).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Create | UV project config + dependencies |
| `.gitignore` | Modify | Ignore `.env` and `data/*.db` |
| `.env.example` | Create | Document required env vars |
| `data/.gitkeep` | Create | Keep `data/` directory in git |
| `main.py` | Create | FastAPI app: DB layer, plant registry, status logic, endpoints, static serving |
| `tests/__init__.py` | Create | Empty — makes `tests/` a package |
| `tests/test_main.py` | Create | All endpoint and logic tests |
| `railway.toml` | Create | Railway build + start command |
| `index.html` | Modify | Add data-plant-id attrs, status badges, lock icon, buttons, JS |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `data/.gitkeep`
- Create: `tests/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "plant-care"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "python-dotenv>=1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.env.example`**

```
APP_SECRET=change-me
DB_PATH=data/waterings.db
```

- [ ] **Step 3: Create `.env`** (not committed)

Copy `.env.example` to `.env` and set a real `APP_SECRET` value. Do not commit this file.

- [ ] **Step 4: Update `.gitignore`**

Add these lines to `.gitignore` (create the file if it doesn't exist):

```
.env
data/*.db
__pycache__/
.pytest_cache/
```

- [ ] **Step 5: Create `data/.gitkeep` and `tests/__init__.py`**

```bash
touch data/.gitkeep tests/__init__.py
```

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

Expected output: packages installed into `.venv/`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example data/.gitkeep tests/__init__.py .gitignore
git commit -m "chore: project scaffolding for watering tracker"
```

---

## Task 2: DB Layer + App Skeleton

**Files:**
- Create: `main.py`
- Create: `tests/test_main.py` (fixture setup only)

- [ ] **Step 1: Write the test fixture**

Create `tests/test_main.py`:

```python
import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("APP_SECRET", "secret123")


@pytest.fixture
def client():
    from main import app, init_db
    init_db()
    with TestClient(app) as c:
        yield c
```

- [ ] **Step 2: Run the test file to verify it fails cleanly (no `main.py` yet)**

```bash
uv run pytest tests/test_main.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Create `main.py` with DB layer and empty app**

```python
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
```

- [ ] **Step 4: Run the fixture again to verify it passes (no test functions yet)**

```bash
uv run pytest tests/test_main.py -v
```

Expected: `no tests ran` (0 collected, no errors)

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: FastAPI skeleton with SQLite DB layer"
```

---

## Task 3: Plant Registry + Status Computation

**Files:**
- Modify: `main.py` — add `PLANTS` dict and `compute_status()`
- Modify: `tests/test_main.py` — add status computation tests

- [ ] **Step 1: Write the failing tests**

Append these test functions to `tests/test_main.py` (the `datetime`/`timezone` imports were already added in Task 2):

```python
from main import compute_status


def test_compute_status_never():
    assert compute_status(7, None) == "never"


def test_compute_status_ok():
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc)  # 4 days ago
    assert compute_status(7, last.isoformat(), now=now) == "ok"


def test_compute_status_due_soon():
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)  # 6 days ago
    assert compute_status(7, last.isoformat(), now=now) == "due_soon"


def test_compute_status_overdue():
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)  # 7 days ago
    assert compute_status(7, last.isoformat(), now=now) == "overdue"


def test_compute_status_boundary_due_soon():
    # exactly 2 days before frequency → due_soon
    now = datetime(2026, 5, 17, 12, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 5, 12, 12, 0, 0, tzinfo=timezone.utc)  # 5 days ago, frequency 7
    assert compute_status(7, last.isoformat(), now=now) == "due_soon"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_main.py -v
```

Expected: `ImportError: cannot import name 'compute_status' from 'main'`

- [ ] **Step 3: Add `PLANTS` and `compute_status` to `main.py`**

Add after the `load_dotenv()` line and before `_db_path()`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_main.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: plant registry and status computation"
```

---

## Task 4: GET /api/waterings Endpoint

**Files:**
- Modify: `main.py` — add GET endpoint
- Modify: `tests/test_main.py` — add endpoint tests

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_main.py`:

```python
def test_get_waterings_all_plants_returned(client):
    res = client.get("/api/waterings")
    assert res.status_code == 200
    data = res.json()
    plant_ids = {item["plant_id"] for item in data}
    assert plant_ids == {
        "hedera", "begonia", "jiboia", "ficus",
        "espada", "haworthia", "sansevieria",
    }


def test_get_waterings_never_status_when_no_log(client):
    res = client.get("/api/waterings")
    for item in res.json():
        assert item["status"] == "never"
        assert item["last_watered"] is None


def test_get_waterings_ok_status_after_watering(client):
    from main import get_db
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO watering_logs (plant_id, watered_at) VALUES (?, ?)",
            ("hedera", now),
        )
    res = client.get("/api/waterings")
    hedera = next(item for item in res.json() if item["plant_id"] == "hedera")
    assert hedera["status"] == "ok"
    assert hedera["last_watered"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_main.py::test_get_waterings_all_plants_returned -v
```

Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Add the GET endpoint to `main.py`**

Add after the `app = FastAPI(lifespan=lifespan)` line:

```python
@app.get("/api/waterings")
def get_waterings():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT plant_id, MAX(watered_at) AS watered_at "
            "FROM watering_logs GROUP BY plant_id"
        ).fetchall()
    last_by_plant = {row["plant_id"]: row["watered_at"] for row in rows}
    return [
        {
            "plant_id": pid,
            "last_watered": last_by_plant.get(pid),
            "status": compute_status(plant["frequency_days"], last_by_plant.get(pid)),
        }
        for pid, plant in PLANTS.items()
    ]
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest tests/test_main.py -v
```

Expected: 8 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: GET /api/waterings endpoint"
```

---

## Task 5: POST /api/water/{plant_id} Endpoint

**Files:**
- Modify: `main.py` — add POST endpoint
- Modify: `tests/test_main.py` — add endpoint tests

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_main.py`:

```python
def test_water_plant_success(client):
    res = client.post(
        "/api/water/hedera",
        headers={"X-App-Secret": "secret123"},
    )
    assert res.status_code == 201
    assert res.json() == {"ok": True}


def test_water_plant_updates_status(client):
    client.post("/api/water/hedera", headers={"X-App-Secret": "secret123"})
    waterings = client.get("/api/waterings").json()
    hedera = next(item for item in waterings if item["plant_id"] == "hedera")
    assert hedera["status"] == "ok"


def test_water_plant_wrong_secret_returns_401(client):
    res = client.post(
        "/api/water/hedera",
        headers={"X-App-Secret": "wrong"},
    )
    assert res.status_code == 401


def test_water_plant_missing_secret_returns_401(client):
    res = client.post("/api/water/hedera")
    assert res.status_code == 401


def test_water_plant_unknown_plant_returns_404(client):
    res = client.post(
        "/api/water/unknown-plant",
        headers={"X-App-Secret": "secret123"},
    )
    assert res.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_main.py::test_water_plant_success -v
```

Expected: FAIL with `405 Method Not Allowed`

- [ ] **Step 3: Add the POST endpoint to `main.py`**

Add the import at the top of `main.py` (update the existing FastAPI import line):

```python
from fastapi import FastAPI, Header, HTTPException
```

Then add the endpoint after `get_waterings()`:

```python
@app.post("/api/water/{plant_id}", status_code=201)
def water_plant(
    plant_id: str,
    x_app_secret: str | None = Header(default=None),
):
    if x_app_secret != os.getenv("APP_SECRET", ""):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if plant_id not in PLANTS:
        raise HTTPException(status_code=404, detail="Plant not found")
    watered_at = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO watering_logs (plant_id, watered_at) VALUES (?, ?)",
            (plant_id, watered_at),
        )
    return {"ok": True}
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest tests/test_main.py -v
```

Expected: 13 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: POST /api/water/{plant_id} endpoint"
```

---

## Task 6: Static File Serving

**Files:**
- Modify: `main.py` — add static file routes

- [ ] **Step 1: Add static file serving to `main.py`**

Add to the imports at the top:

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
```

Add at the bottom of `main.py` (after all route definitions):

```python
@app.get("/")
def serve_index():
    return FileResponse("index.html")


app.mount("/images", StaticFiles(directory="images"), name="images")
```

- [ ] **Step 2: Run all tests to confirm nothing broke**

```bash
uv run pytest tests/test_main.py -v
```

Expected: 13 tests PASSED

- [ ] **Step 3: Smoke-test the running server**

```bash
uv run uvicorn main:app --reload
```

Open `http://localhost:8000` in a browser. The existing plant care page should appear, identical to before. Open `http://localhost:8000/api/waterings` — should return JSON with all 7 plants and status `"never"`.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: serve index.html and images via FastAPI"
```

---

## Task 7: Frontend — Status Badges

**Files:**
- Modify: `index.html` — add badge CSS, `data-plant-id` attributes, and badge HTML

- [ ] **Step 1: Add badge CSS inside the `<style>` block**

Find the closing `</style>` tag in `index.html` and insert this block immediately before it:

```css
    /* Status badges */
    .status-badge {
      position: absolute;
      top: 12px; left: 14px;
      z-index: 3;
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 20px;
      color: #fff;
    }
    .status-ok       { background: #2e7d32; }
    .status-due_soon { background: #e65100; }
    .status-overdue  { background: #b71c1c; }
    .status-never    { background: #546e7a; }
```

- [ ] **Step 2: Add `data-plant-id` attributes and badge HTML to all 7 cards**

For each `.card` div, add a `data-plant-id` attribute and a `.status-badge` span inside `.card-image-wrap`. Make all 7 changes:

**Card 1 — hedera:**
```html
  <div class="card" data-plant-id="hedera">
    <div class="card-image-wrap">
      <img src="images/hedera.jpg" alt="Hedera"/>
      <span class="card-number">01</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 2 — begonia:**
```html
  <div class="card" data-plant-id="begonia">
    <div class="card-image-wrap">
      <img src="images/begonia.jpg" alt="Begônia Rex"/>
      <span class="card-number">02</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 3 — jiboia:**
```html
  <div class="card" data-plant-id="jiboia">
    <div class="card-image-wrap">
      <img src="images/jiboia.jpg" alt="Jibóia"/>
      <span class="card-number">03</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 4 — ficus:**
```html
  <div class="card" data-plant-id="ficus">
    <div class="card-image-wrap">
      <img src="images/ficus.jpg" alt="Ficus Tineke"/>
      <span class="card-number">04</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 5 — espada:**
```html
  <div class="card" data-plant-id="espada">
    <div class="card-image-wrap">
      <img src="images/espada.jpg" alt="Espada de São Jorge"/>
      <span class="card-number">05</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 6 — haworthia:**
```html
  <div class="card" data-plant-id="haworthia">
    <div class="card-image-wrap">
      <img src="images/haworthia.jpg" alt="Haworthia"/>
      <span class="card-number">06</span>
      <span class="status-badge status-never">A carregar…</span>
```

**Card 7 — sansevieria:**
```html
  <div class="card" data-plant-id="sansevieria">
    <div class="card-image-wrap">
      <img src="images/sansevieria.jpg" alt="Sansevieria"/>
      <span class="card-number">07</span>
      <span class="status-badge status-never">A carregar…</span>
```

- [ ] **Step 3: Verify in browser**

Run `uv run uvicorn main:app --reload` and open `http://localhost:8000`. Each plant card should show a grey "A carregar…" pill in the top-left of its photo.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add status badge placeholders to plant cards"
```

---

## Task 8: Frontend — Lock Icon, Buttons, and JS

**Files:**
- Modify: `index.html` — lock icon in header, "Reguei hoje" buttons, JS block

- [ ] **Step 1: Add button CSS inside the `<style>` block**

Append inside the `<style>` block, after the status badge CSS from Task 7:

```css
    /* Watering button */
    .water-btn {
      display: none;
      width: 100%;
      margin-top: 16px;
      padding: 10px 0;
      background: var(--green-mid);
      color: var(--cream);
      border: none;
      border-radius: 6px;
      font-family: 'DM Sans', sans-serif;
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 1px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .water-btn:hover { background: var(--green-deep); }

    /* Lock icon */
    #lock-icon {
      position: absolute;
      top: 20px; right: 24px;
      font-size: 20px;
      cursor: pointer;
      z-index: 10;
      opacity: 0.7;
      transition: opacity 0.2s;
    }
    #lock-icon:hover { opacity: 1; }
```

- [ ] **Step 2: Add lock icon to the header**

Find `<header>` in `index.html`. After the opening `<header>` tag, add:

```html
  <span id="lock-icon" title="Desbloquear regas">🔒</span>
```

- [ ] **Step 3: Add "Reguei hoje" button to all 7 cards**

Inside each `.card-body` div, add the button as the last child. Do this for all 7 cards:

**Card 1 (hedera) — inside `.card-body`, after `.care-section`:**
```html
      <button class="water-btn">💧 Reguei hoje</button>
```

Repeat the exact same `<button class="water-btn">💧 Reguei hoje</button>` line inside the `.card-body` of cards 2 through 7 (begonia, jiboia, ficus, espada, haworthia, sansevieria).

- [ ] **Step 4: Add the JS block**

Add this script block immediately before the closing `</body>` tag:

```html
<script>
  const SECRET_KEY = 'plant_secret';
  const STATUS_LABELS = {
    ok: 'Em dia',
    due_soon: 'Em breve',
    overdue: 'Atrasada',
    never: 'Nunca regada',
  };

  function isUnlocked() {
    return !!localStorage.getItem(SECRET_KEY);
  }

  function updateLockUI() {
    const icon = document.getElementById('lock-icon');
    const buttons = document.querySelectorAll('.water-btn');
    if (isUnlocked()) {
      icon.textContent = '🔓';
      buttons.forEach(b => b.style.display = 'block');
    } else {
      icon.textContent = '🔒';
      buttons.forEach(b => b.style.display = 'none');
    }
  }

  async function loadWaterings() {
    try {
      const res = await fetch('/api/waterings');
      const data = await res.json();
      data.forEach(({ plant_id, status }) => {
        const card = document.querySelector(`[data-plant-id="${plant_id}"]`);
        if (!card) return;
        const badge = card.querySelector('.status-badge');
        badge.className = `status-badge status-${status}`;
        badge.textContent = STATUS_LABELS[status] || status;
      });
    } catch {
      document.querySelectorAll('.status-badge').forEach(b => {
        b.className = 'status-badge status-never';
        b.textContent = 'Sem ligação';
      });
    }
  }

  document.getElementById('lock-icon').addEventListener('click', () => {
    if (isUnlocked()) {
      localStorage.removeItem(SECRET_KEY);
    } else {
      const secret = prompt('Palavra-passe:');
      if (secret) localStorage.setItem(SECRET_KEY, secret);
    }
    updateLockUI();
  });

  document.querySelectorAll('.water-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const plantId = btn.closest('[data-plant-id]').dataset.plantId;
      const secret = localStorage.getItem(SECRET_KEY);
      try {
        const res = await fetch(`/api/water/${plantId}`, {
          method: 'POST',
          headers: { 'X-App-Secret': secret },
        });
        if (res.status === 401) {
          localStorage.removeItem(SECRET_KEY);
          updateLockUI();
          alert('Palavra-passe incorreta.');
          return;
        }
        loadWaterings();
      } catch {
        alert('Não foi possível registar a rega.');
      }
    });
  });

  loadWaterings();
  updateLockUI();
</script>
```

- [ ] **Step 5: Full end-to-end test in browser**

Run `uv run uvicorn main:app --reload` and open `http://localhost:8000`.

1. All cards should show grey "Nunca regada" badges.
2. Click the 🔒 icon → prompt for password → enter the value from your `.env` `APP_SECRET`.
3. Icon becomes 🔓, "Reguei hoje" buttons appear on all cards.
4. Click "Reguei hoje" on one card → badge turns green and shows "Em dia".
5. Click the 🔓 icon → icon returns to 🔒, buttons disappear.
6. Refresh the page → badges still reflect the logged watering (data persisted in SQLite).
7. Enter a wrong password → click a button → alert appears, page locks.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat: watering tracker UI — lock icon, buttons, status badges"
```

---

## Task 9: Railway Deployment

**Files:**
- Create: `railway.toml`

- [ ] **Step 1: Create `railway.toml`**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/waterings"
healthcheckTimeout = 300
```

- [ ] **Step 2: Commit**

```bash
git add railway.toml
git commit -m "chore: add Railway deployment config"
```

- [ ] **Step 3: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 4: Deploy on Railway (one-time dashboard setup)**

1. Go to [railway.app](https://railway.app) and create a new project.
2. Choose **Deploy from GitHub repo** → select `plant-care`.
3. Railway auto-detects `railway.toml` and deploys.
4. In the project settings, go to **Variables** and add:
   - `APP_SECRET` = your chosen password
   - `DB_PATH` = `/data/waterings.db`
5. In the project settings, go to **Volumes** → **Add Volume** → mount path: `/data`.
6. Railway will redeploy automatically. Open the generated `.up.railway.app` URL and verify the page loads and watering logging works.

From this point, every push to `main` triggers an automatic redeploy. The SQLite file on the `/data` volume is unaffected by redeploys.
