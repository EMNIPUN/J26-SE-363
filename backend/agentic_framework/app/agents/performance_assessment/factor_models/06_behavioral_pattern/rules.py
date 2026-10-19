"""The Behavioral Pattern rules (proposal 3.1.7), as code. Decisions are in training/PROTOCOL.md.

    classify(scores, bimodal=None, thresholds=None, late_churn=None) -> {persona, score_modifier, rationale, strength, near_threshold, matched, untestable_rules, ...}

``scores`` is ``{"E": .., "C": .., "Co": ..}``; ``Co`` may be ``None`` when the Collaboration factor is not available (nobody in the team reviewed in the sprint). A missing
score is never replaced by 0 or by a typical value: a rule that needs it is reported as not testable, and when E or C is missing the student is "Unclassified" with a neutral
modifier of 1.00. No model, no network, no randomness.

Rules version 2 has two optional extensions, each switched on by a flag in a threshold set (the proposal's own set and ``calibrated_v1`` run the original rules):
A) ``ext_rusher``: Last-minute rusher also fires on a high late-churn share (``late_churn``, the Consistency package's C_DC, only when the student had activity). Evaluated and
**not adopted** (it missed its precision criterion, see training/PROTOCOL.md); the code stays so the evaluation can be repeated. B) ``ext_free_rider``: Free rider fires on effort
alone, with a milder modifier, when Collaboration is not available. Adopted.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES_VERSION = "behavioral_pattern_rules/2"
MODIFIER_CAP = (0.80, 1.20)
NEAR_THRESHOLD = 0.10

PROPOSAL = {"name": "proposal", "E_high": 0.7, "C_high": 0.7, "C_low": 0.3, "E_mid": 0.4, "E_low": 0.3, "Co_high": 0.7, "Co_low": 0.3}

# order of the table in the proposal; used only to break exact ties
PATTERNS = ("Consistent deep contributor", "Last-minute rusher", "Reviewer or coordinator", "Burst worker", "Free rider")
# modifier at weak evidence -> modifier at strong evidence (the proposal's ranges)
RANGES = {"Consistent deep contributor": (1.10, 1.20), "Last-minute rusher": (0.95, 0.90), "Reviewer or coordinator": (1.00, 1.05), "Burst worker": (1.00, 0.95), "Free rider": (0.85, 0.80)}
RANGE_EFFORT_ONLY = (0.95, 0.90)  # Free rider decided without a Collaboration score (extension B)
# (input, comparison, threshold name); Burst worker also needs the bimodal flag; Last-minute rusher and the effort-only Free rider are handled in evaluate_rule
CONDITIONS = {
    "Consistent deep contributor": (("E", ">", "E_high"), ("C", ">", "C_high")),
    "Last-minute rusher": (("E", ">", "E_high"), ("C", "<", "C_low")),
    "Reviewer or coordinator": (("E", "<", "E_mid"), ("Co", ">", "Co_high")),
    "Burst worker": (("E", ">", "E_high"),),
    "Free rider": (("E", "<", "E_low"), ("Co", "<", "Co_low")),
}
RATIONALE = {
    "Consistent deep contributor": "High effort that is spread steadily across the sprint.",
    "Last-minute rusher": "High effort concentrated at the end of the sprint with little steady work before it.",
    "Reviewer or coordinator": "Little code of their own but strong review and discussion with teammates.",
    "Burst worker": "High effort delivered in irregular, separate bursts.",
    "Free rider": "Very low observable effort together with very little collaboration.",
    "Balanced contributor": "No pattern applies: contributions are in the middle range.",
    "Unclassified": "Effort or Consistency is not available, so no pattern is assigned and no adjustment is made.",
}
RATIONALE_EFFORT_ONLY = "Almost no observable activity; collaboration could not be assessed because nobody in the team reviewed in the sprint, so the adjustment is milder."


def load_thresholds(name=None):
    """Thresholds by name. Default: the calibrated set when thresholds.json exists next to this file, otherwise the proposal's numbers."""
    p = HERE / "thresholds.json"
    sets = {"proposal": PROPOSAL}
    if p.exists():
        stored = json.loads(p.read_text(encoding="utf-8"))
        sets.update({k: {"name": k, **v} for k, v in stored.get("sets", {}).items()})
    return sets[name or ("calibrated" if "calibrated" in sets else "proposal")]


def _valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


def _margin(x, op, thr):
    """Distance past the threshold as a share of the room left to the end of the scale (0 at the threshold, 1 at the end)."""
    room = (1.0 - thr) if op in (">", ">=") else thr
    return max(0.0, min(1.0, ((x - thr) if op in (">", ">=") else (thr - x)) / room)) if room > 0 else 1.0


def _holds(x, op, thr):
    return x > thr if op == ">" else (x >= thr if op == ">=" else x < thr)


def evaluate_rule(pattern, scores, bimodal, th, late_churn=None):
    """(matched, strength or None, why_untestable or None, evidence or None) for one rule."""
    if pattern == "Last-minute rusher" and th.get("ext_rusher"):
        return _rusher_v2(scores, th, late_churn)
    if pattern == "Free rider" and th.get("ext_free_rider") and not _valid(scores.get("Co")) and _valid(scores.get("E")) and _valid(scores.get("C")):
        if scores["E"] < th["E_low"] and scores["C"] < th["C_low"]:
            return True, min(_margin(float(scores["E"]), "<", th["E_low"]), _margin(float(scores["C"]), "<", th["C_low"])), None, "effort_only"
        return False, None, "Co not available (effort-only path not met)", None
    for key, _, _ in CONDITIONS[pattern]:
        if not _valid(scores.get(key)):
            return False, None, f"{key} not available", None
    if pattern == "Burst worker" and bimodal not in (0, 1, True, False):
        return False, None, "C_bimodal not available", None
    if not all(_holds(float(scores[k]), op, th[t]) for k, op, t in CONDITIONS[pattern]):
        return False, None, None, None
    if pattern == "Burst worker" and not bimodal:
        return False, None, None, None
    return True, min(_margin(float(scores[k]), op, th[t]) for k, op, t in CONDITIONS[pattern]), None, "full"


def _rusher_v2(scores, th, late_churn):
    """Extension A: high effort and (low Consistency, the proposal's path, or a high late-churn share)."""
    e, c = scores.get("E"), scores.get("C")
    if not (_valid(e) and _valid(c)):
        return False, None, "E or C not available", None
    paths = []
    if e > th["E_med"] and c < th["C_low"]:
        paths.append(min(_margin(float(e), ">", th["E_med"]), _margin(float(c), "<", th["C_low"])))
    if _valid(late_churn) and e > th["E_med"] and late_churn >= th["DC_high"]:
        paths.append(min(_margin(float(e), ">", th["E_med"]), _margin(float(late_churn), ">=", th["DC_high"])))
    return (True, max(paths), None, "full") if paths else (False, None, None, None)


def modifier_for(pattern, strength, evidence="full"):
    weak, strong = RANGE_EFFORT_ONLY if (pattern == "Free rider" and evidence == "effort_only") else RANGES[pattern]
    return weak + (strong - weak) * strength


def classify(scores, bimodal=None, thresholds=None, late_churn=None):
    th = thresholds or load_thresholds()
    scores = {k: scores.get(k) for k in ("E", "C", "Co")}
    warnings, untestable, matched = [], {}, []
    if not (_valid(scores["E"]) and _valid(scores["C"])):
        missing = [k for k in ("E", "C") if not _valid(scores[k])]
        return _result("Unclassified", 1.0, None, scores, bimodal, th, [], {}, [f"{', '.join(missing)} missing or outside 0-1: no pattern assigned"], "full")
    for pattern in PATTERNS:
        ok, strength, why, evidence = evaluate_rule(pattern, scores, bimodal, th, late_churn)
        if why:
            untestable[pattern] = why
        elif ok:
            matched.append((pattern, strength, modifier_for(pattern, strength, evidence), evidence))
    if any(why.startswith("Co ") for why in untestable.values()):
        warnings.append("Collaboration not available: the Reviewer or coordinator and Free rider rules could not be fully tested")
    if bimodal not in (0, 1, True, False):
        warnings.append("C_bimodal not available: the Burst worker rule could not be tested")
    if th.get("ext_rusher") and not _valid(late_churn):
        warnings.append("late-churn share not available: only the Consistency path of the Last-minute rusher rule was tested")
    if not matched:
        return _result("Balanced contributor", 1.0, None, scores, bimodal, th, [], untestable, warnings, "full")
    # more than one match (Last-minute rusher or Consistent with Burst worker can overlap): the milder modifier wins
    matched.sort(key=lambda m: (abs(m[2] - 1.0), PATTERNS.index(m[0])))
    pattern, strength, mod, evidence = matched[0]
    if len(matched) > 1:
        warnings.append("more than one pattern matched (" + ", ".join(m[0] for m in matched) + "): the one with the milder modifier was used")
    if evidence == "effort_only":
        warnings.append("Free rider decided from effort alone: Collaboration was not available")
    return _result(pattern, mod, strength, scores, bimodal, th, [m[0] for m in matched], untestable, warnings, evidence)


def _result(pattern, modifier, strength, scores, bimodal, th, matched, untestable, warnings, evidence):
    modifier = max(MODIFIER_CAP[0], min(MODIFIER_CAP[1], modifier))
    rationale = RATIONALE_EFFORT_ONLY if (pattern == "Free rider" and evidence == "effort_only") else RATIONALE[pattern]
    return {"persona": pattern, "score_modifier": round(modifier, 4), "rationale": rationale, "strength": None if strength is None else round(strength, 4),
            "near_threshold": bool(strength is not None and strength < NEAR_THRESHOLD), "matched": matched, "evidence": evidence if pattern in PATTERNS else None,
            "untestable_rules": dict(untestable),
            "pattern_features": {"effort": scores["E"], "consistency": scores["C"], "collaboration": scores["Co"], "bimodal": None if bimodal is None else int(bool(bimodal))},
            "thresholds": th["name"], "versions": {"rules": RULES_VERSION}, "warnings": warnings, "model": "RuleBasedTypologyClassifier", "status": "completed"}
