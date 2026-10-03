"""Unit tests for automated quiz timeout watcher."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.agents.performance_assessment.agent import check_expired_quiz_timeouts
from app.agents.performance_assessment.server import app


@pytest.mark.asyncio
async def test_check_expired_quiz_timeouts_wakes_up_expired_thread():
    """Threads whose quiz deadline is in the past receive Command(resume={'timeout': True})."""
    past_deadline = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    mock_checkpointer = MagicMock()
    mock_checkpointer.storage = {
        "sprint_01_student_STU-001": {
            "current_step": "quiz_generated",
            "quiz_deadline": past_deadline,
            "active_verification": {"quiz_extension_deadline": None},
        }
    }

    mock_graph = AsyncMock()
    mock_graph.checkpointer = mock_checkpointer

    expired = await check_expired_quiz_timeouts(graph=mock_graph)

    assert "sprint_01_student_STU-001" in expired
    assert mock_graph.ainvoke.call_count == 1
    # Check that Command resume={'timeout': True} was sent
    call_args, call_kwargs = mock_graph.ainvoke.call_args
    cmd = call_args[0]
    assert hasattr(cmd, "resume")
    assert cmd.resume == {"timeout": True}


@pytest.mark.asyncio
async def test_check_expired_quiz_timeouts_ignores_active_unexpired_thread():
    """Threads whose quiz deadline is in the future are left alone."""
    future_deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    mock_checkpointer = MagicMock()
    mock_checkpointer.storage = {
        "sprint_01_student_STU-002": {
            "current_step": "quiz_generated",
            "quiz_deadline": future_deadline,
            "active_verification": {"quiz_extension_deadline": None},
        }
    }

    mock_graph = AsyncMock()
    mock_graph.checkpointer = mock_checkpointer

    expired = await check_expired_quiz_timeouts(graph=mock_graph)
    assert expired == []
    assert mock_graph.ainvoke.call_count == 0


def test_server_check_timeouts_route_exists():
    """Verify endpoint is mounted on server."""
    routes = [r.path for r in app.routes]
    assert "/api/v1/assessment/check-timeouts" in routes
