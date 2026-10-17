"""The orchestration endpoint is only for the Core API: it needs the shared secret."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

URL = "/api/v1/orchestration"
VALID_REQUEST = {
    "request_id": "req-001",
    "requester": {"user_id": "kc-123", "role": "student"},
    "action": "tutor.chat",
    "student_id": "ST001",
    "group_id": "G01",
    "project_id": "P-01",
    "context": {"project": {"project_id": "P-01", "title": "Online Food Ordering System"}},
    "input": {"message": "Explain JWT"},
}
TOKEN = "test-internal-token"


@pytest.fixture
def bare_client():
    with TestClient(app) as client:
        yield client


def test_missing_token_is_rejected(bare_client, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", TOKEN)

    assert bare_client.post(URL, json=VALID_REQUEST).status_code == 401


def test_wrong_token_is_rejected(bare_client, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", TOKEN)

    response = bare_client.post(URL, json=VALID_REQUEST, headers={"X-Internal-Token": "nope"})

    assert response.status_code == 401


def test_unconfigured_service_refuses_everything(bare_client, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", None)

    response = bare_client.post(URL, json=VALID_REQUEST, headers={"X-Internal-Token": TOKEN})

    assert response.status_code == 503


def test_user_role_in_the_body_does_not_bypass_the_token(bare_client, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", TOKEN)
    forged = {**VALID_REQUEST, "requester": {"user_id": "attacker", "role": "admin"}}

    assert bare_client.post(URL, json=forged).status_code == 401


def test_health_stays_public(bare_client):
    assert bare_client.get("/health").status_code == 200
