import requests

BASE_URL = "http://localhost:8000"

def test_healthcheck():
    resp = requests.get(f"{BASE_URL}/healthcheck")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_characters_endpoint():
    resp = requests.get(f"{BASE_URL}/characters?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data