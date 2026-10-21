"""Load test of the student stage at one deadline (see app/agents/performance_assessment/assessment/loadtest.py for what it does and does not cover).

    cd backend/agentic_framework
    ../.venv/Scripts/python.exe scripts/load_test.py --students 250 --parallel 8 --db-latency 0.05
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FM = Path(__file__).resolve().parents[1] / "app" / "agents" / "performance_assessment" / "factor_models"
sys.path[:0] = [str(FM), str(FM / "03_requirement_fulfillment")]

from app.agents.performance_assessment.assessment.loadtest import run_load  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--students", type=int, default=250)
ap.add_argument("--parallel", type=int, default=8)
ap.add_argument("--db-latency", type=float, default=0.05, help="seconds every database write waits")
ap.add_argument("--rf-seconds", type=float, default=0.3, help="seconds the stand-in for the language-model factor waits")
a = ap.parse_args()
print(json.dumps(asyncio.run(run_load(a.students, a.parallel, a.db_latency, a.rf_seconds)), indent=1))
