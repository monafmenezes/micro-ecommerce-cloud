from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_create_and_list_orders():
    response = client.post("/orders", json={"customer": "Ana"})
    assert response.status_code == 201
    data = response.json()
    assert data["customer"] == "Ana"
    assert data["status"] == "open"

    response = client.get("/orders")
    assert response.status_code == 200
    assert any(o["customer"] == "Ana" for o in response.json())
