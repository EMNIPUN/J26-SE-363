import pytest
from app.tasks.performance_tasks import (
    assess_student,
    parse_rubric,
    generate_ownership_quiz,
    ingest_git_commits,
)
from app.tasks.planning_tasks import (
    estimate_story_points,
    analyze_sprint_velocity,
    assess_backlog_risks,
)
from app.tasks.security_tasks import (
    scan_repository_secrets,
    audit_dependency_vulnerabilities,
    evaluate_code_security_score,
)
from app.tasks.tutor_tasks import (
    generate_guidance,
    explain_code_concept,
    recommend_learning_topics,
)


# =============================================================================
# 1. Performance Agent Tasks (Your Module)
# =============================================================================
@pytest.mark.asyncio
async def test_performance_tasks():
    res1 = await assess_student(payload={"student_id": "IT210001", "sprint_id": "sprint-2"})
    assert res1["final_score"] == 87.5

    res2 = await parse_rubric(payload={"project_id": "P001"})
    assert len(res2["criteria"]) == 4

    res3 = await generate_ownership_quiz(payload={"student_id": "IT210001", "commit_hash": "c1a2"})
    assert len(res3["questions"]) == 1

    res4 = await ingest_git_commits(payload={"student_id": "IT210001", "repo_url": "https://test"})
    assert res4["total_commits"] == 47


# =============================================================================
# 2. Planning Agent Tasks (Teammate A)
# =============================================================================
@pytest.mark.asyncio
async def test_planning_tasks():
    res1 = await estimate_story_points(payload={"user_stories": [{"id": "US1"}, {"id": "US2"}]})
    assert res1["estimated_story_points"] == 34
    assert res1["total_stories"] == 2

    res2 = await analyze_sprint_velocity(payload={"team_id": "team-alpha"})
    assert res2["average_velocity"] == 42.5

    res3 = await assess_backlog_risks(payload={"sprint_id": "sprint-3"})
    assert res3["risk_level"] == "LOW"


# =============================================================================
# 3. Security Agent Tasks (Teammate B)
# =============================================================================
@pytest.mark.asyncio
async def test_security_tasks():
    res1 = await scan_repository_secrets(payload={"repo_url": "https://test"})
    assert res1["is_safe"] is True
    assert res1["leaked_secrets_count"] == 0

    res2 = await audit_dependency_vulnerabilities(payload={"project_id": "P100"})
    assert res2["vulnerabilities_found"] == 0

    res3 = await evaluate_code_security_score(payload={"student_id": "IT210001"})
    assert res3["security_score"] == 96.5


# =============================================================================
# 4. Tutor Agent Tasks (Teammate C)
# =============================================================================
@pytest.mark.asyncio
async def test_tutor_tasks():
    res1 = await generate_guidance(payload={"student_id": "IT210001", "question": "Merge conflict?"})
    assert "tutor_response" in res1

    res2 = await explain_code_concept(payload={"concept": "Factory Pattern"})
    assert "Factory Pattern" in res2["explanation"]

    res3 = await recommend_learning_topics(payload={"student_id": "IT210001"})
    assert len(res3["recommended_modules"]) == 2
