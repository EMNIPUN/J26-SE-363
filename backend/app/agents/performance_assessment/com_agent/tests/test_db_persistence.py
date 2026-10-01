"""Unit tests for decoupled PostgreSQL layer and standalone server endpoints."""

import os
import pytest
from app.agents.performance_assessment.com_agent.db import (
    get_db_url,
    init_assessment_db,
    get_checkpointer,
    save_assessment_result_db,
    save_student_feedback_db,
    get_assessment_result_db,
    INIT_TABLES_SQL,
)
from app.agents.performance_assessment.com_agent.graph import MemorySaver
from app.agents.performance_assessment.server import app


def test_get_db_url_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5434")
    monkeypatch.setenv("POSTGRES_DB", "assessment_db")
    monkeypatch.setenv("POSTGRES_USER", "assessment_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "assessment_pass")

    url = get_db_url()
    assert url == "postgresql://assessment_user:assessment_pass@localhost:5434/assessment_db"


def test_get_db_url_custom_override(monkeypatch):
    custom = "postgresql://custom:custompass@customhost:5432/customdb"
    monkeypatch.setenv("DATABASE_URL", custom)
    assert get_db_url() == custom


def test_get_checkpointer_dev_mode_returns_memory_saver():
    """In development mode, get_checkpointer must return MemorySaver without connecting to DB."""
    cp = get_checkpointer()
    assert isinstance(cp, MemorySaver)


def test_init_assessment_db_offline_graceful_fallback():
    """Connecting to a non-existent port must return False gracefully without crashing."""
    offline_url = "postgresql://user:pass@127.0.0.1:59999/nonexistent_db"
    success = init_assessment_db(db_url=offline_url)
    assert success is False


def test_save_and_get_assessment_result_db_offline_handling():
    """DB save and query methods return False / None when DB is unavailable."""
    offline_url = "postgresql://user:pass@127.0.0.1:59999/nonexistent_db"
    dummy_data = {
        "student_id": "STU-001",
        "sprint_id": "sprint-01",
        "final_score": 0.85,
    }
    assert save_assessment_result_db(dummy_data, db_url=offline_url) is False
    assert save_student_feedback_db(dummy_data, db_url=offline_url) is False
    assert get_assessment_result_db("STU-001", "sprint-01", db_url=offline_url) is None


def test_init_tables_sql_schema_integrity():
    """Ensure required tables and constraints are defined in SQL schema."""
    assert "CREATE TABLE IF NOT EXISTS assessment_results" in INIT_TABLES_SQL
    assert "CREATE TABLE IF NOT EXISTS student_feedback" in INIT_TABLES_SQL
    assert "CREATE TABLE IF NOT EXISTS cohort_baselines" in INIT_TABLES_SQL
    assert "uq_student_sprint UNIQUE (student_id, sprint_id)" in INIT_TABLES_SQL


def test_server_routes_registered():
    """Verify that all required standalone API endpoints are mounted on the FastAPI app."""
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/api/v1/assessment/triggers/sprint-end" in routes
    assert "/api/v1/assessment/triggers/quiz-response" in routes
    assert "/api/v1/assessment/triggers/on-demand" in routes
    assert "/api/v1/assessment/triggers/lecturer-review" in routes
    assert "/api/v1/assessment/status/{thread_id}" in routes
