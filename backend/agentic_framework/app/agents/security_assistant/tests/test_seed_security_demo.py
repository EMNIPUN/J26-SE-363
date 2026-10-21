"""The seed script copies runs into the result folders the Security Assistant pages read, and writes nothing else."""

import hashlib
import json

import pytest

from app.agents.security_assistant import seed_security_demo as seed
from app.agents.security_assistant.tests.test_assess import SAMPLES, Mock, demo, go  # noqa: F401  (demo is a fixture)

TEAM = "J26-SE-363"


@pytest.fixture(scope="module")
def source(demo, tmp_path_factory):
    out = tmp_path_factory.mktemp("assessment")
    go(demo, out, client=Mock(), req=SAMPLES / "requirements.json", tasks=SAMPLES / "tasks.json")
    (out / "pii_mapping.local.json").write_text('{"names": {"Jane Doe": "x"}}', encoding="utf-8")  # must never be copied
    return out


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def contributor(source):
    report = json.loads((source / "report.json").read_text(encoding="utf-8"))
    return next(f["introducing_commit"]["contributor"] for f in report["findings"] if f["introducing_commit"])


def test_a_run_is_copied_with_its_manifest_and_only_the_whitelisted_files(source, tmp_path):
    dest = seed.seed_run(source, tmp_path, TEAM, "run-1")
    assert dest == tmp_path / TEAM / "run-1"
    assert {p.name for p in dest.iterdir()} == {"report.json", "run.json", "audit.jsonl", "report.md", "trace_mapping.local.json"}
    assert (dest / "report.json").read_bytes() == (source / "report.json").read_bytes()  # copied as it is
    assert not (dest / "pii_mapping.local.json").exists()


def test_the_manifest_of_a_run_is_kept_as_it_is(source, tmp_path):
    dest = seed.seed_run(source, tmp_path, TEAM, "run-1")
    assert json.loads((dest / "run.json").read_text(encoding="utf-8")) == json.loads((source / "run.json").read_text(encoding="utf-8"))


def test_a_run_made_before_the_manifest_existed_gets_one_with_unknowns_marked(source, tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    for name in ("report.json", "audit.jsonl"):
        (old / name).write_bytes((source / name).read_bytes())
    m = json.loads((seed.seed_run(old, tmp_path / "out", TEAM) / "run.json").read_text(encoding="utf-8"))
    assert m["checkout"]["kind"] == "unknown" and m["trigger"] == "manual" and m["repo"] == "vuln_py_repo" and m["tools"]
    assert seed.seed_run(old, tmp_path / "out", TEAM).name.endswith("-manual-nocommit")  # a made-up run id still follows the rule


def test_running_it_twice_changes_nothing(source, tmp_path):
    seed.seed_run(source, tmp_path, TEAM, "run-1", student_email="Student@Example.org", as_contributor=contributor(source))
    seed.seed_shared(tmp_path)
    first = tree(tmp_path)
    seed.seed_run(source, tmp_path, TEAM, "run-1", student_email="Student@Example.org", as_contributor=contributor(source))
    seed.seed_shared(tmp_path)
    assert tree(tmp_path) == first and first


def test_the_students_email_goes_only_into_the_local_mapping(source, tmp_path):
    who = contributor(source)
    dest = seed.seed_run(source, tmp_path, TEAM, "run-1", student_email=" Student@Example.org ", as_contributor=who)
    mapping = json.loads((dest / "trace_mapping.local.json").read_text(encoding="utf-8"))
    assert mapping["contributors"][who]["email"] == "student@example.org"
    for name in ("report.json", "run.json", "report.md", "audit.jsonl"):
        assert "student@example.org" not in (dest / name).read_text(encoding="utf-8").lower()


def test_a_run_without_a_mapping_gets_one_when_a_student_is_named(source, tmp_path):
    bare = tmp_path / "bare"
    bare.mkdir()
    for name in ("report.json", "run.json"):
        (bare / name).write_bytes((source / name).read_bytes())
    who = contributor(source)
    dest = seed.seed_run(bare, tmp_path / "out", TEAM, "r", student_email="s@example.org", as_contributor=who)
    assert json.loads((dest / "trace_mapping.local.json").read_text(encoding="utf-8"))["contributors"][who]["email"] == "s@example.org"


@pytest.mark.parametrize("kwargs,why", [
    ({"team": "../x"}, "plain name"), ({"run_id": "../x"}, "plain name"), ({"run_id": "a/b"}, "plain name"),
    ({"student_email": "a@b.co"}, "go together"), ({"as_contributor": "C-0a1b2c3d"}, "go together"),
    ({"student_email": "a@b.co", "as_contributor": "Jane"}, "looks like"),
    ({"student_email": "a@b.co", "as_contributor": "C-00000000"}, "not the introducing contributor"),
])
def test_bad_arguments_are_refused_and_nothing_is_written(source, tmp_path, kwargs, why):
    args = {"team": TEAM, "run_id": "run-1", **kwargs}
    with pytest.raises(ValueError, match=why):
        seed.seed_run(source, tmp_path / "out", args.pop("team"), args.pop("run_id"), **args)
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").rglob("report.json"))


def test_a_folder_that_is_not_a_run_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no report.json"):
        seed.seed_run(tmp_path, tmp_path / "out", TEAM, "r")


def test_the_shared_files_are_the_diagrams_the_workflow_text_and_the_rq1_table(tmp_path):
    names = {p.name for p in seed.seed_shared(tmp_path)}
    assert names == {"workflow.mmd", "orchestrator.mmd", "question.mmd", "governance.mmd", "WORKFLOW.md", "rq1_comparison.csv"}


def test_the_command_seeds_a_run_and_prints_no_email(source, tmp_path, capsys):
    who = contributor(source)
    code = seed.main(["--run", str(source), "--team", TEAM, "--results-dir", str(tmp_path), "--run-id", "r1",
                      "--student-email", "student@example.org", "--as-contributor", who])
    out = capsys.readouterr().out
    assert code == 0 and "seeded" in out and "shared workflow.mmd" in out and "student@example.org" not in out
    assert (tmp_path / TEAM / "r1" / "report.json").is_file()


def test_the_command_reports_usage_errors(source, tmp_path, capsys):
    assert seed.main(["--run", str(source), "--results-dir", str(tmp_path)]) == 3
    assert seed.main(["--run", str(source), "--run", str(source), "--team", TEAM, "--run-id", "x", "--results-dir", str(tmp_path)]) == 3
    assert "--team is needed" in capsys.readouterr().err
    assert seed.main(["--shared-only", "--results-dir", str(tmp_path)]) == 0
