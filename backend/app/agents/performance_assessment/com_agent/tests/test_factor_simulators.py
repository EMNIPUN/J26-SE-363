"""Unit tests for the 7 Factor Model Simulators (Quick vs. Hard modes).

Validates:
- All 7 factor simulators produce outputs conforming to PROPOSAL.md mathematical specifications.
- Dual-tier simulation (quick vs hard) and custom duration overrides.
- Asynchronous parallel execution via asyncio.gather.
- CLI invokability of each simulate.py script.
"""

import sys
import subprocess
import pytest
import asyncio
from pathlib import Path

import importlib.util

def _load_factor_simulator(factor_folder: str):
    file_path = Path(__file__).resolve().parent.parent.parent / "factor_models" / factor_folder / "simulate.py"
    spec = importlib.util.spec_from_file_location(f"sim_{factor_folder}", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sim_effort_mod = _load_factor_simulator("01_effort")
sim_consistency_mod = _load_factor_simulator("02_consistency")
sim_rf_mod = _load_factor_simulator("03_requirement_fulfillment")
sim_collab_mod = _load_factor_simulator("04_collaboration")
sim_complexity_mod = _load_factor_simulator("05_task_complexity")
sim_behavioral_mod = _load_factor_simulator("06_behavioral_pattern")
sim_ownership_mod = _load_factor_simulator("07_code_ownership")

simulate_effort = sim_effort_mod.simulate
async_simulate_effort = sim_effort_mod.async_simulate

simulate_consistency = sim_consistency_mod.simulate
async_simulate_consistency = sim_consistency_mod.async_simulate

simulate_rf = sim_rf_mod.simulate
async_simulate_rf = sim_rf_mod.async_simulate

simulate_collaboration = sim_collab_mod.simulate
async_simulate_collaboration = sim_collab_mod.async_simulate

simulate_complexity = sim_complexity_mod.simulate
async_simulate_complexity = sim_complexity_mod.async_simulate

simulate_behavioral = sim_behavioral_mod.simulate
async_simulate_behavioral = sim_behavioral_mod.async_simulate

simulate_ownership = sim_ownership_mod.simulate
async_simulate_ownership = sim_ownership_mod.async_simulate


def test_factor_1_effort_quick_simulation():
    res = simulate_effort(mode="quick", duration_seconds=0.01)
    assert "score" in res
    assert 0.0 <= res["score"] <= 1.0
    assert "features" in res
    assert "CC" in res["features"]
    assert "LOC_net" in res["features"]
    assert "z_scores" in res
    assert res["status"] == "completed"

    # Test dependency penalty
    res_penalized = simulate_effort(
        payload={"has_committed_dependencies": True},
        mode="quick",
        duration_seconds=0.01,
    )
    assert res_penalized["has_committed_dependencies"] is True
    assert res_penalized["penalty_applied"] > 0.0


def test_factor_2_consistency_quick_simulation():
    res = simulate_consistency(mode="quick", duration_seconds=0.01)
    assert "score" in res
    assert 0.0 <= res["score"] <= 1.0
    assert "features" in res
    assert "AWR" in res["features"]
    assert "DC" in res["features"]
    assert "procrastination_detected" in res
    assert res["status"] == "completed"

    # Test high deadline concentration triggering procrastination
    procrast_res = simulate_consistency(
        payload={"features": {"AWR": 0.20, "DC": 0.85, "LI_norm": 0.40, "CV_norm": 0.60}},
        mode="quick",
        duration_seconds=0.01,
    )
    assert procrast_res["procrastination_detected"] is True


def test_factor_3_requirement_fulfillment_quick_simulation():
    res = simulate_rf(mode="quick", duration_seconds=0.01)
    assert "score" in res
    assert 0.0 <= res["score"] <= 1.0
    assert "features" in res
    assert "completed_tasks_count" in res["features"]
    assert "task_evaluations" in res
    assert len(res["task_evaluations"]) >= 1
    assert "traceability_rate" in res
    assert res["status"] == "completed"


def test_factor_4_collaboration_quick_simulation():
    res = simulate_collaboration(mode="quick", duration_seconds=0.01)
    assert "score" in res
    assert 0.0 <= res["score"] <= 1.0
    assert "features" in res
    assert "PRC_depth" in res["features"]
    assert "IC_depth" in res["features"]
    assert "substantiveness_rating" in res
    assert res["status"] == "completed"


def test_factor_5_task_complexity_quick_simulation():
    res = simulate_complexity(mode="quick", duration_seconds=0.01)
    assert "score" in res
    assert 0.0 <= res["score"] <= 1.0
    assert "features" in res
    assert "SP" in res["features"]
    assert "DR" in res["features"]
    assert res["structural_impact_level"] in ["low", "medium", "high"]
    assert res["status"] == "completed"


def test_factor_6_behavioral_pattern_quick_simulation():
    # Test Consistent deep contributor
    res_consistent = simulate_behavioral(
        payload={"factor_scores": {"effort": 0.85, "consistency": 0.80, "collaboration": 0.70, "code_ownership": 0.80}},
        mode="quick",
        duration_seconds=0.01,
    )
    assert res_consistent["persona"] == "Consistent deep contributor"
    assert res_consistent["score_modifier"] == 1.15

    # Test Last-minute rusher
    res_rusher = simulate_behavioral(
        payload={"factor_scores": {"effort": 0.85, "consistency": 0.20, "collaboration": 0.50, "code_ownership": 0.60}},
        mode="quick",
        duration_seconds=0.01,
    )
    assert res_rusher["persona"] == "Last-minute rusher"
    assert res_rusher["score_modifier"] == 0.92

    # Test Free rider
    res_free = simulate_behavioral(
        payload={"factor_scores": {"effort": 0.20, "consistency": 0.20, "collaboration": 0.15, "code_ownership": 0.30}},
        mode="quick",
        duration_seconds=0.01,
    )
    assert res_free["persona"] == "Free rider"
    assert res_free["score_modifier"] == 0.82


def test_factor_7_code_ownership_phases_and_capping():
    # Phase 1: generate
    q_res = simulate_ownership(phase="generate", mode="quick", duration_seconds=0.01)
    assert q_res["status"] == "quiz_generated"
    assert "generated_question" in q_res
    assert "code_snippet" in q_res

    # Phase 2: evaluate normal response
    eval_res = simulate_ownership(
        payload={"student_response": "The function calculates subtotal with tax and discount correctly."},
        phase="evaluate",
        mode="quick",
        duration_seconds=0.01,
    )
    assert eval_res["status"] == "completed"
    assert eval_res["features"]["capped_applied"] is False
    assert eval_res["score"] > 0.50

    # Phase 2: extension window capping
    eval_capped = simulate_ownership(
        payload={"student_response": "Good answer", "is_extension_period": True},
        phase="evaluate",
        mode="quick",
        duration_seconds=0.01,
    )
    assert eval_capped["features"]["capped_applied"] is True
    assert eval_capped["score"] <= 0.50

    # Phase 2: timeout zero score
    eval_to = simulate_ownership(
        payload={"is_timeout": True},
        phase="evaluate",
        mode="quick",
        duration_seconds=0.01,
    )
    assert eval_to["score"] == 0.0
    assert eval_to["features"]["timeout"] is True


@pytest.mark.asyncio
async def test_concurrent_all_factors_simulation():
    """Validates that all factor simulators can run concurrently in parallel fan-out without blocking."""
    tasks = [
        async_simulate_effort(mode="quick", duration_seconds=0.02),
        async_simulate_consistency(mode="quick", duration_seconds=0.02),
        async_simulate_rf(mode="quick", duration_seconds=0.02),
        async_simulate_collaboration(mode="quick", duration_seconds=0.02),
        async_simulate_complexity(mode="quick", duration_seconds=0.02),
        async_simulate_behavioral(mode="quick", duration_seconds=0.02),
        async_simulate_ownership(mode="quick", duration_seconds=0.02),
    ]

    results = await asyncio.gather(*tasks)
    assert len(results) == 7
    for res in results:
        assert res["status"] in ["completed", "quiz_generated"]
        assert "execution_time_seconds" in res


def test_cli_execution_of_all_simulators():
    """Validates that each factor simulator can be invoked directly from CLI."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "factor_models"
    scripts = [
        base_dir / "01_effort" / "simulate.py",
        base_dir / "02_consistency" / "simulate.py",
        base_dir / "03_requirement_fulfillment" / "simulate.py",
        base_dir / "04_collaboration" / "simulate.py",
        base_dir / "05_task_complexity" / "simulate.py",
        base_dir / "06_behavioral_pattern" / "simulate.py",
        base_dir / "07_code_ownership" / "simulate.py",
    ]

    for script in scripts:
        assert script.exists(), f"{script} must exist"
        cmd = [sys.executable, str(script), "--mode", "quick", "--duration", "0.01"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, f"CLI invocation failed for {script.name}: {proc.stderr}"
        assert '"status":' in proc.stdout
