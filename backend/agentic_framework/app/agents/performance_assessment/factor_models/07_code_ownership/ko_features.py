"""Hand-built, deterministic features of an answer to a code question, the reference explanation, and the guards that run before the model.

Used both when training (training/) and when the agent scores an answer (score.py), so the two see the same numbers. No model, no network.

Everything here compares the answer with the question, the code and the facts the syntax tree gave (questions.py); none of it reads who wrote the answer.
"""
import keyword
import re

FEATURES_VERSION = "ko_features/2"
FEATURE_NAMES = ["n_words", "log_chars", "identifier_recall", "identifier_share", "code_copy", "question_echo", "fact_overlap", "hedges", "reasoning_markers", "has_backticks",
                 "focus_overlap", "exc_named"]
MIN_WORDS = 4
CODE_COPY_LIMIT = 0.60
ECHO_LIMIT = 0.80

WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
HEDGES = re.compile(r"\b(i think|i guess|not sure|maybe|probably|i believe|kind of|sort of|i'm not sure|i am not sure|something like)\b", re.I)
REASONING = re.compile(r"\b(because|since|so that|so the|so it|otherwise|instead|therefore|which means|that way|in order to|if not|only when|only if)\b", re.I)
STOP = {"the", "a", "an", "of", "to", "in", "and", "or", "is", "it", "this", "that", "for", "on", "as", "be", "by", "with", "at", "are", "was", "if", "not", "self"}


def identifiers(code):
    """Names used in the code that are worth mentioning: not keywords, not one- or two-letter names, not 'self'."""
    names = {w for w in WORD.findall(code) if w not in ("self", "cls") and not keyword.iskeyword(w) and len(w) > 2}
    return {w.lower() for w in names}


def words(text):
    return [w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", text)]


def _ngrams(ws, n):
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def _calls(facts):
    """Called names, without exception constructors (older stored facts include them; questions.facts() no longer does)."""
    return [c for c in (facts or {}).get("calls", []) if not c.endswith(("Error", "Exception", "Warning"))]


def fact_terms(facts):
    """Key terms a correct answer is expected to use: exception names, names in conditions, returned and called names. facts: output of questions.facts()."""
    out = set()
    if not facts:
        return out
    for g in facts.get("guards", []):
        out |= {w.lower() for w in WORD.findall(g["raises"] + " " + g["cond"])}
    for h in facts.get("handlers", []):
        out |= {w.lower() for w in WORD.findall(h["exc"] + " " + h["then"])}
    for e in facts.get("early_returns", []):
        out |= {w.lower() for w in WORD.findall(e["cond"] + " " + e["value"])}
    for lp in facts.get("loops", []):
        out |= {w.lower() for w in WORD.findall((lp["target"] or "") + " " + lp["iter"])}
    for r in facts.get("returns", [])[-1:]:
        out |= {w.lower() for w in WORD.findall(r)}
    for c in _calls(facts)[:3]:
        out |= {w.lower() for w in WORD.findall(c)}
    return {w for w in out if len(w) > 2 and not keyword.iskeyword(w) and w not in STOP}


def focus_facts(facts, qtype):
    """(terms, exception names) of the fact the question is about, e.g. the first guard for a 'guard' question. Empty when the question type is unknown."""
    f = facts or {}
    texts, excs = [], []
    if qtype == "guard" and f.get("guards"):
        g = f["guards"][0]
        texts, excs = [g["raises"], g["cond"]], [g["raises"]]
    elif qtype == "handler" and f.get("handlers"):
        h = f["handlers"][0]
        texts, excs = [h["exc"], h["then"]], [h["exc"]]
    elif qtype == "early_return" and f.get("early_returns"):
        texts = [f["early_returns"][0]["cond"], f["early_returns"][0]["value"]]
    elif qtype == "loop" and f.get("loops"):
        texts = [f["loops"][0]["target"] or "", f["loops"][0]["iter"]]
    elif qtype == "return_value" and f.get("returns"):
        texts = [f["returns"][-1]] + _calls(f)[:2]
    elif qtype == "purpose":
        texts = list(f.get("params", []))
    terms = {w.lower() for t in texts for w in WORD.findall(t)}
    terms = {w for w in terms if len(w) > 2 and not keyword.iskeyword(w) and w not in STOP}
    names = {w.lower() for e in excs for w in WORD.findall(e.split(".")[-1]) if len(w) > 2}
    return terms, names


def reference_text(facts, name=""):
    """The reference explanation in words, built from the facts only (so it is the same for training and serving)."""
    parts = []
    if name:
        parts.append(f"{name}:")
    for g in (facts or {}).get("guards", []):
        parts.append(f"raises {g['raises']} when {g['cond']}.")
    for h in (facts or {}).get("handlers", []):
        parts.append(f"catches {h['exc']} and then {h['then']}.")
    for e in (facts or {}).get("early_returns", []):
        parts.append(f"returns {e['value']} when {e['cond']}.")
    for lp in (facts or {}).get("loops", []):
        parts.append(f"loops over {lp['iter']}." if lp["target"] else f"repeats while {lp['iter']}.")
    for r in (facts or {}).get("returns", [])[-2:]:
        parts.append(f"returns {r}.")
    if _calls(facts):
        parts.append("calls " + ", ".join(_calls(facts)[:3]) + ".")
    return " ".join(parts)


def featurize(answer, question, code, facts=None, qtype=None):
    """The hand-built features of one answer, as a dict keyed by FEATURE_NAMES. qtype: the question type (guard, handler, ...) when known."""
    aw = words(answer)
    n = len(aw)
    ids = identifiers(code)
    mentioned = {w for w in aw if w in ids}
    code_words = words(code)
    ans_grams, code_grams = _ngrams(aw, 4), _ngrams(code_words, 4)
    q_grams = _ngrams(words(question), 4)
    terms = fact_terms(facts)
    focus, excs = focus_facts(facts, qtype)
    aset = set(aw)
    return {
        "focus_overlap": len(focus & aset) / len(focus) if focus else 0.0,
        "exc_named": float(bool(excs & aset)) if excs else 0.0,
        "n_words": n,
        "log_chars": float(__import__("math").log1p(len(answer))),
        "identifier_recall": len(mentioned) / len(ids) if ids else 0.0,
        "identifier_share": sum(1 for w in aw if w in ids) / n if n else 0.0,
        "code_copy": len(ans_grams & code_grams) / len(ans_grams) if ans_grams else 0.0,
        "question_echo": len(ans_grams & q_grams) / len(ans_grams) if ans_grams else 0.0,
        "fact_overlap": len(terms & set(aw)) / len(terms) if terms else 0.0,
        "hedges": len(HEDGES.findall(answer)),
        "reasoning_markers": len(REASONING.findall(answer)),
        "has_backticks": int("`" in answer),
    }


REPEAT_SHARE = 0.20
REPEAT_MIN = 6


def guard(answer, question, code, facts=None, qtype=None):
    """Why an answer is rated 1 without the model, or None. Deterministic and checkable.

    Rules (training/PROTOCOL.md, the last two added after the first robustness run): too short; repeats the question; copies the code; mentions nothing from this
    code (no identifier of the code and no term of the fact the question asks about, so a fluent answer written for another function or a generic sentence is not rated);
    one word makes up a large share of the answer (padding).
    """
    text = (answer or "").strip()
    aw = words(text)
    if len(aw) < MIN_WORDS:
        return "the answer is empty or shorter than 4 words"
    f = featurize(text, question, code, facts, qtype)
    if f["question_echo"] >= ECHO_LIMIT:
        return "the answer mostly repeats the question"
    cl = [ln.strip() for ln in code.splitlines() if ln.strip()]
    pasted = sum(len(words(ln)) for ln in cl if ln and ln in text)
    if f["code_copy"] >= CODE_COPY_LIMIT or (len(aw) and pasted / len(aw) >= CODE_COPY_LIMIT):
        return "the answer mostly copies lines from the code"
    if f["identifier_recall"] == 0 and f["focus_overlap"] == 0:
        return "the answer mentions nothing from this code"
    top = max((aw.count(w) for w in set(aw) if w not in STOP), default=0)
    if top >= REPEAT_MIN and top / len(aw) >= REPEAT_SHARE:
        return "one word makes up a large share of the answer (padding)"
    return None


def feature_sets(E, H=None):
    """Matrices for the feature sets of training/PROTOCOL.md from embeddings E {ans, ques, code, ref, joint} (rows L2-normalised) and hand-built features H (n, k) or None.

    A: answer. B: answer + similarity of the answer to reference/code/question. C: B + answer-times-reference. D: joint question+answer text + similarities.
    "+H" appends the hand-built features. Defined here so training and serving build the same matrix.
    """
    import numpy as np
    sims = np.column_stack([(E["ans"] * E["ref"]).sum(1), (E["ans"] * E["code"]).sum(1), (E["ans"] * E["ques"]).sum(1)])
    sets = {"A": E["ans"], "B": np.hstack([E["ans"], sims]), "C": np.hstack([E["ans"], sims, E["ans"] * E["ref"]]), "D": np.hstack([E["joint"], sims])}
    if H is not None:
        h = np.asarray(H, float)
        sets.update({f"{k}+H": np.hstack([v, h]) for k, v in list(sets.items())})
    return sets
