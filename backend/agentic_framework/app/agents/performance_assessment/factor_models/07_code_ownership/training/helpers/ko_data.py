"""Data, splits and embeddings for the Code Ownership experiments (PROTOCOL.md).

    d = load()                          216 answers with facts, labels (score = (rating - 1) / 4), roles (dev / test) and dev folds
    E = embeddings("unixcoder", d)      cached frozen-encoder vectors for answer, question, code, reference and the joint question+answer text
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
KO = TRAIN.parent
sys.path.insert(0, str(KO))
sys.path.append(str(KO.parent / "ml_lib"))
import ko_features as F  # noqa: E402

DATASET = TRAIN / "dataset"
CACHE = DATASET / "cache"
SEED = 20261019
N_FOLDS = 5
PARTS = ("ans", "ques", "code", "ref", "joint")


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load():
    d = pd.read_csv(DATASET / "ownership_qa.csv")
    sn = pd.read_csv(DATASET / "snippets.csv").set_index("snippet_id")
    d["facts"] = d.snippet_id.map(lambda s: json.loads(sn.loc[s, "facts"]))
    d["score"] = (d.rating - 1) / 4
    d["score_independent"] = (d.rating_independent - 1) / 4
    d["score_mean"] = (d.score + d.score_independent) / 2
    d["reference"] = [F.reference_text(r.facts, r.function) for r in d.itertuples()]
    d["joint"] = d.question + " " + d.answer
    d["role"] = "dev"
    # final test: per question type the function with the lowest hash of "<snippet_id>final-test"
    for kind, g in d.groupby("question_type"):
        ids = sorted(g.snippet_id.unique(), key=lambda s: _hash(s + "final-test"))
        d.loc[d.snippet_id == ids[0], "role"] = "test"
    # dev folds: functions dealt round-robin within each question type in hash order, so each fold holds all types
    d["fold"] = -1
    dev = d[d.role == "dev"]
    k = 0
    for kind in sorted(dev.question_type.unique()):
        ids = sorted(dev[dev.question_type == kind].snippet_id.unique(), key=lambda s: _hash(s + "fold"))
        for s in ids:
            d.loc[d.snippet_id == s, "fold"] = k % N_FOLDS
            k += 1
    return d.reset_index(drop=True)


def embeddings(key, d, threads=8):
    """{part: (n, dim)} for the rows of d; computed once per encoder and cached by text hash."""
    from embedder import Encoder
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.json.npz"
    store = dict(np.load(path, allow_pickle=True)) if path.exists() else {}
    texts = {"ans": d.answer, "ques": d.question, "code": d.code, "ref": d.reference, "joint": d.joint}
    enc, new = None, False
    out = {}
    for part, col in texts.items():
        hs = [_hash(t) for t in col]
        missing = sorted({h: t for h, t in zip(hs, col) if h not in store}.items())
        if missing:
            enc = enc or Encoder(key, threads=threads)
            vecs = enc.embed([t for _, t in missing])
            for (h, _), v in zip(missing, vecs):
                store[h] = v
            new = True
        out[part] = np.vstack([store[h] for h in hs])
    if new:
        np.savez(path, **store)
    return out


def hand_features(d):
    return pd.DataFrame([F.featurize(r.answer, r.question, r.code, r.facts, r.question_type) for r in d.itertuples()])[F.FEATURE_NAMES]


def feature_sets(E, H=None):
    return F.feature_sets(E, H)
