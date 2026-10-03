"""Unit tests for non-lossy evidence ingestion, smart dependency detection, and AST evidence tool."""

import pytest
from app.agents.performance_assessment.com_agent.ingestion.evidence_preparer import (
    detect_dependencies_and_clean_loc,
    is_dependency_or_generated_file,
    ASTEvidenceTool,
    prepare_all_factor_payloads,
    ingest_and_pool_evidence,
    clone_or_fetch_team_repo,
)


def test_is_dependency_or_generated_file():
    assert is_dependency_or_generated_file("package-lock.json") is True
    assert is_dependency_or_generated_file("frontend/yarn.lock") is True
    assert is_dependency_or_generated_file("vendor/autoload.php") is True
    assert is_dependency_or_generated_file("node_modules/express/index.js") is True
    assert is_dependency_or_generated_file("assets/app.min.js") is True
    assert is_dependency_or_generated_file("backend/app/auth.py") is False
    assert is_dependency_or_generated_file("services/payment_service.ts") is False


def test_detect_dependencies_and_clean_loc_with_dependencies():
    """Detects lockfiles/dependencies, computes net human LOC vs dependency LOC, and truncates patches."""
    commit_files = [
        {
            "filename": "backend/app/auth.py",
            "additions": 45,
            "deletions": 5,
            "patch": "+def login(): pass\n+def logout(): pass\n-def old_func(): pass",
        },
        {
            "filename": "package-lock.json",
            "additions": 15000,
            "deletions": 0,
            "patch": "+\"name\": \"heavy_package\",\n" * 500,
        },
        {
            "filename": "assets/bundle.min.js",
            "additions": 3500,
            "deletions": 0,
            "patch": "+!function(){var x=1;}();\n",
        },
    ]

    analysis = detect_dependencies_and_clean_loc(commit_files, max_diff_lines=10)

    assert analysis["total_raw_loc"] == 50 + 15000 + 3500
    assert analysis["dependency_loc"] == 18500
    assert analysis["net_human_loc"] == 50
    assert analysis["has_committed_dependencies"] is True
    assert "package-lock.json" in analysis["detected_dependency_files"]
    assert "assets/bundle.min.js" in analysis["detected_dependency_files"]

    # Dependency patches should be cleanly suppressed to avoid DB bloat
    for f in analysis["cleaned_files"]:
        if f["is_dependency"]:
            assert "[DEPENDENCY DIFF SUPPRESSED" in f["patch"]


def test_detect_dependencies_and_clean_loc_human_only():
    """Only human-authored code: zero dependencies detected, full patches preserved."""
    commit_files = [
        {
            "filename": "backend/app/routes.py",
            "additions": 120,
            "deletions": 10,
            "patch": "+@app.get('/items')\n+def get_items(): return []",
        }
    ]

    analysis = detect_dependencies_and_clean_loc(commit_files)
    assert analysis["total_raw_loc"] == 130
    assert analysis["dependency_loc"] == 0
    assert analysis["net_human_loc"] == 130
    assert analysis["has_committed_dependencies"] is False
    assert analysis["detected_dependency_files"] == []


@pytest.mark.asyncio
async def test_ast_evidence_tool_valid_code():
    tool = ASTEvidenceTool()
    raw_bundle = {
        "commits": [
            {
                "sha": "abcdef12",
                "files": [
                    {
                        "filename": "backend/app/service.py",
                        "patch": "+def process_order(order_id, user_id):\n+    if not order_id:\n+        raise ValueError()\n+    return {'status': 'processed'}",
                    }
                ],
            }
        ]
    }

    result = await tool.prepare_evidence(raw_bundle, {"student_id": "STU-001"})
    assert result["has_syntax_errors"] is False
    assert len(result["candidate_snippets"]) == 1
    candidate = result["candidate_snippets"][0]
    assert "process_order" in candidate["functions"]
    assert candidate["cyclomatic_complexity"] >= 2
    assert candidate["has_syntax_error"] is False


@pytest.mark.asyncio
async def test_ast_evidence_tool_incomplete_code_syntax_error_resilience():
    """Broken code at sprint deadline must not crash the tool: flags has_syntax_errors gracefully."""
    tool = ASTEvidenceTool()
    raw_bundle = {
        "commits": [
            {
                "sha": "abcdef34",
                "files": [
                    {
                        "filename": "backend/app/broken.py",
                        "patch": "+def incomplete_function(x, y:\n+    if x >\n+        broken syntax here",
                    }
                ],
            }
        ]
    }

    result = await tool.prepare_evidence(raw_bundle, {"student_id": "STU-001"})
    # Must NOT raise SyntaxError; handled gracefully
    assert result["has_syntax_errors"] is True
    assert len(result["candidate_snippets"]) == 1
    assert result["candidate_snippets"][0]["has_syntax_error"] is True


@pytest.mark.asyncio
async def test_prepare_all_factor_payloads_concurrency():
    """Verifies that all 6 factor payloads are prepared concurrently without missing data."""
    raw_bundle = {
        "commits": [
            {
                "sha": "12345678",
                "commit": {
                    "message": "Implement session validation",
                    "author": {"date": "2025-09-03T10:00:00Z"},
                },
                "files": [
                    {
                        "filename": "backend/app/auth.py",
                        "additions": 40,
                        "deletions": 5,
                        "patch": "+def validate_session(): return True",
                    }
                ],
            }
        ],
        "review_comments": [
            {"id": 1, "body": "Great refactor on the database session pool.", "created_at": "2025-09-04T12:00:00Z"}
        ],
        "issue_comments": [
            {"id": 101, "body": "Checked the docker network configuration.", "created_at": "2025-09-04T14:00:00Z"}
        ],
        "student_tasks": [
            {
                "task_id": "TASK-101",
                "title": "Auth token generator",
                "status": "Done",
                "story_points": 5,
                "acceptance_criteria": ["Return JWT token", "Check expiry"],
                "description": "Implement HMAC session generation",
            }
        ],
    }

    payloads = await prepare_all_factor_payloads(raw_bundle, {"student_id": "STU-001"})

    assert "effort" in payloads
    assert "consistency" in payloads
    assert "requirement_fulfillment" in payloads
    assert "collaboration" in payloads
    assert "task_complexity" in payloads
    assert "code_ownership" in payloads

    # Verify data integrity
    assert payloads["effort"]["commits_count"] == 1
    assert payloads["consistency"]["active_days_count"] == 1
    assert payloads["requirement_fulfillment"]["completed_tasks_count"] == 1
    assert payloads["collaboration"]["pr_reviews_authored"] == 1
    assert payloads["task_complexity"]["total_story_points"] == 5


@pytest.mark.asyncio
async def test_team_level_repo_sandbox_directory(tmp_path):
    """Team-level clone directory is created under team_{team_id}."""
    repo_dir = await clone_or_fetch_team_repo(
        repo_url="https://github.com/mock-org/team-repo",
        team_id="TEAM-A",
        sandbox_base_dir=tmp_path / "sandbox" / "team_TEAM-A",
    )
    assert repo_dir.exists()
    assert "team_TEAM-A" in str(repo_dir)
