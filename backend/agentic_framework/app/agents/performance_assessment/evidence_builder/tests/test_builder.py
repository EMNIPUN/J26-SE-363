"""Evidence builder against a throwaway local repository with several authors (no network)."""
import os
import subprocess

import pytest

from app.agents.performance_assessment.evidence_builder import Roster, build_team_evidence
from app.agents.performance_assessment.evidence_builder.gitlog import parse_log, parse_patches
from app.agents.performance_assessment.evidence_builder.identity import is_bot
from app.agents.performance_assessment.workspace import WorkspaceManager

SPRINT = {"id": "T9-S1", "team_id": "T9", "start": "2026-03-01", "end": "2026-03-14", "days": 14}
ROSTER = Roster([{"student_id": "STU-1", "emails": ["amy@x.org"], "logins": ["amy-gh"], "names": ["Amy A"]},
                 {"student_id": "STU-2", "emails": ["bob@x.org"], "logins": ["bob-gh"], "names": ["Bob B"]},
                 {"student_id": "STU-3", "emails": ["cy@x.org"], "logins": ["cy-gh"], "names": ["Cy C"]}])


def git(cwd, *args, who="amy", when=None):
    people = {"amy": ("Amy A", "amy@x.org"), "bob": ("Bob B", "bob@x.org"), "core": ("Core Dev", "core@x.org"), "stranger": ("Stranger", "who@elsewhere.com"), "bot": ("ci[bot]", "ci@bots.org")}
    n, e = people[who]
    env = {**os.environ, "GIT_AUTHOR_NAME": n, "GIT_AUTHOR_EMAIL": e, "GIT_COMMITTER_NAME": n, "GIT_COMMITTER_EMAIL": e}
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, msg, who, when):
    for name, text in files.items():
        p = repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", "-A", who=who, when=when)
    git(repo, "commit", "-q", "-m", msg, who=who, when=when)
    return git(repo, "rev-parse", "HEAD")


FEATURE_A = "\n".join(["# feature a", "def a1():", "    return 1", "", "def a2():", "    x = 2", "    y = 3", "    return x + y", "", "def a3():", "    return 'done'", ""])


class Repo(os.PathLike):
    def __init__(self, path, first_commit):
        self.path, self.first_commit = path, first_commit

    def __fspath__(self):
        return str(self.path)

    def __str__(self):
        return str(self.path)


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "origin"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, {"lib.py": "def lib():\n    return 1\n", "util.py": "from lib import lib\n\ndef util():\n    return lib()\n", "app.py": "from lib import lib\nfrom util import util\n\nprint(util() + lib())\n"},
           "base", "core", "2026-02-20T10:00:00+05:30")
    first = commit(r, {"feature_a.py": FEATURE_A}, "feat a", "amy", "2026-03-02T10:00:00+05:30")
    commit(r, {"feature_a.py": FEATURE_A.replace("x = 2", "x = 20").replace("y = 3", "y = 30").replace("return 1", "return 10").replace("return 'done'", "return 'ok'"), "feature_b.py": "def b():\n    return 2\n"},
           "rework a, add b", "bob", "2026-03-05T11:00:00+05:30")
    commit(r, {"junk.py": "x = 1\n"}, "stranger", "stranger", "2026-03-06T10:00:00+05:30")
    commit(r, {"gen.py": "y = 1\n"}, "bot", "bot", "2026-03-07T10:00:00+05:30")
    git(r, "checkout", "-q", "-b", "side")
    commit(r, {"side.py": "s = 1\n"}, "side work", "bob", "2026-03-08T10:00:00+05:30")
    git(r, "checkout", "-q", "main")
    git(r, "merge", "-q", "--no-ff", "side", "-m", "Merge pull request #2 from bob/side", who="bob", when="2026-03-10T10:00:00+05:30")
    commit(r, {"feature_c.py": "def c():\n    return 3\n"}, "feat c", "amy", "2026-03-13T23:30:00+05:30")
    commit(r, {"late.py": "z = 1\n"}, "after sprint", "bob", "2026-03-20T10:00:00+05:30")
    return Repo(r, first)


@pytest.fixture()
def ws(tmp_path):
    return WorkspaceManager(tmp_path / "ws", allow_local=True)


PRS = [{"number": 1, "user": {"login": "amy-gh"}, "created_at": "2026-03-02T05:00:00Z", "merged_at": "2026-03-06T05:00:00Z", "closed_at": "2026-03-06T05:00:00Z", "merged_by": "bob-gh",
        "_reviews": [{"user": {"login": "bob-gh"}, "state": "COMMENTED", "body": "The loop recomputes the total on every call, so cache it before the render.", "submitted_at": "2026-03-03T05:00:00Z"},
                     {"user": {"login": "ci[bot]"}, "state": "COMMENTED", "body": "bot", "submitted_at": "2026-03-03T06:00:00Z"}],
        "_review_comments": [{"user": {"login": "bob-gh"}, "body": "@amy-gh why not use a set here?", "created_at": "2026-03-03T05:30:00Z", "in_reply_to_id": None},
                             {"user": {"login": "amy-gh"}, "body": "Own comment, not counted for her", "created_at": "2026-03-03T07:00:00Z", "in_reply_to_id": 1}],
        "_issue_comments": [{"user": {"login": "cy-gh"}, "body": "Thanks, merging after the demo.", "created_at": "2026-03-04T05:00:00Z"}], "_commits": []},
       {"number": 2, "user": {"login": "bob-gh"}, "created_at": "2026-03-08T05:00:00Z", "merged_at": None, "closed_at": None, "merged_by": None, "_reviews": [], "_review_comments": [], "_issue_comments": [], "_commits": []}]


def test_log_and_patch_parsers_on_hand_written_text():
    text = "\x1e" + "a" * 40 + "\x1f" + "\x1f" + "Amy\x1famy@x.org\x1f2026-03-02T10:00:00+05:30\x1fsubject\x1fbody\x1e\n1\t2\tsrc/a.py\n-\t-\timg.png\n"
    c = parse_log(text)[0]
    assert c["files"] == [("src/a.py", 1, 2), ("img.png", None, None)] and c["parents"] == []
    p = parse_patches("@@@" + "a" * 40 + "\ndiff --git a/src/a.py b/src/a.py\nindex 1..2 100644\n--- a/src/a.py\n+++ b/src/a.py\n@@ -1,0 +2,2 @@\n+x = 1\n+--- not a header\n")
    assert p["a" * 40]["src/a.py"].splitlines() == ["@@ -1,0 +2,2 @@", "+x = 1", "+--- not a header"]


def test_bots_are_recognised():
    assert is_bot("ci[bot]", "") and is_bot("dependabot", "") and not is_bot("Amy A", "amy@x.org")


def test_evidence_per_student(ws, repo):
    tasks = {"STU-1": [{"task_id": "T9-001", "title": "Feature A", "story_points": 5, "subtask_count": 2, "status": "Done", "student_id": "STU-1", "completed_by": "STU-1", "linked_commits": [repo.first_commit[:7]],
                        "acceptance_criteria": ["returns 1", "returns the sum"]}],
             "STU-2": [{"task_id": "T9-002", "title": "Build on A", "story_points": 3, "subtask_count": 1, "status": "Done", "student_id": "STU-2", "linked_commits": [repo.first_commit[:7]], "acceptance_criteria": ["x"]}]}
    res = build_team_evidence(ws, str(repo), ROSTER, SPRINT, tasks, PRS)
    e1, e2, e3 = res.evidence["STU-1"], res.evidence["STU-2"], res.evidence["STU-3"]
    # commits: only the student's own, inside the sprint (author's date), bots and strangers not attributed
    assert [c["subject"] for c in e1["commits"]] == ["feat c", "feat a"]
    assert sorted(c["subject"] for c in e2["commits"]) == sorted(["rework a, add b", "side work", "Merge pull request #2 from bob/side"])
    assert e3["commits"] == []
    assert res.quality["unmapped_authors"] and "Stranger <who@elsewhere.com>" in res.quality["unmapped_authors"]
    assert res.quality["bot_commits"] == 1 and res.quality["commits_outside_sprint"] >= 2  # core's base commit and bob's late one
    # clean lines: feature_a has 8 code lines, 1 comment, 2 blank lines in the first commit
    fa = next(f for f in e1["commits"][1]["files"] if f["path"] == "feature_a.py")
    assert fa["line_stats"]["added"]["code"] == 8 and fa["line_stats"]["added"]["comment"] == 1 and fa["line_stats"]["added"]["blank"] == 2
    # merge commits are marked and carry no files
    assert any(c["is_merge"] and c["files"] == [] for c in e2["commits"])
    # tasks: linked prefix resolved to the real SHA; the teammate's commit is available to Task Complexity of the other student
    assert e1["tasks"][0]["commit_ids"] == [repo.first_commit] and e1["tasks"][0]["acceptance_criteria"] == ["returns 1", "returns the sum"]
    assert [c["id"] for c in e2["task_commits"]] == [repo.first_commit] and e1["task_commits"] == []
    # reach before the sprint: lib.py is imported by util.py and app.py (two hops: app imports util imports lib)
    assert e1["repo"]["reach_before"]["lib.py"] == 2 and e1["repo"]["reach_before"].get("feature_a.py") is None


def test_ownership_uses_blame_at_the_end_of_the_sprint(ws, repo):
    res = build_team_evidence(ws, str(repo), ROSTER, SPRINT, {}, PRS)
    own1, own2 = res.evidence["STU-1"]["ownership"], res.evidence["STU-2"]["ownership"]
    assert own1["added_lines"] > own1["surviving_lines"] > 0  # bob rewrote some of amy's lines
    assert own2["surviving_lines"] > 0 and own1["files"] >= 2
    assert res.evidence["STU-3"]["ownership"]["added_lines"] == 0


def test_github_parts(ws, repo):
    res = build_team_evidence(ws, str(repo), ROSTER, SPRINT, {}, PRS)
    e1, e2 = res.evidence["STU-1"], res.evidence["STU-2"]
    assert [p["id"] for p in e1["pull_requests"]] == ["1"] and e1["pull_requests"][0]["merged_at"]
    assert e2["merged_for_others"] == 1 and e1["merged_for_others"] == 0
    assert len(e2["reviews"]) == 1 and e2["reviews"][0]["pr_author"] == "STU-1" and "recomputes" in e2["reviews"][0]["body"]
    assert [c["kind"] for c in e2["comments"]] == ["review_comment"] and e2["comments"][0]["mentions"] == 1
    assert e1["reviews"] == [] and e1["comments"] == []  # her own comment on her own PR does not count
    assert res.evidence["STU-3"]["comments"][0]["kind"] == "discussion"
    assert e1["team"]["reviews_and_comments"] == 3  # bob's review, bob's review comment, cy's comment (the bot and the author are not counted)


def test_without_github_the_pull_request_parts_are_absent_not_empty(ws, repo):
    res = build_team_evidence(ws, str(repo), ROSTER, SPRINT, {}, None)
    assert "reviews" not in res.evidence["STU-1"] and "team" not in res.evidence["STU-1"] and res.quality["github"] is False


def test_the_real_factor_code_can_read_the_evidence(ws, repo):
    from app.agents.performance_assessment.evidence_builder.builder import _fm
    _, _, registry, _ = _fm()
    res = build_team_evidence(ws, str(repo), ROSTER, SPRINT, {}, PRS)
    factors = registry.load_factors(["effort", "consistency", "collab", "ko"])
    features, removed, warnings = registry.featurize_all(res.evidence["STU-1"], factors)
    assert features["E_CC"] >= 2 and features["C_AWR"] > 0 and "Co_PCount" in features and features["KO_survival"] is not None
    empty, *_ = registry.featurize_all(res.evidence["STU-3"], factors)
    assert empty["C_no_activity"] == 1
