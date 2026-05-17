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
    from main import app
    with TestClient(app) as c:
        yield c
