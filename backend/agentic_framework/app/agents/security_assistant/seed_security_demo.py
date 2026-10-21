"""Put Security Assistant runs where the Security Assistant pages read them. Writes files only; it never touches a database.

    python -m app.agents.security_assistant.seed_security_demo --run scan_output/assess_vuln_py_repo --team J26-SE-363 \\
        [--results-dir DIR] [--run-id ID] [--student-email E --as-contributor C-xxxxxxxx] [--shared-only]

Result folders (the Core API reads them, see backend/server/app/modules/security/reader.py):

    <results-dir>/<team>/<run-id>/{report.json, run.json, audit.jsonl, report.md, trace_mapping.local.json}
    <results-dir>/_shared/{workflow,orchestrator,question,governance}.mmd, WORKFLOW.md, rq1_comparison.csv

Only those file names are copied (never pii_mapping.local.json). The default results folder is `scan_output/results` (git-ignored). A run is
copied as it is: nothing is re-scanned, re-interpreted or edited, except two things you ask for:
  * a missing run.json is written from the report (provenance that the run did not record is marked "unknown");
  * `--student-email E --as-contributor C-xxxxxxxx` sets the e-mail of that contributor in the local mapping, so the registered student
    sees those findings as "mine". The e-mail goes only into trace_mapping.local.json and is never printed.
Running it twice gives the same files.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.agents.security_assistant import manifest as mf

ROOT = Path(__file__).resolve().parent
RUN_FILES = ("report.json", "run.json", "audit.jsonl", "report.md", "trace_mapping.local.json")
SHARED_FILES = {"workflow.mmd": ROOT / "docs" / "workflow.mmd", "orchestrator.mmd": ROOT / "docs" / "orchestrator.mmd",
                "question.mmd": ROOT / "docs" / "question.mmd", "governance.mmd": ROOT / "docs" / "governance.mmd",
                "WORKFLOW.md": ROOT / "WORKFLOW.md", "rq1_comparison.csv": ROOT / "rq1_results" / "rq1_comparison.csv"}
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
CONTRIBUTOR = re.compile(r"^C-[0-9a-f]{8}$")
DEFAULT_RESULTS = Path("scan_output") / "results"


def default_run_id(manifest: dict) -> str:
    stamp = (manifest.get("started_at") or "unknown-time").replace(":", "").replace("-", "")[:13]
    sha = manifest.get("commit_sha")
    return f"{stamp}-{manifest.get('trigger', 'manual')}-{sha[:7] if sha else 'nocommit'}"


def manifest_from_report(report: dict, modified: float) -> dict:
    """A run.json for a run that was made before the manifest existed; what the run did not record is "unknown"."""
    when = datetime.fromtimestamp(modified, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"manifest_version": mf.MANIFEST_VERSION, "repo": report["meta"].get("source"), "commit_sha": report["meta"].get("commit_sha"),
            "trigger": "manual", "scan_type": "reused-scan" if report["scan"].get("reused") else "full", "started_at": when, "finished_at": when,
            "checkout": {"kind": "unknown", "read_only": True, "deleted_after": None, "code_executed": False},
            "tools": [{"tool": r["tool"], "version": r["tool_version"]} for r in report["scan"]["tool_runs"]],
            "llm": {"model": report["meta"].get("llm_model"), "temperature": report["meta"].get("temperature"),
                    "seed": (report.get("llm_usage") or {}).get("seed"), "interpreter_prompt": report["meta"].get("interpreter_prompt"),
                    "trace_prompt": report["meta"].get("trace_prompt")}}


def seed_shared(results: Path) -> list[Path]:
    shared = Path(results) / "_shared"
    shared.mkdir(parents=True, exist_ok=True)
    out = []
    for name, source in SHARED_FILES.items():
        if source.is_file():
            shutil.copyfile(source, shared / name)
            out.append(shared / name)
    return out


def seed_run(source: Path, results: Path, team: str, run_id: str | None = None, *, student_email: str | None = None,
             as_contributor: str | None = None) -> Path:
    """Copy one run folder into `<results>/<team>/<run-id>`. Returns the destination."""
    source = Path(source)
    if not (source / "report.json").is_file():
        raise ValueError(f"{source} has no report.json")
    if not NAME.match(team):
        raise ValueError("the team code must be a plain name such as J26-SE-363")
    report = json.loads((source / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads((source / "run.json").read_text(encoding="utf-8")) if (source / "run.json").is_file() \
        else manifest_from_report(report, (source / "report.json").stat().st_mtime)
    run_id = run_id or default_run_id(manifest)
    if not NAME.match(run_id):
        raise ValueError("the run id must be a plain name")
    if (student_email is None) != (as_contributor is None):
        raise ValueError("--student-email and --as-contributor go together")
    if as_contributor is not None and not CONTRIBUTOR.match(as_contributor):
        raise ValueError("a contributor id looks like C-0a1b2c3d")
    if as_contributor is not None and as_contributor not in {(f.get("introducing_commit") or {}).get("contributor") for f in report["findings"]}:
        raise ValueError(f"{as_contributor} is not the introducing contributor of any finding in this run")
    dest = Path(results) / team / run_id
    dest.mkdir(parents=True, exist_ok=True)
    for name in RUN_FILES:
        if name == "run.json":
            (dest / name).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        elif (source / name).is_file():
            shutil.copyfile(source / name, dest / name)
    if student_email is not None:
        set_student(dest, student_email, as_contributor)
    return dest


def set_student(dest: Path, email: str, contributor: str) -> None:
    """Make `contributor` the registered student's e-mail in the run's local mapping (created if the run has none)."""
    path = dest / "trace_mapping.local.json"
    doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"WARNING": "local only: maps pseudonymous contributor ids to real people; do not share or commit",
                                                                              "salt": "seeded", "contributors": {}}
    doc["contributors"][contributor] = {**doc["contributors"].get(contributor, {"name": "demo student"}), "email": email.strip().lower()}
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, action="append", default=[], help="a run folder made by `assess` (repeat for several runs)")
    ap.add_argument("--team", help="the team code, e.g. J26-SE-363")
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--run-id", help="name of the result folder (default: made from the time, trigger and commit; only with one --run)")
    ap.add_argument("--student-email")
    ap.add_argument("--as-contributor")
    ap.add_argument("--shared-only", action="store_true", help="only copy the diagrams, WORKFLOW.md and the RQ1 table")
    args = ap.parse_args(argv)
    try:
        if args.run_id and len(args.run) > 1:
            raise ValueError("--run-id needs exactly one --run")
        if args.run and not args.team:
            raise ValueError("--team is needed with --run")
        for source in args.run:
            print(f"seeded {seed_run(source, args.results_dir, args.team, args.run_id, student_email=args.student_email, as_contributor=args.as_contributor)}")
        for path in seed_shared(args.results_dir):
            print(f"shared {path.name}")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
