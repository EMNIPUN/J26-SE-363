"""The auditor that looks before it decides: tools, limits, and that it can never set a score."""
import json

import pytest

from app.agents.performance_assessment.assessment import audit, factors, fusion, investigate
from app.agents.performance_assessment.assessment.tests.test_pipeline import events, new_run, repo, world, ws  # noqa: F401  (fixtures)
from app.agents.performance_assessment.assessment.tests.test_units import CARDS, all_completed, res


class Script:
    """A model that answers from a list, one reply per call, and remembers what it was asked."""

    model = "script"

    def __init__(self, *replies):
        self.replies, self.seen = list(replies), []

    def chat(self, messages, **kw):
        self.seen.append(messages)

        class R:
            ok = True
            text = self.replies.pop(0) if self.replies else json.dumps({"decisions": [], "summary": "out of replies"})

        return R()


def silent_student():
    results = all_completed(effort=0.0)
    evidence = {"student_id": "S", "tasks": [{"id": "T1", "status": "Done", "completed_by": "S", "story_points": 5, "commit_ids": ["a"]}], "pull_requests": [], "reviews": [],
                "commits": [{"id": "c1", "authored_at": "2026-04-10T10:00:00+05:30", "is_merge": False, "subject": "configure the gateway   routes", "files": [
                    {"path": "k8s/auth.yaml", "kind": "config", "added": 40, "deleted": 0, "line_stats": {"added": {"code": 40}, "deleted": {"code": 0}}}]}]}
    return results, evidence, audit.findings(results, evidence)


def call(tool, **args):
    return json.dumps({"tool": tool, "args": args})


def final(fid, action="accept", reason="The commits are configuration only, which Effort does not count."):
    return json.dumps({"decisions": [{"finding": fid, "action": action, "reason": reason}], "summary": "Effort is blind to this work."})


def test_the_model_can_look_at_the_evidence_before_it_decides():
    results, evidence, found = silent_student()
    fid = [f for f in found if f["severity"] != "info"][0]["id"]
    llm = Script(call("inspect_evidence", what="files"), call("get_factor_card", factor="effort"), final(fid))
    out = investigate.run(llm, found, CARDS, results, evidence)
    assert [t["tool"] for t in out["trace"]] == ["inspect_evidence", "get_factor_card"]
    assert '"config": 1' in out["trace"][0]["result"] and "k8s/auth.yaml" in out["trace"][0]["result"]
    assert "allowed_remedies" in llm.seen[2][-1]["content"]  # the model got the whole card; the log keeps a shortened copy
    assert out["decisions"][fid]["action"] == "accept" and "configuration only" in out["decisions"][fid]["reason"]
    assert "Tool result:" in llm.seen[1][-1]["content"]  # the result was handed back to the model


def test_commit_subjects_are_cut_and_no_address_or_answer_reaches_the_model():
    results, evidence, found = silent_student()
    evidence["commits"][0]["subject"] = "x" * 300
    evidence["commits"][0]["author_email"] = "someone@example.com"
    out = investigate._tool_inspect(evidence, {"what": "commits"})
    assert len(out["recent"][0]["subject"]) == 80 and "someone@example.com" not in json.dumps(out)


def test_marking_a_factor_not_available_leaves_it_out_and_never_sets_a_score():
    results, evidence, found = silent_student()
    fid = [f for f in found if f["severity"] != "info"][0]["id"]
    llm = Script(call("mark_not_available", factor="effort", reason="All 19 commits are configuration files, which Effort cannot count."), final(fid, "escalate", "Effort left out; check the infrastructure work by hand."))
    out = investigate.run(llm, found, CARDS, results, evidence)
    assert out["overrides"] == {"effort": "All 19 commits are configuration files, which Effort cannot count."}
    changed = investigate.apply_overrides(results, out["overrides"])
    assert changed["effort"]["status"] == "not_available" and changed["effort"]["score"] is None and "left out by the auditor" in changed["effort"]["warnings"][-1]
    assert results["effort"]["score"] == 0.0  # the original result is untouched
    fused = fusion.fuse({**results, **changed}, None)
    assert "effort" not in fused["effective_weights"] and sum(fused["effective_weights"].values()) == pytest.approx(1.0)


def test_bad_requests_to_the_tools_are_refused_without_effect():
    results, evidence, found = silent_student()
    results["collaboration"] = res("collaboration", None, status="not_available")
    fid = [f for f in found if f["severity"] != "info"][0]["id"]
    llm = Script(call("mark_not_available", factor="effort", reason="short"), call("mark_not_available", factor="collaboration", reason="The factor has no score, so it cannot be left out."),
                 call("set_score", factor="effort", score=0.9), call("get_factor_card", factor="nope"), final(fid))
    out = investigate.run(llm, found, CARDS, results, evidence)
    assert out["overrides"] == {}
    assert [("error" in t["result"]) for t in out["trace"]] == [True, True, True, True]
    assert "unknown tool" in out["trace"][2]["result"]


def test_the_investigation_has_a_step_limit_and_a_model_that_never_finishes_gets_no_decision():
    results, evidence, found = silent_student()
    llm = Script(*[call("compare_with_history")] * 20)
    assert investigate.run(llm, found, CARDS, results, evidence) is None
    assert len(llm.seen) <= investigate.MAX_STEPS + 2  # it stopped asking, it did not loop forever


def test_garbage_replies_cost_a_step_and_the_old_style_final_answer_still_works():
    results, evidence, found = silent_student()
    fid = [f for f in found if f["severity"] != "info"][0]["id"]
    out = investigate.run(Script("I think it is fine.", final(fid)), found, CARDS, results, evidence)
    assert out["trace"][0]["tool"] == "(invalid reply)" and out["decisions"][fid]["action"] == "accept"
    assert investigate.run(Script(final(fid)), found, CARDS, results, evidence)["trace"] == []  # answered at once, as audit.llm_decide's format
    assert investigate.run(None, found, CARDS, results, evidence) is None
    assert investigate.run(Script(final("x")), [f for f in found if f["severity"] == "info"], CARDS, results, evidence) is None


# ---- in the pipeline -------------------------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_in_a_run_the_investigation_is_logged_and_a_left_out_factor_changes_the_mark(world, monkeypatch):
    from app.agents.performance_assessment.assessment import graph as graph_mod, runner

    sv = world

    class Auditor:
        model = "auditor"

        def chat(self, messages, **kw):
            tag = kw.get("tag", "")

            class R:
                ok = True
                text = "{}"

            if tag.startswith("audit"):
                user = messages[1]["content"]
                findings = json.loads(user)["findings"] if messages[1]["role"] == "user" and user.startswith("{") else []
                last = messages[-1]["content"]
                if findings and not last.startswith("Tool result"):
                    f = next((x for x in findings if x["factor"] == "effort"), findings[0])
                    R.text = call("mark_not_available", factor=f["factor"], reason="The auditor found that this factor cannot see the student's work.") if f["factor"] != "fusion" else call("compare_with_history")
                elif findings:
                    R.text = json.dumps({"decisions": [{"finding": x["id"], "action": "accept", "reason": "Left the factor out; the rest stands."} for x in findings], "summary": "ok"})
                else:
                    R.text = json.dumps({"decisions": [], "summary": "ok"})
            elif tag == "polish":
                R.text = ""
            else:
                from experiments.agent_critic import AgentCritic
                R.text = AgentCritic.dry_responder(messages, tag)
            return R()

    sv.llm = Auditor()
    original = factors.run_factor

    async def zero_effort_for_bob(name, evidence, **kw):
        out = await original(name, evidence, **kw)
        if name == "effort" and evidence["student_id"] == "STU-2":
            out = {**out, "score": 0.0, "status": "completed"}  # a score the audit will question
        return out

    monkeypatch.setattr(factors, "run_factor", zero_effort_for_bob)
    rid = new_run(sv)
    assert (await runner.run_assessment(sv, rid))["status"] == "succeeded"
    tools = [e for e in events(sv, rid, "tool") if e["node_path"] == "student:STU-2/explain"]
    bob = {r["student_id"]: r for r in sv.store.latest_results("T9", "T9-S1")}["STU-2"]
    assert any(t["payload"].get("tool") == "mark_not_available" for t in tools)  # the model's call is in the log of the explain step
    assert "effort" in bob["justification"]["audit"]["left_out"]
    assert bob["factors"]["effort"]["status"] == "not_available" and bob["factors"]["effort"]["score"] is None
    assert bob["mark"] is not None and "Effort" in bob["justification"]["summary"]  # the mark was composed again without Effort, and the summary says so
    assert any("left out of the mark by the auditor" in e["message"] for e in events(sv, rid, "log"))
