"""The Collaboration score: a specified combination of six measures, with an evidence gate (PROTOCOL.md).

There is no fitted model here, on purpose: the data cannot support learned weights (PROTOCOL.md, "Why the combining step is fixed-weight").

    Collaboration = mean of the measures that have evidence, each scaled to 0-1:
        review comment substantiveness, issue comment substantiveness, meaningful mentions and replies,
        reviewed pull requests, authored comments, interaction response and resolution rate

Design assumptions (stated, measured in the sensitivity analysis, never tuned): equal weights, and the caps below.
A measure with no evidence (no review text, no pull request of the student's own) is left out of the mean. Count measures are 0 when the
student did nothing. If the team showed no review activity at all in the sprint the score is **not available** (``None``), not 0: a student
must not be marked down for something the team never did; fusion then redistributes the weight.
"""
import importlib.util
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cl = _load("collab_cleaning", "cleaning.py")

SCORE_VERSION = "collaboration-fixed/1"
MEASURES = ("review_substance", "issue_substance", "mentions_replies", "reviewed_prs", "authored_comments", "response_rate")
CAPS = {"mentions_replies": 3, "reviewed_prs": 3, "authored_comments": 5}
EQUAL = {m: 1 / len(MEASURES) for m in MEASURES}


class NotEnoughEvidence(ValueError):
    """Raised by ``evaluate`` when the score is not available; the agent's bridge turns it into a fallback and redistributes the weight."""


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def measures(evidence, caps=CAPS):
    """The six measures (0-1, or None when there is no evidence) and the counts behind them.

    Reviewed pull requests, mentions and replies, and authored comments count only engagement with substantive text (substance above 0), so approvals,
    one-word replies and padding cannot raise them; merging teammates' pull requests still counts once each.
    """
    c = cl.contributions(evidence)
    f = cl.featurize(evidence)["features"]
    sub_r = [cl.substance(t) for t in c["review_texts"]]
    sub_d = [cl.substance(t) for t in c["discussion_texts"]]
    substantive = sum(1 for x in sub_r + sub_d if x > 0)
    prs = {r.get("pr_id") or f"review-{i}" for i, r in enumerate(c["reviews"]) if r.get("body") and cl.substance(r["body"]) > 0}
    prs |= {m.get("pr_id") or f"comment-{i}" for i, m in enumerate(c["comments"]) if m.get("body") and cl.substance(m["body"]) > 0}
    reviewed = len(prs) + c["merged_for_others"]
    mentions = sum(int(bool(m.get("is_reply"))) + min(1, int(m.get("mentions", 0))) for m in c["comments"] if m.get("body") and cl.substance(m["body"]) > 0)
    m = {"review_substance": _mean(sub_r), "issue_substance": _mean(sub_d),
         "mentions_replies": min(1.0, mentions / caps["mentions_replies"]), "reviewed_prs": min(1.0, reviewed / caps["reviewed_prs"]),
         "authored_comments": min(1.0, substantive / caps["authored_comments"]), "response_rate": f["Co_IR"]}
    counts = {"review_texts": len(sub_r), "discussion_texts": len(sub_d), "substantive_texts": substantive, "trivial_texts": len(sub_r) + len(sub_d) - substantive,
              "reviewed_prs": reviewed, "mentions_replies": mentions, "own_prs": f["Co_prs_opened"], "merged_for_others": c["merged_for_others"],
              "excluded_self_or_bot": c["excluded_self_or_bot"]}
    return m, counts


def combine(m, weights=None):
    """Weighted mean of the measures that have evidence (weights renormalised over them)."""
    w = weights or EQUAL
    have = {k: v for k, v in m.items() if v is not None}
    total = sum(w[k] for k in have)
    return sum(w[k] * v for k, v in have.items()) / total if total else None


def sensitivity_interval(evidence, n=200, seed=7):
    """5th and 95th percentile of the score under random weightings and caps scaled by 0.5x / 1x / 2x. A design-uncertainty range, not a statistical interval."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        scale = (0.5, 1.0, 2.0)[i % 3]
        m, _ = measures(evidence, {k: v * scale for k, v in CAPS.items()})
        g = [rng.gammavariate(1.0, 1.0) for _ in MEASURES]
        w = {k: x / sum(g) for k, x in zip(MEASURES, g)}
        s = combine(m, w)
        if s is not None:
            out.append(s)
    if not out:
        return None
    out.sort()
    return [round(out[int(0.05 * (len(out) - 1))], 4), round(out[int(0.95 * (len(out) - 1))], 4)]


def team_reviews(evidence):
    """True / False when the evidence says whether anyone in the team reviewed or commented in the sprint, None when it does not say.

    The agent may supply ``evidence["team"] = {"reviews_and_comments": n}``: counts only, nothing about other students.
    """
    t = evidence.get("team")
    if isinstance(t, dict) and "reviews_and_comments" in t:
        return int(t["reviews_and_comments"]) > 0
    return None


def assess(evidence):
    """The full result for one student and sprint. ``score`` is None when it is not available (see ``warnings``)."""
    cl.schema.validate(evidence)
    base = cl.featurize(evidence)
    m, counts = measures(evidence)
    warnings = list(base["warnings"])
    team = team_reviews(evidence)
    active = bool(counts["review_texts"] or counts["discussion_texts"] or counts["own_prs"] or counts["merged_for_others"] or counts["reviewed_prs"])
    score, interval = None, None
    if team is False:
        warnings.append("not available: nobody in the team reviewed or commented in this sprint, so collaboration cannot be read; not scored as 0")
    elif team is None and not active:
        warnings.append("not available: no review or pull-request activity by this student and the team's activity was not supplied, so it cannot be told whether the team reviews")
    else:
        score = combine(m)
        interval = sensitivity_interval(evidence)
        if team is None:
            warnings.append("the team's review activity was not supplied; the score assumes the team reviews")
    features = {**{f"Co_measure_{k}": (None if v is None else round(v, 4)) for k, v in m.items()}, **{f"Co_count_{k}": v for k, v in counts.items()}}
    return {"factor": "collaboration", "score": None if score is None else round(score, 4), "interval": interval,
            "interval_kind": "sensitivity to weights and caps (design uncertainty), not a statistical interval", "features": features,
            "removed": {"trivial_or_approval_texts": counts["trivial_texts"], "excluded_self_or_bot": counts["excluded_self_or_bot"]},
            "versions": {"cleaning": base["versions"]["cleaning"], "features": base["versions"]["features"], "score": SCORE_VERSION}, "warnings": warnings}
