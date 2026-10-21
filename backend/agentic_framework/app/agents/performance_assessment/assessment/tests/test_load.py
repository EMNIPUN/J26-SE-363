"""Many students at one deadline: everything finishes, concurrency stays bounded, memory stays small (scripts/load_test.py runs the same with 250)."""
import pytest

from app.agents.performance_assessment.assessment.loadtest import run_load


@pytest.mark.asyncio
async def test_a_crowd_of_students_is_assessed_within_the_concurrency_limit(tmp_path):
    out = await run_load(students=30, parallel=4, db_latency=0.02, rf_seconds=0.1, work_dir=tmp_path)
    assert out["assessed"] == 30 and out["failed"] == 0 and out["marks_present"] == 30 and out["results_saved"] == 30
    assert 1 < out["max_students_at_once"] <= 4  # parallel, and never more than the limit
    assert out["peak_memory_mb"] < 100
    assert out["events"] > 30 * 20  # every student's steps are in the log
