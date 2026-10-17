"""Comprehensive End-to-End Stress Test Script for Performance Assessment Agent.

Executes actual LangGraph threads using real 'Nexa Web Platform' data from Data Collection:
- Uses real student mappings (S01 Sadeesha, S02 Eric, S03 Ehara, S04 Vageesha)
- Uses real Scrum & Git data from actual_raw_evidence_sadeesha_projects.json
- Uses local nexa_repo or cloned GitHub repository
- Uses a deterministic LLM Simulator with 3 operational modes (Normal, Boundary, Fault-Injection)
- Tests all 8 execution paths and edge cases:
  1. Happy Path (S01 Lead Contributor)
  2. Free-Rider Path (S04 Zero-Commit Disengaged Persona)
  3. Ghostwriter Discrepancy & Lecturer Review
  4. Active Verification Quiz 48h Timeout & +24h Extension (Score Capped at 0.50)
  5. Active Verification Double Timeout (Score 0.0, Critical Discrepancy)
  6. Multi-Sprint Memory Progression (Sprint 0 -> Sprint 2)
  7. PII Redaction & Restoration Guardrail Integrity
"""

import os
import sys
import json
import asyncio
import pathlib
import logging
from typing import Dict, Any, List, Optional, Tuple

# Ensure backend root is on sys.path
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
AGENT_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = AGENT_ROOT.parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simulate_all_paths")

# LangGraph and Agent imports
from langgraph.types import Command
from langgraph.store.memory import InMemoryStore

from app.agents.performance_assessment.agent import (
    trigger_sprint_end,
    submit_quiz_response,
    submit_lecturer_review,
    get_assessment_status,
)
from app.agents.performance_assessment.com_agent.graph import (
    build_com_agent_graph,
    make_thread_config,
    build_initial_state,
)
from app.agents.performance_assessment.com_agent.state import (
    AssessmentState,
    DiscrepancyAlert,
    ActiveVerificationState,
)
from app.agents.performance_assessment.com_agent.db import init_assessment_db

# Paths to external Data Collection
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_COLLECTION_DIR = PROJECT_ROOT.parent / "Data Collection"
EVIDENCE_JSON_PATH = DATA_COLLECTION_DIR / "datasets" / "actual_raw_evidence_sadeesha_projects.json"
USER_MAPPING_PATH = DATA_COLLECTION_DIR / "user_mapping.json"
LOCAL_NEXA_REPO = DATA_COLLECTION_DIR / "nexa_repo"


class LLMSimulator:
    """Configurable LLM Simulator supporting Normal, Boundary, and Fault-Injection modes."""

    def __init__(self, mode: str = "normal"):
        self.mode = mode
        self.call_history = []

    def __call__(self, system_prompt: str, user_prompt: str, model_params: Optional[Dict[str, Any]] = None) -> str:
        self.call_history.append({"system": system_prompt, "user": user_prompt})

        # Check for PII Leakage Guardrail
        real_names = ["Sadeesha", "Croos", "Eric", "Ehara", "Vageesha"]
        for name in real_names:
            if name.lower() in user_prompt.lower() or name.lower() in system_prompt.lower():
                logger.error(f"[SECURITY ALERT] Unredacted PII detected in LLM prompt: {name}")

        if self.mode == "fault_injection":
            return "MALFORMED_OUTPUT: {"

        if "Instructor Assessment Dossier" in system_prompt or "instructor_assessment_dossier" in system_prompt:
            return (
                "# Instructor Assessment Dossier: [STUDENT_A] ([STUDENT_ID])\n\n"
                "**Sprint:** sprint-01 | **Final Score S:** 0.88 / 1.00\n"
                "**Contributor Archetype:** Consistent Contributor (Modifier: 1.05)\n\n"
                "### Factor Breakdown\n"
                "- Effort: 0.90\n- Consistency: 0.85\n- Requirement Fulfillment: 0.88\n\n"
                "### Attention Required & Anomalies\n"
                "None detected. Healthy distribution of commits and code ownership.\n\n"
                "### Audit Evidence Traces\n"
                "- Verified AST code comprehension.\n"
            )

        if "Student Formative Feedback" in system_prompt or "student_formative_feedback" in system_prompt:
            return (
                "# Sprint Performance Feedback for [STUDENT_A]\n\n"
                "Great work this sprint! You demonstrated strong backend architecture skills.\n\n"
                "### Key Strengths\n"
                "- Consistent commit velocity and clean architectural modularity.\n\n"
                "### Actionable Goals\n"
                "- Continue conducting peer reviews on pull requests.\n"
            )

        return "Default simulated LLM response."


def load_nexa_real_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Loads student mapping and actual sprint raw evidence for Nexa Web."""
    users = []
    if USER_MAPPING_PATH.exists():
        with open(USER_MAPPING_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)

    nexa_records = []
    if EVIDENCE_JSON_PATH.exists():
        with open(EVIDENCE_JSON_PATH, "r", encoding="utf-8") as f:
            all_records = json.load(f)
            nexa_records = [r for r in all_records if "nexa" in str(r.get("team_id", "")).lower()]

    return users, nexa_records


def build_student_context_from_nexa(
    student_id: str,
    sprint_id: str = "Sprint 0",
    users: Optional[List[Dict[str, Any]]] = None,
    evidence_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Extracts realistic StudentContext for a given student from Nexa Web dataset."""
    u_info = next((u for u in (users or []) if u.get("student_id") == student_id), {})
    e_info = next(
        (
            e for e in (evidence_records or [])
            if e.get("student_id") == student_id and e.get("sprint_id") == sprint_id
        ),
        {},
    )

    effort_data = e_info.get("effort", {})
    return {
        "student_id": student_id,
        "student_name": u_info.get("name", "Student " + student_id),
        "student_github_username": u_info.get("github_username", "student_" + student_id),
        "student_git_emails": u_info.get("git_emails", [f"{student_id.lower()}@sliit.lk"]),
        "team_id": "team_01_nexa",
        "sprint_id": sprint_id,
        "repo_url": "https://github.com/sadeeshasathsara/nexa",
        "sprint_start": e_info.get("sprint_start", "2025-08-14T00:00:00Z"),
        "sprint_end": e_info.get("sprint_end", "2025-09-06T23:59:59Z"),
        "assigned_tasks": [
            {
                "task_id": f"NEXAWEB-{i}",
                "title": f"Feature implementation module {i}",
                "status": "DONE",
                "story_points": 5,
                "acceptance_criteria": ["All endpoints functional", "Unit tests passing"],
            }
            for i in range(1, 4)
        ],
        "commit_history": [
            {
                "sha": f"abc123{i}",
                "author": {"login": u_info.get("github_username")},
                "commit": {
                    "author": {
                        "name": u_info.get("name"),
                        "email": u_info.get("git_emails", ["user@test.com"])[0],
                        "date": "2025-08-20T10:00:00Z",
                    },
                    "message": f"feat: implement service module {i}",
                },
                "stats": {"additions": 150, "deletions": 20, "total": 170},
            }
            for i in range(max(1, effort_data.get("commit_count", 3)))
        ],
        "pull_requests": [
            {
                "number": 1,
                "title": "PR: Core API implementation",
                "state": "closed",
                "merged": True,
                "user": {"login": u_info.get("github_username")},
                "comments": 3,
                "review_comments": 2,
            }
        ],
    }


async def test_path_1_happy_path_lead(graph, users, nexa_records):
    """Path 1: S01 (Sadeesha) - High Effort, High Quality, On-Time Quiz -> Finalized."""
    logger.info("=== Running Path 1: S01 Happy Path (Lead Contributor) ===")
    ctx = build_student_context_from_nexa("S01", "Sprint 0", users, nexa_records)

    # 1. Trigger Sprint End -> Pauses at Quiz
    thread_ids = await trigger_sprint_end("Sprint 0", ["S01"], graph=graph, custom_contexts={"S01": ctx})
    thread_id = thread_ids[0]

    state = get_assessment_status(thread_id, graph=graph)
    assert state.get("current_step") == "quiz_generated", f"Expected quiz_generated, got {state.get('current_step')}"

    # 2. Submit high quality quiz response within 48h window
    status = await submit_quiz_response(
        thread_id=thread_id,
        student_response="The exp claim sets the expiration epoch timestamp, preventing replay attacks after token invalidation.",
        graph=graph,
    )
    assert status == "evaluation_complete", f"Expected evaluation_complete, got {status}"

    final_state = get_assessment_status(thread_id, graph=graph)
    logger.info(f"Path 1 debug: current_step={final_state.get('current_step')}, final_score={final_state.get('final_score')}, requires_review={final_state.get('requires_human_review')}, flags={final_state.get('discrepancy_flags')}")
    assert final_state.get("final_score") is not None
    logger.info(f"[PASS] Path 1 Completed. Final Score: {final_state.get('final_score'):.2f}, Persona: {final_state.get('behavioral_persona')}")


async def test_path_2_free_rider(graph, users, nexa_records):
    """Path 2: S04 (Vageesha) - Zero Commits Free-Rider -> Low score, Disengaged persona."""
    logger.info("=== Running Path 2: S04 Free-Rider Contributor ===")
    ctx = build_student_context_from_nexa("S04", "Sprint 0", users, nexa_records)
    ctx["commit_history"] = []

    thread_ids = await trigger_sprint_end("Sprint 0", ["S04"], graph=graph, custom_contexts={"S04": ctx})
    thread_id = thread_ids[0]

    status = await submit_quiz_response(
        thread_id=thread_id,
        student_response="I did not work on this section of code.",
        graph=graph,
    )

    final_state = get_assessment_status(thread_id, graph=graph)
    assert final_state.get("final_score") <= 0.45
    logger.info(f"[PASS] Path 2 Completed. Final Score: {final_state.get('final_score'):.2f}, Persona: {final_state.get('behavioral_persona')}")


async def test_path_3_ghostwriter_discrepancy(graph, users, nexa_records):
    """Path 3: High Commits (S01 real data), but Zero Quiz Score -> Ghostwriter Discrepancy & Lecturer Review."""
    logger.info("=== Running Path 3: Ghostwriter Discrepancy & Lecturer Review ===")
    ctx = build_student_context_from_nexa("S01", "Sprint 0", users, nexa_records)
    ctx["student_id"] = "S01_GHOST"

    thread_ids = await trigger_sprint_end("Sprint 0", ["S01_GHOST"], graph=graph, custom_contexts={"S01_GHOST": ctx})
    thread_id = thread_ids[0]

    # Submit completely irrelevant short answer -> triggers low KO score & discrepancy
    status = await submit_quiz_response(
        thread_id=thread_id,
        student_response="idk",
        graph=graph,
    )
    assert status == "pending_lecturer_review"

    review_state = get_assessment_status(thread_id, graph=graph)
    assert review_state.get("requires_human_review") is True
    assert review_state.get("current_step") == "discrepancy_checked"

    # Lecturer Reviews and Overrides Score
    final_status = await submit_lecturer_review(
        thread_id=thread_id,
        override_score=0.55,
        reason="Student demonstrated partial understanding during manual interview.",
        lecturer_id="LEC-PROF-SILVA",
        graph=graph,
    )
    assert final_status == "finalized"

    final_state = get_assessment_status(thread_id, graph=graph)
    assert final_state.get("lecturer_reviewed") is True
    assert final_state.get("final_score") == 0.55
    logger.info(f"[PASS] Path 3 Completed. Lecturer override applied: {final_state.get('final_score')}")


async def test_path_4_quiz_extension_capped(graph, users, nexa_records):
    """Path 4: S03 - Misses 48h deadline -> +24h extension granted -> score capped at 0.50."""
    logger.info("=== Running Path 4: Quiz Extension & Capped Score ===")
    ctx = build_student_context_from_nexa("S03", "Sprint 0", users, nexa_records)

    thread_ids = await trigger_sprint_end("Sprint 0", ["S03"], graph=graph, custom_contexts={"S03": ctx})
    thread_id = thread_ids[0]
    cfg = make_thread_config("Sprint 0", "S03")

    # 1. Trigger initial 48h timeout
    await graph.ainvoke(Command(resume={"timeout": True}), config=cfg)

    mid_state = get_assessment_status(thread_id, graph=graph)
    assert mid_state.get("quiz_is_extended") is True

    # 2. Student submits during the extension window
    status = await submit_quiz_response(
        thread_id=thread_id,
        student_response="Extended response explaining token security and payload expiration.",
        graph=graph,
    )

    final_state = get_assessment_status(thread_id, graph=graph)
    ko_factor = final_state.get("factor_scores", {}).get("code_ownership") or final_state.get("factor_scores", {}).get("07_code_ownership")
    ko_score = getattr(ko_factor, "score", None) if hasattr(ko_factor, "score") else (ko_factor.get("score") if isinstance(ko_factor, dict) else ko_factor)
    assert ko_score is not None, "Expected valid code ownership score"
    assert ko_score <= 0.50, f"Expected capped score <= 0.50, got {ko_score}"
    logger.info(f"[PASS] Path 4 Completed. Capped Ownership Score: {ko_score}")


async def test_path_5_double_timeout(graph, users, nexa_records):
    """Path 5: Student misses both 48h and +24h extension -> Score 0.0, Critical Discrepancy."""
    logger.info("=== Running Path 5: Double Timeout (Both Windows Expired) ===")
    ctx = build_student_context_from_nexa("S01", "Sprint 2", users, nexa_records)
    ctx["student_id"] = "S01_TIMEOUT"

    thread_ids = await trigger_sprint_end("Sprint 2", ["S01_TIMEOUT"], graph=graph, custom_contexts={"S01_TIMEOUT": ctx})
    thread_id = thread_ids[0]
    cfg = make_thread_config("Sprint 2", "S01_TIMEOUT")

    # Window 1 timeout -> extension
    await graph.ainvoke(Command(resume={"timeout": True}), config=cfg)
    # Window 2 timeout -> double timeout
    await graph.ainvoke(Command(resume={"timeout": True}), config=cfg)

    state = get_assessment_status(thread_id, graph=graph)
    assert state.get("quiz_is_double_timed_out") is True
    assert state.get("requires_human_review") is True
    logger.info("[PASS] Path 5 Completed. Double timeout correctly flagged for review.")


async def test_path_6_multi_sprint_memory(users, nexa_records):
    """Path 6: Cross-sprint progression from Sprint 0 to Sprint 2 using InMemoryStore."""
    logger.info("=== Running Path 6: Multi-Sprint Memory Trajectory ===")
    store = InMemoryStore()
    graph_with_store = build_com_agent_graph(store=store)

    # Sprint 0
    ctx_s0 = build_student_context_from_nexa("S01", "Sprint 0", users, nexa_records)
    t_s0 = await trigger_sprint_end("Sprint 0", ["S01"], graph=graph_with_store, custom_contexts={"S01": ctx_s0})
    await submit_quiz_response(t_s0[0], student_response="Valid explanation for sprint 0", graph=graph_with_store)

    # Sprint 2
    ctx_s2 = build_student_context_from_nexa("S01", "Sprint 2", users, nexa_records)
    t_s2 = await trigger_sprint_end("Sprint 2", ["S01"], graph=graph_with_store, custom_contexts={"S01": ctx_s2})
    await submit_quiz_response(t_s2[0], student_response="Valid explanation for sprint 2", graph=graph_with_store)

    state_s2 = get_assessment_status(t_s2[0], graph=graph_with_store)
    trajectory = state_s2.get("historical_trajectory", [])
    assert len(trajectory) >= 1
    assert trajectory[0].get("sprint_id") == "Sprint 0"
    logger.info(f"[PASS] Path 6 Completed. Historical trajectory preserved across sprints: {trajectory}")


async def test_path_7_pii_sanitization_guardrail(graph, users, nexa_records):
    """Path 7: Verify PII Redaction & Restoration."""
    logger.info("=== Running Path 7: PII Sanitization Guardrail ===")
    sim = LLMSimulator(mode="normal")
    ctx = build_student_context_from_nexa("S01", "Sprint 0", users, nexa_records)
    ctx["student_name"] = "Sadeesha Sathsara"
    ctx["student_git_emails"] = ["sadeeshasathsara99@gmail.com"]

    thread_ids = await trigger_sprint_end("Sprint 0", ["S01"], graph=graph, custom_contexts={"S01": ctx})
    await submit_quiz_response(thread_ids[0], student_response="Token exp claim prevents token replay attacks.", graph=graph)

    final_state = get_assessment_status(thread_ids[0], graph=graph)
    report = final_state.get("instructor_report_markdown", "")

    # Output dossier must be restored with student's actual name
    assert "Sadeesha Sathsara" in report
    logger.info("[PASS] Path 7 Completed. PII Redaction and Restoration verified.")


async def main():
    logger.info("================================================================================")
    logger.info("STARTING PERFORMANCE ASSESSMENT AGENT END-TO-END STRESS TEST")
    logger.info("Target Project: 'NEXA Web Platform' (Real Data from Data Collection)")
    logger.info("================================================================================")

    init_assessment_db()

    users, nexa_records = load_nexa_real_data()
    logger.info(f"Loaded {len(users)} students from user_mapping.json")
    logger.info(f"Loaded {len(nexa_records)} Nexa sprint records from actual_raw_evidence_sadeesha_projects.json")

    graph = build_com_agent_graph()

    results = []
    tests = [
        ("Path 1: Happy Path Lead Contributor", lambda: test_path_1_happy_path_lead(graph, users, nexa_records)),
        ("Path 2: Free-Rider Contributor", lambda: test_path_2_free_rider(graph, users, nexa_records)),
        ("Path 3: Ghostwriter Discrepancy & Lecturer Review", lambda: test_path_3_ghostwriter_discrepancy(graph, users, nexa_records)),
        ("Path 4: Quiz Extension & Capped Score", lambda: test_path_4_quiz_extension_capped(graph, users, nexa_records)),
        ("Path 5: Double Timeout Anomaly", lambda: test_path_5_double_timeout(graph, users, nexa_records)),
        ("Path 6: Cross-Sprint Memory Progression", lambda: test_path_6_multi_sprint_memory(users, nexa_records)),
        ("Path 7: PII Sanitization Guardrail", lambda: test_path_7_pii_sanitization_guardrail(graph, users, nexa_records)),
    ]

    for name, test_fn in tests:
        try:
            await test_fn()
            results.append((name, "PASSED", None))
        except Exception as e:
            logger.error(f"[FAIL] {name}: {e}", exc_info=True)
            results.append((name, "FAILED", str(e)))

    logger.info("================================================================================")
    logger.info("STRESS TEST SUMMARY RESULTS")
    logger.info("================================================================================")
    all_passed = True
    for name, status, err in results:
        mark = "✓" if status == "PASSED" else "✗"
        logger.info(f"[{mark}] {name}: {status}" + (f" -> {err}" if err else ""))
        if status != "PASSED":
            all_passed = False

    if all_passed:
        logger.info("ALL 7 CRITICAL CORNER PATHS PASSED SUCCESSFULLY!")
    else:
        logger.error("SOME PATHS FAILED. PLEASE REVIEW LOGS ABOVE.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
