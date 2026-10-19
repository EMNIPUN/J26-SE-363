"""Phase 2 of Code Ownership: rate a student's answer and turn it into KO = (R - 1) / 4 (proposal 3.1.8).

    rate(answer, question, code, facts=None) -> {rating, score, interval, guard, features, model}

Steps: (1) deterministic guards (ko_features.guard: empty, repeats the question, copies the code) rate 1 without the model; (2) the frozen encoder embeds the
answer, question, code, reference explanation and the joint question+answer text; (3) the chosen feature set (model/ko_model.json) goes through the trained
regression head (model/ko_head.joblib); (4) the prediction is clipped to 0-1 and R = 1 + 4 * score.

The trained head and its card are written by training/experiments/exp01_baseline_pipeline (notebook 06). If the encoder, its libraries (torch, transformers,
scikit-learn, joblib) or the trained head are missing, ``ModelUnavailable`` is raised and the factor reports "not available" (the weight is redistributed),
never a guessed score.
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / "model"
SCORE_VERSION = "code-ownership-score/1"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


kf = _load("ko_features_prod", "ko_features.py")
emb = _load("ko_embedder_prod", "embedder.py")
ModelUnavailable = emb.ModelUnavailable
# a saved head refers to the Blocks transformer as ko_blocks.Blocks; register this folder's module under that name so joblib can load it
sys.modules.setdefault("ko_blocks", _load("ko_blocks", "ko_blocks.py"))
_CACHE = {}


def card():
    p = MODEL_DIR / "ko_model.json"
    if not p.exists():
        raise ModelUnavailable("no trained Code Ownership head found (model/ko_model.json): run training/experiments/exp01_baseline_pipeline/06_final_test.ipynb")
    return json.loads(p.read_text(encoding="utf-8"))


def _head():
    if "head" not in _CACHE:
        try:
            import joblib
        except ImportError as e:
            raise ModelUnavailable(f"scikit-learn/joblib are not installed: {e}") from e
        path = MODEL_DIR / "ko_head.joblib"
        if not path.exists():
            raise ModelUnavailable("no trained Code Ownership head found (model/ko_head.joblib)")
        _CACHE["head"] = joblib.load(path)
    return _CACHE["head"]


def _encoder(key, threads=None):
    if key not in _CACHE:
        _CACHE[key] = emb.Encoder(key, threads=threads)
    return _CACHE[key]


def rate(answer, question, code, facts=None, encoder=None, qtype=None):
    """Rate one answer. ``qtype`` is the question type from the quiz (guard, handler, ...). ``encoder`` may be passed in (tests, batch use); otherwise the card's encoder is loaded once and reused."""
    c = card()
    why = kf.guard(answer, question, code)
    hand = kf.featurize(answer or "", question or "", code or "", facts, qtype)
    out = {"guard": why, "features": {f"KO_{k}": v for k, v in hand.items()}, "model": {"encoder": c["encoder"], "feature_set": c["feature_set"], "head": c["head"], "version": SCORE_VERSION}}
    if why:
        out.update({"rating": 1.0, "score": 0.0, "interval": [0.0, 0.0]})
        return out
    import numpy as np
    H = np.array([[hand[n] for n in kf.FEATURE_NAMES]], float)
    if c["encoder"] is None:  # the chosen model uses the hand-built features only: no encoder, no torch
        X = H
    else:
        enc = encoder or _encoder(c["encoder"])
        ref = kf.reference_text(facts, "")
        texts = {"ans": answer, "ques": question or "Explain what this code does.", "code": code, "ref": ref or "Explains what the code does.", "joint": (question or "") + " " + answer}
        keys = list(texts)
        vecs = enc.embed([texts[k] for k in keys])
        E = {k: vecs[i:i + 1] for i, k in enumerate(keys)}
        X = kf.feature_sets(E, H)[c["feature_set"]]
    score = float(np.clip(_head().predict(X)[0], 0.0, 1.0))
    lo, hi = c.get("residual_quantiles", [-0.2, 0.2])
    out.update({"rating": round(1 + 4 * score, 3), "score": round(score, 4), "interval": [round(max(0.0, score + lo), 4), round(min(1.0, score + hi), 4)]})
    return out
