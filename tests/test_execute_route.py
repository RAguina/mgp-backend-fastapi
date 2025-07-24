# tests/test_execute_route.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_post_execute_endpoint():
    response = client.post("/api/v1/execute", json={
        "prompt": "Explica qué es un modelo de lenguaje.",
        "model": "mistral7b",
        "strategy": "optimized"
    })
    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert "prompt" in data
    assert "output" in data
    assert "flow" in data
    assert "metrics" in data
