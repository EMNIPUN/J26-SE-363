"""Queue one assessment run for the worker that is already running.

    cd backend/agentic_framework
    ../.venv/Scripts/python.exe scripts/trigger_run.py --team MC01 --sprint MC01-S3 --mode snapshot \
        --repo https://github.com/sadeeshasathsara/MediCare \
        --board-dir "../../../Data Collection/scrum_simulation/medicare" --identity "../../../Data Collection/scrum_simulation/medicare/private/identity.json" \
        --simulate-now 2026-04-13T23:00:00+05:30

What it does, in this order, and nothing else:
  1. saves the team's tracking record (repository, roster from the identity file, sprint dates, board folder) in the database named by --env-file,
  2. creates the run row,
  3. puts the job `performance.assess_team` on the queue. The worker (`python -m worker`) picks it up.
It then prints the run id and the command that watches the run (scripts/watch_run.py).

The database is the one in SERVER_DIRECT_URL of --env-file (default ../server/.env), the same one the worker uses. Only that one variable is read from the file, and it is never printed.
The identity file (git names, e-mails and logins of the students) is personal data: it is read, stored in the team's roster record, and never printed.
`--simulate-now` makes a snapshot behave as if it were taken at that moment (for a sprint that is already over); `--board-dir` points the Scrum MCP server at a board outside the course dataset.
"""
import argparse
import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_database_url(env_file: str) -> None:
    text = Path(env_file).read_text(encoding="utf-8")
    m = re.search(r"^SERVER_DIRECT_URL=(.*)$", text, re.M)
    if not m or not m.group(1).strip():
        sys.exit(f"no SERVER_DIRECT_URL in {env_file}")
    os.environ["SERVER_DIRECT_URL"] = m.group(1).strip().strip('"').strip("'")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", required=True)
    ap.add_argument("--sprint", required=True)
    ap.add_argument("--mode", choices=["snapshot", "final"], default="snapshot")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--board-dir", required=True)
    ap.add_argument("--identity", required=True)
    ap.add_argument("--simulate-now")
    ap.add_argument("--env-file", default="../server/.env")
    a = ap.parse_args()

    load_database_url(a.env_file)
    from shared.performance import PerformanceStore, RunAlreadyActive
    from shared.queue import app as queue

    board = Path(a.board_dir).resolve()
    sprint = next((r for r in csv.DictReader(open(board / "sprints.csv", encoding="utf-8")) if r["sprint_id"] == a.sprint), None)
    if sprint is None:
        sys.exit(f"sprint {a.sprint} is not in {board / 'sprints.csv'}")
    ident = json.loads(Path(a.identity).read_text(encoding="utf-8"))
    roster = [{"student_id": s["student_id"], "emails": s["emails"], "logins": s["logins"], "names": s["git_names"]} for s in ident["students"]]
    sprints = [{"id": r["sprint_id"], "start": r["start_date"], "end": r["end_date"]} for r in csv.DictReader(open(board / "sprints.csv", encoding="utf-8")) if r["team_id"] == a.team]
    config = {"roster": roster, "sprints": sprints, "scrum_data_dir": str(board), "release_to_students": False}
    if a.simulate_now:
        config["simulate_now"] = a.simulate_now

    store = PerformanceStore()
    store.upsert_tracked_team(a.team, a.repo, a.team, config, "trigger_run.py")
    print(f"tracking saved: team {a.team}, {len(roster)} students, {len(sprints)} sprints, board {board.name}")
    try:
        run = store.create_run(a.team, a.sprint, a.mode, "trigger_run.py")
    except RunAlreadyActive as e:
        run = e.run
        if run["status"] != "queued" or run.get("job_id"):
            sys.exit(f"a {a.mode} run for this sprint is already {run['status']}: {run['id']}")
        print("reusing the run from an earlier attempt that never reached the queue")
    run_id = str(run["id"])
    store.close()  # the database allows few connections at once: do not hold one while the queue opens its own

    async def enqueue():
        async with queue.open_async():
            return await queue.configure_task(name="performance.assess_team", queue="performance", lock=a.team).defer_async(payload={"run_id": run_id})

    job = asyncio.run(enqueue())
    store = PerformanceStore()
    store.update_run(run_id, job_id=job)
    store.close()
    print(f"queued job {job} on queue 'performance'")
    print(f"RUN ID: {run_id}")
    print(f"watch:  ../.venv/Scripts/python.exe scripts/watch_run.py {run_id}")


if __name__ == "__main__":
    main()
