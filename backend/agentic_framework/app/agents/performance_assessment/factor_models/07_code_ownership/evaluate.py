"""Production entry point of the Code Ownership factor (looked up by ``com_agent/factor_bridge.py``: ``factor_models/07_code_ownership/evaluate.py``).

The agent's quiz node calls two functions of this module (the node holds the flow: the 48-hour window, the extension and its cap, the double timeout; this folder holds
everything about the code, the question and the rating):

``generate_quiz(payload)``  phase 1. payload ``{"files": [{"path", "text"}], "student_id", "sprint_id"}`` -> question, snippet, reference criteria, AST metadata, or ``None``.
``evaluate(payload)``       phase 2. payload ``{"student_response", "code_snippet", "generated_question", "facts"?, "ownership"?, "is_timeout"?, "allow_unvalidated_language"?}``
                            -> standard factor result ``{factor, score, interval, features, removed, versions, warnings}`` with ``features.ko_raw_score``.

``evaluate`` raises ``NotEnoughEvidence`` (the bridge then applies its fallback and fusion redistributes the weight, as for Collaboration) when there is no answer yet, when
the encoder or the trained head cannot be loaded, or when the code is not Python (the scorer is trained and tested on Python only; ``allow_unvalidated_language`` switches that
check off and the result then carries a warning). A timeout payload (``is_timeout``) is a real zero, not an unavailable score.

Until the agent's ingestion hands over source files, ``async_evaluate`` passes payloads it cannot score to ``simulate.py`` exactly as before.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_quiz = _load("ko_quiz_prod", "quiz.py")
_score = _load("ko_score_prod", "score.py")
_clean = _quiz.cleaning


class NotEnoughEvidence(ValueError):
    """Raised when the factor cannot be scored; the agent's bridge turns it into a fallback and fusion redistributes the weight."""


def generate_quiz(payload, context=None):
    """Phase 1: the question for one student and sprint, or None when no file has a function worth asking about."""
    return _quiz.generate(payload.get("files") or [], payload.get("student_id", ""), payload.get("sprint_id", ""), payload.get("salt", ""))


def _language_python(payload):
    meta = payload.get("ast_metadata") or {}
    if meta.get("language"):
        return meta["language"] == "python"
    path = payload.get("file_path") or ""
    if path:
        return path.endswith(".py")
    code = payload.get("code_snippet") or ""
    return code.lstrip().startswith(("def ", "async def ", "@")) or "def " in code.split("\n", 1)[0]


def evaluate(payload, context=None):
    passive = _clean.featurize(payload["evidence"]) if isinstance(payload.get("evidence"), dict) and payload["evidence"].get("schema") == "evidence/1" else None
    if payload.get("is_timeout"):
        return {"factor": "code_ownership", "score": 0.0, "interval": [0.0, 0.0], "features": {"ko_raw_score": 0.0, "comprehension_rating_1_to_5": 1.0, "timeout": True},
                "removed": {}, "versions": {"score": _score.SCORE_VERSION}, "warnings": ["no answer within the quiz windows"]}
    answer = (payload.get("student_response") or "").strip()
    if not answer:
        raise NotEnoughEvidence("no quiz answer yet: the active part of Code Ownership is pending")
    code = payload.get("code_snippet") or ""
    if not code:
        raise NotEnoughEvidence("no code snippet to compare the answer with")
    warnings = []
    if not _language_python(payload):
        if not payload.get("allow_unvalidated_language"):
            raise NotEnoughEvidence("the answer scorer is trained and tested on Python only; this code is in another language (not scored)")
        warnings.append("scored with a scorer that is not validated for this language")
    try:
        qtype = (payload.get("ast_metadata") or {}).get("question_type") or payload.get("question_type")
        r = _score.rate(answer, payload.get("generated_question") or "", code, payload.get("facts"), qtype=qtype)
    except _score.ModelUnavailable as e:
        raise NotEnoughEvidence(f"code ownership scorer unavailable: {e}") from e
    if r["guard"]:
        warnings.append(f"rated 1 without the model: {r['guard']}")
    features = {"ko_raw_score": r["score"], "comprehension_rating_1_to_5": r["rating"], "guard": r["guard"], **r["features"]}
    if passive:
        features.update({k: v for k, v in passive["features"].items() if k != "KO_quiz_score"})
    return {"factor": "code_ownership", "score": r["score"], "interval": r["interval"], "features": features, "removed": {},
            "versions": {"score": _score.SCORE_VERSION, **{k: v for k, v in r["model"].items() if k != "version"}}, "warnings": warnings, "model": f"{r['model']['encoder']}+{r['model']['head']}"}


async def async_evaluate(payload, context=None):
    if "student_response" in payload or payload.get("is_timeout"):
        try:
            return evaluate(payload, context)
        except NotEnoughEvidence:
            # no usable answer or no installed model: let the bridge record a fallback instead of inventing a score
            raise
    ctx = context or {}
    mode = ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")
    duration = 0.01 if "pytest" in sys.modules else None
    sim = _load("ko_simulate", "simulate.py")
    return await sim.async_simulate(payload=payload, mode=mode, duration_seconds=duration)


def generate_many(files, student_id="", sprint_id="", count=10):
    """Phase 1 for a whole batch: up to ``count`` distinct questions about the student's own code."""
    return _quiz.generate_many(files or [], student_id, sprint_id, count)
