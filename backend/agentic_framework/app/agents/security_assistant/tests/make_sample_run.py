"""Make the checked-in sample runs the Security Assistant pages show in demo mode and the tests read.

    python -m app.agents.security_assistant.tests.make_sample_run [<results-dir>]

The sample is the synthetic Python demo repository, the saved Python scan, a MOCK LLM (every finding "confirmed", model name `mock-model`) and the
MOCK Tutor: it demonstrates the flow and says nothing about the quality of any model. Two runs of the same repository:
  sample-python-demo     the whole flow
  sample-python-no-llm   the same repository without the LLM stages (INCOMPLETE), for the compare view and the "skipped is not clean" display
Default results folder: backend/server/app/modules/security/sample_results (team folder J26-SE-363).
"""

import sys
import tempfile
from pathlib import Path

from app.agents.security_assistant import seed_security_demo as seed
from app.agents.security_assistant.tests.test_assess import SAMPLES, Forbidden, Mock, go
from app.agents.security_assistant.tools.tests.demo_repos import make_demo_repos

TEAM = "J26-SE-363"
RUNS = {"sample-python-demo": {"allow_external_llm": True}, "sample-python-no-llm": {"allow_external_llm": False}}
DEFAULT = Path(__file__).resolve().parents[5] / "server" / "app" / "modules" / "security" / "sample_results"


def build(results: Path) -> list[Path]:
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        demo = next(r for r in make_demo_repos(tmp / "repos") if r.name == "vuln_py_repo")
        for run_id, options in RUNS.items():
            out = tmp / run_id
            if options["allow_external_llm"]:
                go(demo, out, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
            else:
                go(demo, out, allow_external_llm=False, client=Forbidden())
            made.append(seed.seed_run(out, results, TEAM, run_id))
    seed.seed_shared(results)
    return made


if __name__ == "__main__":
    for path in build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT):
        print(f"wrote {path}")
