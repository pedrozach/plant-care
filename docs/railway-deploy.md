# Deploying to Railway

This document explains how this project is configured to run on [Railway](https://railway.app) and how each piece works.

---

## What is Railway?

Railway is a hosting platform that takes your code from GitHub and runs it on a server in the cloud. You don't have to configure Linux, Docker, or any infrastructure manually — Railway detects what kind of project you have and figures out how to build and start it.

---

## What was added to make this work

Only two things were added to the project specifically for Railway:

### 1. `railway.toml`

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uv run uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/waterings"
healthcheckTimeout = 300
```

This file tells Railway:

| Setting | What it does |
|---|---|
| `builder = "nixpacks"` | Use Nixpacks to auto-detect the language and install dependencies. It reads `pyproject.toml` and installs everything with `uv`. |
| `startCommand` | The shell command Railway runs to start the server after the build is done. |
| `--host 0.0.0.0` | Makes the server listen on all network interfaces, not just `localhost`. Required so Railway's infrastructure can reach the process. |
| `--port $PORT` | Railway injects the `$PORT` environment variable automatically. The app must listen on that port, not a hardcoded one. |
| `healthcheckPath` | Railway calls this URL after deploy to verify the app is running. If it returns a non-2xx response, the deploy is marked as failed. |
| `healthcheckTimeout` | How many seconds Railway waits for the health check before giving up (useful while the database is initializing). |

### 2. Environment variables set in the Railway dashboard

The app reads two variables from the environment:

| Variable | Purpose | Where to set it |
|---|---|---|
| `APP_SECRET` | A secret token required to call `POST /api/water/:id`. Without it, the endpoint rejects all requests. | Railway dashboard → Variables tab |
| `DB_PATH` | Path to the SQLite database file. Defaults to `data/waterings.db` if not set. | Optional; Railway sets it only if you want to override the default. |

These are never committed to git — `.env` is in `.gitignore`. The `.env.example` file shows which variables are needed so anyone cloning the repo knows what to create.

---

## How the build works step by step

```
GitHub push
    │
    ▼
Railway detects pyproject.toml
    │
    ▼
Nixpacks installs uv, then runs: uv sync
    │ (installs fastapi, uvicorn, python-dotenv)
    ▼
Railway runs: uv run uvicorn main:app --host 0.0.0.0 --port $PORT
    │
    ▼
FastAPI starts → init_db() creates the SQLite table if missing
    │
    ▼
Railway hits GET /api/waterings → 200 OK → deploy succeeds
```

---

## Why `uv run uvicorn` instead of just `uvicorn`?

When Railway builds with Nixpacks, `uv` manages the virtual environment inside the container. The `uvicorn` binary lives inside that venv and may not be on the system `PATH` by default. Using `uv run uvicorn` tells `uv` to activate the venv and run `uvicorn` from inside it, which always resolves correctly regardless of where Railway puts the venv.

---

## Limitations of this setup

- **SQLite on Railway is not persistent by default.** Railway's filesystem is ephemeral — if the container restarts, the database file is lost. For a real production app you would use a Railway Postgres plugin or mount a persistent volume. For a demo or student project, SQLite is fine.
- **Single instance only.** SQLite does not support concurrent writes from multiple processes, so this setup should not be scaled to more than one Railway replica.

---

## How to deploy your own copy

1. Fork or clone this repo and push it to your GitHub account.
2. Go to [railway.app](https://railway.app), create a new project, and connect your GitHub repo.
3. In the Railway dashboard, open the **Variables** tab and add:
   - `APP_SECRET` — any secret string you choose
4. Railway will build and deploy automatically. Every subsequent push to `main` triggers a new deploy.
