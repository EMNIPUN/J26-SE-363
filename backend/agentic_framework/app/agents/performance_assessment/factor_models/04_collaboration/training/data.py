"""Loaders for the public review-comment datasets and the student texts (Collaboration, step 1: the comment-substance scorer).

Public data (downloaded by ``download_data.py`` into ``data/raw/``, not committed):
- OpenDev / OpenStack Nova, WSU-SEAL/CR-usefulness-EMSE (GPL-3.0): 2,500 comments, ``is_useful`` 1 / 0.
- RevHelper, masud-technope/RevHelper-Replication-Package-MSR2017 (MIT): 1,480 comments, useful / not useful.
Label meaning: a comment is "useful" when the code author acted on it. That is related to, not the same as, "substantive".
"""
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
COLLAB = HERE.parent
RAW = COLLAB / "data" / "raw"
sys.path.insert(0, str(COLLAB))
from cleaning import clean_text  # noqa: E402

FM = COLLAB.parent
SIM = FM / "dataset" / "synthetic_students" / "out"
EVID = FM / "dataset" / "evidence"


def norm(s):
    return re.sub(r"\W+", " ", str(s).lower()).strip()


def load_opendev():
    d = pd.read_csv(RAW / "opendev.csv", low_memory=False)[["comment_id", "change_id", "is_useful", "message"]]
    d = d.rename(columns={"comment_id": "id", "message": "text", "change_id": "group", "is_useful": "y"})
    d["source"] = "opendev"
    return d


def load_revhelper():
    rows = []
    for part, files in (("train", ("revhelper_train_corpus-useful", "revhelper_train_corpus-non-useful")), ("val", ("revhelper_val_corpus-useful", "revhelper_val_corpus-non-useful"))):
        for f, y in zip(files, (1, 0)):
            for line in (RAW / f"{f}.txt").read_text(encoding="utf-8", errors="replace").split("\n"):
                m = re.match(r"^(\S+-\d+-n?u)\s*[|\t ]*(.*)$", line)
                if m and m.group(2).strip():
                    rows.append((m.group(1), m.group(1).split("-")[1], y, m.group(2), "revhelper", part))
    d = pd.DataFrame(rows, columns=["id", "group", "y", "text", "source", "part"])
    return d


def with_clean(d):
    d = d.copy()
    d["clean"] = d.text.map(clean_text)
    return d


def public_pool():
    """Both public sets, cleaned like the pipeline cleans student text; RevHelper texts also in OpenDev are dropped from RevHelper."""
    od, rh = with_clean(load_opendev()), with_clean(load_revhelper())
    seen = set(od.text.map(norm))
    rh = rh[~rh.text.map(norm).isin(seen)]
    return od, rh


def student_texts():
    """Reviews and comments written in the students' repositories: real (public pseudonymised evidence) and simulated."""
    out = []
    for name, path, who, kind in (("real", EVID / "pr_reviews.csv", "reviewer_id", "review"), ("real", EVID / "pr_comments.csv", "author_id", "comment"),
                                  ("simulated", SIM / "reviews_simulated.csv", "reviewer_id", "review"), ("simulated", SIM / "comments_simulated.csv", "author_id", "comment")):
        d = pd.read_csv(path).fillna("")
        for r in d.itertuples():
            if str(r.body).strip():
                out.append((name, kind, getattr(r, who), r.body))
    return with_clean(pd.DataFrame(out, columns=["source", "kind", "author", "text"]))
