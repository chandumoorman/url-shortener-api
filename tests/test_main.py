# tests/test_main.py
# Tests run against an in-memory SQLite DB — completely isolated from your real DB.
# TestClient simulates HTTP requests without running the actual server.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, get_db
from database import Base

# In-memory SQLite for tests — wiped clean after every test session
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the real get_db with a test version pointing to test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables before each test, drop after — clean slate every time
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_shorten_url():
    response = client.post("/shorten", json={"original_url": "https://www.google.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert len(data["short_code"]) == 6
    assert data["click_count"] == 0


def test_shorten_same_url_twice_returns_same_code():
    # Idempotency test — same URL should return same short code
    r1 = client.post("/shorten", json={"original_url": "https://www.github.com"})
    r2 = client.post("/shorten", json={"original_url": "https://www.github.com"})
    assert r1.json()["short_code"] == r2.json()["short_code"]


def test_redirect():
    # Create a short URL first
    create_resp = client.post("/shorten", json={"original_url": "https://www.python.org"})
    short_code = create_resp.json()["short_code"]

    # follow_redirects=False lets us inspect the redirect response itself
    redirect_resp = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 307
    assert redirect_resp.headers["location"] == "https://www.python.org"


def test_redirect_increments_click_count():
    create_resp = client.post("/shorten", json={"original_url": "https://www.fastapi.tiangolo.com"})
    short_code = create_resp.json()["short_code"]

    client.get(f"/{short_code}", follow_redirects=False)
    client.get(f"/{short_code}", follow_redirects=False)

    stats = client.get(f"/stats/{short_code}")
    assert stats.json()["click_count"] == 2


def test_redirect_not_found():
    response = client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404


def test_invalid_url_rejected():
    # Pydantic should reject this before it even hits your route code
    response = client.post("/shorten", json={"original_url": "not-a-url"})
    assert response.status_code == 422


def test_delete_url():
    create_resp = client.post("/shorten", json={"original_url": "https://www.example.com"})
    short_code = create_resp.json()["short_code"]

    delete_resp = client.delete(f"/{short_code}")
    assert delete_resp.status_code == 200

    # Confirm it's gone
    get_resp = client.get(f"/{short_code}", follow_redirects=False)
    assert get_resp.status_code == 404