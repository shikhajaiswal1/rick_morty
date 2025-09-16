from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_healthcheck():
    resp = client.get("/healthcheck")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_characters_endpoint():
    with TestClient(app) as client:  # <-- IMPORTANT
        resp = client.get("/characters?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
