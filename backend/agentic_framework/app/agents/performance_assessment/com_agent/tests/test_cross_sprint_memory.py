"""Tests for cross-sprint memory and cohort baseline calculator (T2.5)."""

import pytest
from app.agents.performance_assessment.com_agent.state import CohortBaseline
from app.agents.performance_assessment.com_agent.ingestion.cohort_baseline import (
    compute_current_sprint_raw_baseline,
    load_historical_baselines,
    compute_rolling_average_baseline,
    save_sprint_baseline,
)


def test_compute_current_sprint_raw_baseline_with_commits():
    commits_by_student = {
        "STU-001": [
            {
                "sha": "c1",
                "stats": {"additions": 100, "deletions": 20},
                "files": ["a.py", "b.py"],
            },
            {
                "sha": "c2",
                "stats": {"additions": 50, "deletions": 10},
                "files": ["c.py"],
            },
        ],
        "STU-002": [
            {
                "sha": "c3",
                "stats": {"additions": 60, "deletions": 10},
                "files": ["d.py"],
            }
        ],
    }

    baseline = compute_current_sprint_raw_baseline(commits_by_student)

    assert baseline["student_count"] == 2
    means = baseline["metric_means"]
    stds = baseline["metric_stds"]

    # STU-001: cc=2, loc_net=120, fc=3
    # STU-002: cc=1, loc_net=50, fc=1
    # Means: cc=(2+1)/2 = 1.5, loc_net=(120+50)/2 = 85.0, fc=(3+1)/2 = 2.0
    assert means["cc"] == 1.5
    assert means["loc_net"] == 85.0
    assert means["fc"] == 2.0

    # STDs should be > 0.0
    assert stds["cc"] > 0.0
    assert stds["loc_net"] > 0.0
    assert stds["fc"] > 0.0


def test_compute_current_sprint_raw_baseline_empty():
    baseline = compute_current_sprint_raw_baseline({})
    assert baseline["student_count"] == 0
    assert baseline["metric_means"] == {}
    assert baseline["metric_stds"] == {}


def test_load_historical_baselines_sprint_1_empty():
    store = {}
    history = load_historical_baselines(store, team_id="TEAM-A")
    assert history == []

    none_history = load_historical_baselines(None, team_id="TEAM-A")
    assert none_history == []


def test_save_and_load_historical_baselines_dict_store():
    store = {}
    team_id = "TEAM-01"

    # Sprint 1
    raw_sprint1 = {
        "metric_means": {"cc": 10.0, "loc_net": 300.0},
        "metric_stds": {"cc": 2.0, "loc_net": 50.0},
        "student_count": 4,
    }
    save_sprint_baseline(store, team_id, "sprint-01", raw_sprint1)

    history = load_historical_baselines(store, team_id)
    assert len(history) == 1
    assert history[0]["sprint_id"] == "sprint-01"
    assert history[0]["metric_means"]["cc"] == 10.0

    # Sprint 2
    raw_sprint2 = {
        "metric_means": {"cc": 14.0, "loc_net": 400.0},
        "metric_stds": {"cc": 3.0, "loc_net": 60.0},
        "student_count": 4,
    }
    save_sprint_baseline(store, team_id, "sprint-02", raw_sprint2)

    history2 = load_historical_baselines(store, team_id)
    assert len(history2) == 2
    assert [h["sprint_id"] for h in history2] == ["sprint-01", "sprint-02"]


def test_compute_rolling_average_baseline():
    historical = [
        {
            "sprint_id": "sprint-01",
            "metric_means": {"cc": 10.0, "loc_net": 200.0},
            "metric_stds": {"cc": 2.0, "loc_net": 40.0},
        },
        {
            "sprint_id": "sprint-02",
            "metric_means": {"cc": 14.0, "loc_net": 300.0},
            "metric_stds": {"cc": 3.0, "loc_net": 50.0},
        },
    ]

    current = {
        "sprint_id": "sprint-03",
        "metric_means": {"cc": 12.0, "loc_net": 250.0},
        "metric_stds": {"cc": 2.5, "loc_net": 45.0},
        "student_count": 5,
    }

    rolling = compute_rolling_average_baseline(historical, current)

    assert isinstance(rolling, CohortBaseline)
    assert rolling.sprint_count_used == 3
    assert rolling.student_count == 5

    # Mean of cc: (10 + 14 + 12) / 3 = 12.0
    assert rolling.metric_means["cc"] == 12.0
    # Mean of loc_net: (200 + 300 + 250) / 3 = 250.0
    assert rolling.metric_means["loc_net"] == 250.0


def test_save_and_load_with_mock_store_object():
    class MockStoreItem:
        def __init__(self, value):
            self.value = value

    class MockBaseStore:
        def __init__(self):
            self.storage = {}

        def get(self, namespace, key):
            stored = self.storage.get((namespace, key))
            return MockStoreItem(stored) if stored is not None else None

        def put(self, namespace, key, value):
            self.storage[(namespace, key)] = value

    store = MockBaseStore()
    team_id = "TEAM-B"

    # Sprint 1
    raw = {
        "metric_means": {"cc": 5.0},
        "metric_stds": {"cc": 1.0},
        "student_count": 3,
    }
    save_sprint_baseline(store, team_id, "sprint-01", raw)

    history = load_historical_baselines(store, team_id)
    assert len(history) == 1
    assert history[0]["sprint_id"] == "sprint-01"
    assert history[0]["metric_means"]["cc"] == 5.0


@pytest.mark.asyncio
async def test_historical_trajectory_rendered_in_explanation_prompt():
    """T8.6.3: historical_trajectory values visible in rendered explanation prompt."""
    from app.agents.performance_assessment.com_agent.nodes.explanation_node import generate_explanation_node

    captured = []
    def mock_llm(sys_p, usr_p, cfg):
        captured.append(usr_p)
        return "Report content"

    trajectory = [
        {"sprint_id": "sprint-01", "final_score": 0.75, "behavioral_persona": "Steady Contributor"},
        {"sprint_id": "sprint-02", "final_score": 0.82, "behavioral_persona": "High Performer"},
    ]

    state = {
        "student_name": "Alice Perera",
        "student_id": "STU-001",
        "sprint_id": "sprint-03",
        "factor_scores": {},
        "final_score": 0.88,
        "historical_trajectory": trajectory,
    }

    await generate_explanation_node(state, llm_callable=mock_llm)
    assert len(captured) == 2

    # Check both prompts received formatted trajectory
    for prompt_text in captured:
        assert "sprint-01" in prompt_text
        assert "0.75" in prompt_text
        assert "sprint-02" in prompt_text
        assert "0.82" in prompt_text

