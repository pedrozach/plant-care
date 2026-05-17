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
