from fastapi.testclient import TestClient

from app import main


def test_core_api_starts_and_serves_health(monkeypatch):
    monkeypatch.setattr(main, "check_db_connection", lambda: True)

    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_core_api_registers_job_routes():
    paths = main.app.openapi()["paths"]

    assert "post" in paths["/api/v1/jobs"]
