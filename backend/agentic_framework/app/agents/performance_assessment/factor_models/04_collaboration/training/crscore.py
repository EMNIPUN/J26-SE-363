"""Loader for the CRScore human study (phase 2): human ratings of code review comments, MIT, github.com/atharva-naik/CRScore.

Ratings are 1-5 on three scales: conciseness (Con), comprehensiveness (Comp) and relevance (Rel). The reviewed items are comments written by ten
"systems": nine models and ``msg``, the original human reviewer comment. Each diff appears with several systems, so splits must group by diff.
Files live in data/crscore/ (not committed); see download_crscore.py.
"""
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from cleaning import clean_text  # noqa: E402

DATA = HERE.parent / "data" / "crscore"
RATINGS = {"Con (P)": "con", "Comp (R)": "comp", "Rel (F)": "rel"}
BASE = "https://raw.githubusercontent.com/atharva-naik/CRScore/main/human_study/phase2/"
FILES = [f"{l}_{w}_review_qual_final" for l in ("java", "js", "py") for w in ("atharva", "marcus")] + \
        [f"phase2_agreement_annot_{w}" for w in ("Atharva", "Marcus")] + [f"phase2_agreement_annot_last100_{w}" for w in ("Atharva", "Marcus")]


def _tidy(path, **extra):
    d = pd.read_csv(path)
    d["id"] = d["id"].ffill()
    d["diff"] = d["diff"].ffill()  # the diff is given once per block of comments for the same change
    d = d.rename(columns=RATINGS)
    d = d[d.rel.notna() & d.review.notna() & (d.review.astype(str).str.strip() != "")].copy()
    d["review"] = d.review.astype(str).str.strip()
    for k, v in extra.items():
        d[k] = v
    return d[["id", "system", "review", "con", "comp", "rel", "diff"] + list(extra)]


def load_main():
    """One row per rated comment from the six main files (two raters, three languages)."""
    parts = []
    for lang in ("java", "js", "py"):
        for who in ("atharva", "marcus"):
            parts.append(_tidy(DATA / f"{lang}_{who}_review_qual_final.csv", lang=lang, rater=who))
    d = pd.concat(parts, ignore_index=True)
    d["group"] = d.lang + "-" + d.id.astype(int).astype(str)
    d["human"] = d.system == "msg"
    d["clean"] = d.review.map(clean_text)
    return d


def load_pairs():
    """Comments rated by both annotators (the four agreement files): one row per comment with both raters' ratings."""
    out = []
    for suffix in ("", "_last100"):
        a = _tidy(DATA / f"phase2_agreement_annot{suffix}_Atharva.csv")
        m = _tidy(DATA / f"phase2_agreement_annot{suffix}_Marcus.csv")
        j = a.merge(m, on=["id", "system", "review"], suffixes=("_a", "_m"))
        out.append(j)
    j = pd.concat(out, ignore_index=True).drop_duplicates(["id", "system", "review"])
    return j
