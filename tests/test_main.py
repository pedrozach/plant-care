import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import compute_status


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("APP_SECRET", "secret123")


@pytest.fixture
def client():
    from main import app
    with TestClient(app) as c:
        yield c


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
