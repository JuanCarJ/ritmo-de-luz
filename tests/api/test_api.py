from fastapi.testclient import TestClient

from apps.api.app.main import app


def test_health_and_demo_contract():
    with TestClient(app) as client:
        health = client.get("/health")
        demo = client.get("/api/demo")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert demo.status_code == 200
    assert demo.json()["bands"] == 12

