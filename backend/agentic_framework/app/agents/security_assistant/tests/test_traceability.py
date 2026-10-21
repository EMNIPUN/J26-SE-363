"""Traceability: introducing commit, requirement/task links, pseudonymous contributors. Git repositories are built in a
temporary folder, the LLM is a scripted mock; no scanner, network or API key is used."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.agents.security_assistant import trace
from app.agents.security_assistant.report import upsert_section
from app.agents.security_assistant.traceability import (
    FormatError, Proposal, Pseudonymizer, Story, Task, build_links, introducing_commit, load_stories, load_tasks,
)

SAMPLES = Path(__file__).resolve().parents[1] / "traceability_samples"
ALICE, ALICE_MAIL = "Alice Example", "alice.example@students.example.org"
BOB, BOB_MAIL = "Bob Builder", "bob.builder@students.example.org"


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def git(repo, name, mail, *args):
    done = subprocess.run(["git", "-c", f"user.name={name}", "-c", f"user.email={mail}", *args], cwd=repo,
                          check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "student"
    r.mkdir()
    git(r, ALICE, ALICE_MAIL, "init", "-q")
    (r / "app.py").write_text("import flask\n\ndef login():\n    return 1\n")
    git(r, ALICE, ALICE_MAIL, "add", "-A")
    git(r, ALICE, ALICE_MAIL, "commit", "-q", "-m", "T-101 US-01: login")
    (r / "app.py").write_text("import flask\n\ndef login():\n    return 1\n\ndef orders(user_id):\n    return user_id\n")
    git(r, BOB, BOB_MAIL, "add", "-A")
    git(r, BOB, BOB_MAIL, "commit", "-q", "-m", f"quick change, ask {BOB} ({BOB_MAIL})")
    (r / "old.py").write_text("KEY = 'x'\n")
    git(r, ALICE, ALICE_MAIL, "add", "-A")
    git(r, ALICE, ALICE_MAIL, "commit", "-q", "-m", "T-103 add old settings")
    (r / "old.py").unlink()
    git(r, ALICE, ALICE_MAIL, "add", "-A")
    git(r, ALICE, ALICE_MAIL, "commit", "-q", "-m", "remove old settings")
    return r


def old_sha(repo):
    return git(repo, ALICE, ALICE_MAIL, "log", "--format=%H", "--diff-filter=A", "--", "old.py")


STORIES = [Story("US-01", "Customers can log in", ["login route /login", "the token expires"]),
           Story("US-02", "Customers see their own orders", ["route /users/<user_id>/orders", "no other customer's orders"])]
TASKS = [Task("T-101", "Implement login", "Sprint 1", "US-01", []), Task("T-102", "Orders list", "Sprint 1", "US-02", []),
         Task("T-103", "S3 settings", "Sprint 2", None, [])]


def group(gid, rule, file, line, status="confirmed", source=None, message="", **extra):
    brief = {"finding_key": gid, "category": "V1", "tool": "codeql", "rule_id": rule, "file_path": file, "line": line,
             "fix_pattern": "general", "severity_tool": "high", "cwe": "CWE-639", "source": source, "sink": None,
             "function_or_endpoint": None, "message": message, **extra}
    return {"group_id": gid, "kind": "single", "package": None, "representative": brief, "members": [brief],
            "result": {"status": status, "confidence": 0.9, "rationale": "r", "evidence_ids": ["E1"]}}


def write_doc(tmp_path, *groups):
    p = tmp_path / "out" / "interpreted.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"meta": {}, "summary": {}, "merge_log": [], "groups": list(groups)}), encoding="utf-8")
    return p


class Mock:
    model = "mock-model"

    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    async def complete(self, system, user, schema=None, schema_name="verdict"):
        self.prompts.append((system, user, schema_name))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


def proposal(story="", task="", evidence=("E1",), confidence=0.7):
    return {"story_id": story, "task_id": task, "rationale": "looks related", "evidence_ids": list(evidence),
            "confidence": confidence}


def files(tmp_path, stories=True, tasks=True):
    """Neutral requirement and task files (no file names in the texts, so only the rules under test can fire)."""
    out = []
    if stories:
        p = tmp_path / "req.json"
        p.write_text(json.dumps({"stories": [{"id": s.id, "title": s.title, "acceptance_criteria": s.acceptance_criteria}
                                             for s in STORIES]}), encoding="utf-8")
        out += ["--requirements", p]
    if tasks:
        p = tmp_path / "tasks.json"
        p.write_text(json.dumps({"tasks": [{"id": t.id, "title": t.title, "sprint": t.sprint, "story_id": t.story_id,
                                            "commits": t.commits} for t in TASKS]}), encoding="utf-8")
        out += ["--tasks", p]
    return [str(x) for x in out]


def go(args, client=None):
    return run(trace.main([str(a) for a in args], client=client))


def traced(tmp_path):
    return json.loads((tmp_path / "out" / "traced.json").read_text(encoding="utf-8"))


# ---- the introducing commit -------------------------------------------------------------------------------------------------------------
def test_the_introducing_commit_is_the_one_that_added_the_line(repo):
    first, _ = introducing_commit(repo, "app.py", 3)  # def login(): from the first commit
    second, how = introducing_commit(repo, "app.py", 6)  # def orders(...) from Bob's commit
    assert first.subject == "T-101 US-01: login" and second.author_name == BOB
    assert "added the line" in how


def test_a_deleted_file_is_found_from_the_commit_the_scanner_reported(repo):
    c, _ = introducing_commit(repo, "old.py", 1, start_rev=old_sha(repo))
    assert c.subject == "T-103 add old settings"


def test_no_introducing_commit_is_reported_as_such(repo, tmp_path):
    none, why = introducing_commit(repo, "missing.py", 1)
    assert none is None and "no introducing commit" in why
    none, why = introducing_commit(tmp_path, "app.py", 1)
    assert none is None and "no git history" in why
    none, why = introducing_commit(repo, "../escape.py", 1)
    assert none is None


def test_a_dependency_without_a_line_uses_the_first_commit_that_added_it(repo):
    (repo / "requirements.txt").write_text("flask==1.0\n")
    git(repo, ALICE, ALICE_MAIL, "add", "-A")
    git(repo, ALICE, ALICE_MAIL, "commit", "-q", "-m", "T-104 pin deps")
    c, how = introducing_commit(repo, "requirements.txt", None, needle="flask")
    assert c.subject == "T-104 pin deps" and "first commit that added" in how


# ---- the input files ---------------------------------------------------------------------------------------------------------------------
def test_the_sample_files_load():
    stories, tasks = load_stories(SAMPLES / "requirements.json"), load_tasks(SAMPLES / "tasks.json")
    assert [s.id for s in stories] == ["US-01", "US-02", "US-03"]
    assert [t.id for t in tasks][-1] == "T-105" and tasks[-1].story_id is None


@pytest.mark.parametrize("content", ['not json', '{"stories": "x"}', '{"stories": [{"id": "bad id!", "title": "t"}]}',
                                     '{"stories": [{"id": "A", "title": "t"}, {"id": "A", "title": "u"}]}'])
def test_a_bad_requirements_file_is_refused(tmp_path, content):
    p = tmp_path / "r.json"
    p.write_text(content)
    with pytest.raises(FormatError):
        load_stories(p)


def test_the_cli_exits_3_on_a_bad_file(tmp_path, repo, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    assert go([write_doc(tmp_path, group("G01", "r", "app.py", 3)), repo, "--requirements", bad]) == 3
    assert "cannot read the input" in capsys.readouterr().err


# ---- link rules -----------------------------------------------------------------------------------------------------------------------------
def commit_of(repo, line):
    return introducing_commit(repo, "app.py", line)[0]


def finding(file="app.py", line=3, endpoint=None):
    return trace.finding_from_brief(group("G", "r", file, line, function_or_endpoint=endpoint)["representative"])


def test_a_commit_message_that_names_the_ids_gives_verified_links(repo):
    links, rejected, _ = build_links(finding(line=3), commit_of(repo, 3), STORIES, TASKS)
    by = {(l.kind, l.id): l for l in links}
    assert by[("task", "T-101")].status == "verified" and "commit_message_reference" in by[("task", "T-101")].methods
    assert by[("story", "US-01")].status == "verified" and by[("story", "US-01")].confidence >= 0.9
    assert all(l.evidence and l.methods for l in links) and not rejected


def test_a_task_that_lists_the_commit_is_verified_and_gives_its_story(repo):
    sha = commit_of(repo, 6).sha
    tasks = [Task("T-102", "Orders list", "Sprint 1", "US-02", [sha[:10]])]
    links, _, _ = build_links(finding(line=6), commit_of(repo, 6), STORIES, tasks)
    by = {(l.kind, l.id): l for l in links}
    assert by[("task", "T-102")].methods == ["task_commit_list"] and by[("story", "US-02")].methods == ["task_linked_story"]


def test_a_file_or_endpoint_in_exactly_one_story_is_verified_but_two_are_not(repo):
    links, _, _ = build_links(finding(line=6, endpoint="/login"), commit_of(repo, 6), STORIES, [])
    assert [(l.id, l.status, l.methods) for l in links] == [("US-01", "verified", ["file_or_endpoint_mentioned"])]
    both = STORIES + [Story("US-09", "Another login page", ["also /login"])]
    links, _, notes = build_links(finding(line=6, endpoint="/login"), commit_of(repo, 6), both, [])
    assert links == [] and any("too vague" in n for n in notes)


def test_a_model_proposal_alone_is_only_a_candidate(repo):
    links, rejected, notes = build_links(finding(line=6), commit_of(repo, 6), STORIES, TASKS,
                                         Proposal("US-02", "T-102", "related", ["E1"], 0.7))
    assert {(l.id, l.status, tuple(l.methods)) for l in links} == {("US-02", "candidate", ("llm_proposal",)),
                                                                   ("T-102", "candidate", ("llm_proposal",))}
    assert not rejected


def test_a_proposal_that_a_rule_also_supports_becomes_verified_and_keeps_both_methods(repo):
    links, _, _ = build_links(finding(line=3), commit_of(repo, 3), STORIES, TASKS, Proposal("US-01", "T-101", "x", ["E1"], 0.6))
    task = next(l for l in links if l.id == "T-101")
    assert task.status == "verified" and task.methods == ["commit_message_reference", "llm_proposal"]


def test_a_story_or_task_id_that_does_not_exist_is_rejected(repo):
    links, rejected, _ = build_links(finding(line=6), commit_of(repo, 6), STORIES, TASKS, Proposal("US-99", "T-999", "x", ["E1"], 0.9))
    assert links == [] and {r["id"] for r in rejected} == {"US-99", "T-999"}
    assert all("does not exist" in r["reason"] for r in rejected)


def test_a_finding_without_a_matching_story_says_so(repo):
    _, _, notes = build_links(finding(line=6), commit_of(repo, 6), STORIES, TASKS)
    assert "no matching story" in notes


# ---- the command --------------------------------------------------------------------------------------------------------------------------
def test_deterministic_run_verifies_and_writes_outputs(tmp_path, repo, capsys):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 3))
    assert go([doc, repo, *files(tmp_path)], client=None) == 0
    t = traced(tmp_path)
    ids = {(l["kind"], l["id"], l["status"]) for l in t["traces"][0]["links"]}
    assert ("task", "T-101", "verified") in ids and ("story", "US-01", "verified") in ids
    assert t["traces"][0]["introducing_commit"]["subject"] == "T-101 US-01: login"
    md = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    assert "## Traceability" in md and "T-101" in md and "introducing commit" in md.lower()
    assert "blame" not in md.lower() and "responsible" not in md.lower()


def test_without_a_requirements_file_findings_link_to_commits_only(tmp_path, repo, capsys):
    class Forbidden:
        model = "forbidden"

        async def complete(self, *a, **k):
            raise AssertionError("the LLM was called")

    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    assert go([doc, repo, "--propose-links", "--allow-external-llm"], client=Forbidden()) == 0
    t = traced(tmp_path)
    assert t["traces"][0]["links"] == [] and t["traces"][0]["introducing_commit"]["sha"]
    assert t["meta"]["requirements_file"] is None
    assert "linked to commits only" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    assert "no requirements file given" in capsys.readouterr().out


def test_a_finding_with_no_introducing_commit_is_reported_honestly(tmp_path, repo):
    doc = write_doc(tmp_path, group("G01", "r", "gone.py", 4))
    assert go([doc, repo, *files(tmp_path)]) == 0
    t = traced(tmp_path)["traces"][0]
    assert t["introducing_commit"] is None and any("no introducing commit" in n for n in t["notes"])
    assert traced(tmp_path)["summary"]["without_introducing_commit"] == 1
    assert "none found" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")


def test_history_only_finding_uses_the_commit_that_added_the_line(tmp_path, repo):
    doc = write_doc(tmp_path, group("G01", "aws-access-token", "old.py", 1, source=f"commit:{old_sha(repo)}"))
    assert go([doc, repo, *files(tmp_path)]) == 0
    t = traced(tmp_path)["traces"][0]
    assert t["introducing_commit"]["subject"] == "T-103 add old settings"
    assert ("task", "T-103") in {(l["kind"], l["id"]) for l in t["links"]}


def test_llm_candidate_only_link_and_the_fake_story_id(tmp_path, repo):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    mock = Mock(proposal(story="US-02", task="T-102"))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=mock) == 0
    links = traced(tmp_path)["traces"][0]["links"]
    assert {(l["id"], l["status"]) for l in links} == {("US-02", "candidate"), ("T-102", "candidate")}
    assert mock.prompts[0][2] == "link"

    mock = Mock(proposal(story="US-77"))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=mock) == 0
    t = traced(tmp_path)
    assert t["traces"][0]["links"] == [] and t["traces"][0]["rejected_links"][0]["id"] == "US-77"
    assert t["summary"]["rejected_links"] == 1


@pytest.mark.parametrize("reply, why", [(proposal(story="US-02", evidence=("E9",)), "does not exist"),
                                        ("not json", "not valid JSON"),
                                        ({"story_id": "US-02"}, "schema errors"),
                                        (proposal(story="US-02", confidence=3), "schema errors")])
def test_bad_model_output_gives_no_link(tmp_path, repo, reply, why):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=Mock(reply)) == 2
    t = traced(tmp_path)["traces"][0]
    assert t["links"] == [] and any(why in n for n in t["notes"])


def test_a_failed_llm_call_gives_no_link_and_exit_2(tmp_path, repo):
    from app.agents.security_assistant.interpreter.llm import LLMError
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=Mock(LLMError("down"))) == 2
    assert traced(tmp_path)["traces"][0]["links"] == []


def test_only_confirmed_findings_are_traced(tmp_path, repo):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 3), group("G02", "r", "app.py", 6, status="dismissed"),
                    group("G03", "r", "app.py", 6, status="uncertain"))
    assert go([doc, repo, *files(tmp_path)]) == 0
    assert [t["group_id"] for t in traced(tmp_path)["traces"]] == ["G01"]


def test_proposals_are_refused_without_the_flag_and_dry_run_calls_nothing(tmp_path, repo, capsys):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    assert go([doc, repo, *files(tmp_path), "--propose-links"], client=Mock(proposal())) == 4
    mock = Mock(proposal())
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--dry-run"], client=mock) == 0
    out = capsys.readouterr().out
    assert mock.prompts == [] and "Stories" in out and "nothing was sent" in out
    assert not (tmp_path / "out" / "traced.json").exists()


# ---- privacy ------------------------------------------------------------------------------------------------------------------------------
def test_no_author_name_or_email_in_any_output_or_prompt(tmp_path, repo, capsys):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6), group("G02", "r", "app.py", 3),
                    group("G03", "k", "old.py", 1, source=f"commit:{old_sha(repo)}"))
    mock = Mock(proposal(story="US-02", task="T-102"))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=mock) == 0
    seen = capsys.readouterr().out + "\n".join(f"{s}\n{u}" for s, u, _ in mock.prompts)
    for p in (tmp_path / "out").iterdir():
        if not p.name.endswith(".local.json"):
            seen += p.read_text(encoding="utf-8")
    for secret in (ALICE, BOB, "Alice", "alice.example", "bob.builder", "students.example.org", "Builder"):
        assert secret.lower() not in seen.lower(), secret
    contributors = {t["introducing_commit"]["contributor"] for t in traced(tmp_path)["traces"]}
    assert len(contributors) == 2 and all(c.startswith("C-") for c in contributors)


def test_the_mapping_is_a_local_file_and_the_ids_are_stable_between_runs(tmp_path, repo):
    doc = write_doc(tmp_path, group("G01", "r", "app.py", 6))
    assert go([doc, repo]) == 0
    first = traced(tmp_path)["traces"][0]["introducing_commit"]["contributor"]
    mapping = tmp_path / "out" / "trace_mapping.local.json"
    assert BOB_MAIL in mapping.read_text(encoding="utf-8")  # the real person is only here
    assert go([doc, repo]) == 0
    assert traced(tmp_path)["traces"][0]["introducing_commit"]["contributor"] == first
    assert Pseudonymizer.load(mapping).id_for(BOB, BOB_MAIL) == first


def test_the_salt_can_be_fixed_from_the_environment(monkeypatch):
    monkeypatch.setenv("SECURITY_ASSISTANT_PSEUDONYM_SALT", "s")
    a = Pseudonymizer.load(Path("does-not-exist.json")).id_for("x", "X@y.org")
    b = Pseudonymizer.load(Path("does-not-exist.json")).id_for("other", "x@y.org")
    assert a == b  # keyed on the lower-cased email


# ---- the report section -------------------------------------------------------------------------------------------------------------------
def test_upsert_section_replaces_instead_of_appending(tmp_path):
    md = tmp_path / "report.md"
    md.write_text("# scan\n\n<!-- a -->\n## A\nold\n\n<!-- b -->\n## B\nkeep\n", encoding="utf-8")
    upsert_section(md, "<!-- a -->", "<!-- a -->\n## A\nnew\n")
    upsert_section(md, "<!-- c -->", "<!-- c -->\n## C\nadded\n")
    upsert_section(md, "<!-- c -->", "<!-- c -->\n## C\nadded again\n")
    text = md.read_text(encoding="utf-8")
    assert "old" not in text and "new" in text and "keep" in text and text.count("<!-- c -->") == 1 and "added again" in text
    assert text.index("<!-- a -->") < text.index("<!-- b -->") < text.index("<!-- c -->")


# ---- the seeded samples against the demo repository ---------------------------------------------------------------------------
def test_samples_and_demo_repo_agree_and_the_ci_finding_has_no_story(tmp_path):
    from app.agents.security_assistant.tools.tests.demo_repos import make_demo_repos
    demo = next(r for r in make_demo_repos(tmp_path / "demo") if r.name == "vuln_py_repo")
    doc = write_doc(tmp_path, group("G01", "orders", "app.py", 19), group("G02", "unpinned-uses", ".github/workflows/ci.yml", 6))
    assert go([doc, demo, "--requirements", SAMPLES / "requirements.json", "--tasks", SAMPLES / "tasks.json"]) == 0
    t = {x["group_id"]: x for x in traced(tmp_path)["traces"]}
    assert ("task", "T-101", "verified") in {(l["kind"], l["id"], l["status"]) for l in t["G01"]["links"]}
    assert ("story", "US-01", "verified") in {(l["kind"], l["id"], l["status"]) for l in t["G01"]["links"]}
    assert [(l["kind"], l["id"]) for l in t["G02"]["links"]] == [("task", "T-105")]
    assert "no matching story" in t["G02"]["notes"] and traced(tmp_path)["summary"]["findings_without_story"] == 1


def test_the_groq_client_sends_the_given_schema_for_strict_models():
    from app.agents.security_assistant.interpreter.llm import GroqClient
    c = GroqClient("k", "openai/gpt-oss-120b")
    body = c._body("s", "u", True, trace.LINK_SCHEMA, "link")
    assert body["response_format"]["json_schema"]["name"] == "link" and body["response_format"]["json_schema"]["schema"] is trace.LINK_SCHEMA
    assert c._body("s", "u", True)["response_format"]["json_schema"]["name"] == "verdict"


# ---- one proposal per file, commit and category ---------------------------------------------------------------------------------------
def test_findings_of_one_file_commit_and_category_share_one_llm_call(tmp_path, repo):
    mock = Mock(proposal(story="US-01", task="T-101"))
    g1, g2 = group("G01", "r1", "app.py", 3), group("G02", "r2", "app.py", 4)  # lines 3 and 4 were added by the same commit
    g3 = group("G03", "r3", "app.py", 3)
    g3["representative"]["category"] = "V3"  # another category: its own question
    doc = write_doc(tmp_path, g1, g2, g3)
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=mock) == 0
    assert len(mock.prompts) == 2  # G01 and G02 share, G03 asks again
    t = {x["group_id"]: x for x in traced(tmp_path)["traces"]}
    for gid in ("G01", "G02", "G03"):
        assert {(l["id"], l["status"]) for l in t[gid]["links"]} >= {("US-01", "verified"), ("T-101", "verified")}
    shared_note = [l["evidence"] for l in t["G02"]["links"] if "llm_proposal" in l["methods"]]
    assert shared_note and any("one proposal for the findings of this file" in e for ev in shared_note for e in ev)
    assert not any("one proposal for the findings" in e for ev in [l["evidence"] for l in t["G01"]["links"]] for e in ev)


def test_a_failed_proposal_is_not_shared_and_is_asked_again(tmp_path, repo):
    from app.agents.security_assistant.interpreter.llm import LLMError
    mock = Mock(LLMError("down"))
    doc = write_doc(tmp_path, group("G01", "r1", "app.py", 3), group("G02", "r2", "app.py", 4))
    assert go([doc, repo, *files(tmp_path), "--propose-links", "--allow-external-llm"], client=mock) == 2
    assert len(mock.prompts) == 2 and traced(tmp_path)["summary"]["proposal_failures"] == 2
