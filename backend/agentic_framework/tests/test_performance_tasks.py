"""The assessment jobs: periodic sync, staggered nightly snapshots, one run per team."""
import subprocess
from datetime import datetime, timezone

import pytest
from procrastinate import testing
from shared.performance.memory_store import MemoryStore
from shared.queue import app as queue_app

from app.agents.performance_assessment.assessment.services import Services
from app.agents.performance_assessment.workspace import WorkspaceManager
from app.tasks import performance_tasks as tasks


def today():
    return datetime.now(timezone.utc).date().isoformat()


@pytest.fixture()
def world(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    for args in (["init", "-q", "-b", "main"], ["-c", "user.name=a", "-c", "user.email=a@x.org", "commit", "-q", "--allow-empty", "-m", "first"]):
        subprocess.run(["git", *args], cwd=origin, check=True, capture_output=True)
    store = MemoryStore()
    sprint = {"id": "S1", "start": "2000-01-01", "end": "2999-12-31"}
    store.upsert_tracked_team("T1", str(origin), "T1", {"sprints": [sprint]})
    store.upsert_tracked_team("T2", str(origin), "T2", {"sprints": [{"id": "S0", "start": "2000-01-01", "end": "2000-02-01"}]})  # sprint is over
    sv = Services(store=store, ws=WorkspaceManager(tmp_path / "ws", allow_local=True), scrum=lambda: None, work_dir=tmp_path / "runs")
    monkeypatch.setattr(tasks, "_services", sv)
    with queue_app.replace_connector(testing.InMemoryConnector()) as app:
        yield sv, app.connector


@pytest.mark.asyncio
async def test_sync_fetches_the_mirror_and_records_it(world):
    sv, _ = world
    assert await tasks.sync_team({"team_ref": "T1"}) == {"team_ref": "T1", "commits": 1}
    assert sv.store.get_tracked_team("T1")["config"]["last_sync"]["commits"] == 1
    sv.store.set_tracking_status("T1", "paused")
    assert await tasks.sync_team({"team_ref": "T1"}) == {"skipped": True}


@pytest.mark.asyncio
async def test_nightly_snapshots_start_only_for_sprints_in_progress_each_at_its_own_offset(world):
    sv, connector = world
    assert await tasks.snapshot_all(0) == {"started": 1}
    runs = sv.store.list_runs("T1")
    assert len(runs) == 1 and runs[0]["mode"] == "snapshot" and sv.store.list_runs("T2") == []
    job = next(iter(connector.jobs.values()))
    assert job["task_name"] == "performance.assess_team" and job["lock"] == "T1" and job["args"] == {"payload": {"run_id": runs[0]["id"]}}
    assert job["scheduled_at"] is not None
    assert await tasks.snapshot_all(0) == {"started": 0}  # a snapshot is already queued for it


@pytest.mark.asyncio
async def test_two_hourly_sync_queues_one_job_per_active_team(world):
    _, connector = world
    assert await tasks.sync_all(0) == {"teams": 1}
    assert await tasks.sync_all(0) == {"teams": 0}  # the first sync is still waiting: not queued twice
    syncs = [j for j in connector.jobs.values() if j["task_name"] == "performance.sync_team"]
    assert len(syncs) == 1 and syncs[0]["queueing_lock"] == "sync:T1"
