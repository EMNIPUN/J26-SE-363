"""Runtime of the regression factors (Effort, Consistency, Task Complexity): evaluates a JSON model card without scikit-learn.

A card is written by ml_lib/fit_production.py (ridge on transformed features, median imputation, standardisation, optional guard, optional zero rule). This module does only arithmetic
on a feature dict, so the agent needs nothing installed for these three factors.

    result = evaluate(card_path, cleaning_module, payload, context, min_days=0)

``payload`` is either raw evidence (``evidence/1``) or ``{"features": {...}}`` with the factor's own feature names. During a sprint, ``evidence["as_of"]`` (ISO time of the snapshot)
makes the result provisional: counts are to date, the interval widens with the part of the sprint still to come, and a factor that needs a minimum number of days says so instead of scoring.
"""
import json
import math
from datetime import date, datetime
from pathlib import Path


class NotEnoughEvidence(ValueError):
    """The score is not available (the agent's bridge records a fallback and fusion redistributes the weight)."""


def log_signed(x):
    return math.copysign(math.log1p(abs(x)), x)


def _tf(x, kind):
    return {"raw": x, "log": log_signed(x), "one_minus": 1.0 - x}[kind]


class LinearCard:
    def __init__(self, card: dict):
        self.card = card

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def predict(self, features: dict):
        """(score in 0..1, warnings). Missing features are replaced by the training median and reported."""
        c, warnings = self.card, []
        f = dict(features)
        orig_cc = f.get("E_CC")
        g = c.get("guard")
        if g:  # counts credited only as far as the evidence supports them (earlier Effort protocol)
            cc = float(f.get("E_CC") or 0)
            f["E_CC"] = min(cc, max(float(f.get("E_LOC_net_capped") or 0), 0.0) / g["lines_per_commit"])
            f["E_FC"] = min(float(f.get("E_FC") or 0), g["files_per_commit"] * max(cc, 1.0))
        z = c.get("zero_rule")
        if z:
            val = orig_cc if z["column"] == "E_CC" else f.get(z["column"])
            if val is not None and float(val) == z["equals"]:
                return 0.0, ["no activity: the score is 0 by rule"]
        total = c["intercept"]
        for i, spec in enumerate(c["features"]):
            v = f.get(spec["name"])
            if v is None or (isinstance(v, float) and math.isnan(v)):
                x = c["medians"][i]
                warnings.append(f"feature {spec['name']} missing: the training median was used")
            else:
                x = _tf(float(v), spec["transform"])
            total += c["coef"][i] * ((x - c["mean"][i]) / c["scale"][i])
        return min(1.0, max(0.0, total)), warnings

    def interval(self, score, elapsed_fraction=1.0):
        lo, hi = self.card["residual_quantiles"]
        widen = 1.0 + 2.0 * (1.0 - min(1.0, max(0.0, elapsed_fraction)))
        return [round(max(0.0, score + lo * widen), 4), round(min(1.0, score + hi * widen), 4)]


def _elapsed(evidence):
    """(days elapsed, fraction of the sprint elapsed) at evidence['as_of'], or (None, 1.0) when the evidence is final."""
    as_of = evidence.get("as_of")
    if not as_of:
        return None, 1.0
    s = evidence["sprint"]
    start = date.fromisoformat(s["start"])
    now = datetime.fromisoformat(as_of.replace("Z", "+00:00")).date()
    days = max(0, (now - start).days + 1)
    return days, min(1.0, days / max(1, int(s["days"])))


def covers(card_path, features) -> bool:
    """True when ``features`` has every feature the card needs (so a feature payload of an older caller with other names is not scored by mistake)."""
    names = [f["name"] for f in LinearCard.load(card_path).card["features"]]
    z = LinearCard.load(card_path).card.get("zero_rule")
    return isinstance(features, dict) and all(n in features for n in names) and (not z or z["column"] in features or z["column"] == "E_CC")


def evaluate(card_path, cleaning, payload, context=None, *, min_days=0, factor=None):
    card = LinearCard.load(card_path)
    warnings, removed, versions = [], {}, {"model": card.card["version"], "candidate": card.card["candidate"]}
    days, fraction = None, 1.0
    if isinstance(payload, dict) and payload.get("schema") == "evidence/1":
        days, fraction = _elapsed(payload)
        if days is not None and days < min_days:
            raise NotEnoughEvidence(f"{card.card['factor']} needs at least {min_days} days of the sprint; {days} have passed")
        out = cleaning.featurize(payload)
        features, removed, warnings = dict(out["features"]), out.get("removed", {}), list(out.get("warnings", []))
        versions.update(out.get("versions", {}))
    elif isinstance(payload, dict) and isinstance(payload.get("features"), dict):
        features = dict(payload["features"])
    else:
        raise ValueError(f"{card.card['factor']}: the payload is neither evidence/1 nor {{'features': {{...}}}}")
    score, w = card.predict(features)
    warnings += w
    provisional = fraction < 1.0
    if provisional:
        warnings.append(f"provisional: {days} of {payload['sprint']['days']} days of the sprint; counts are to date and the score can still change")
    cv = card.card["cv"]
    if not cv["beats_baseline"]:
        warnings.append(f"validation: this model is not shown to beat the single-feature baseline ({cv['baseline']}); read the score as that baseline's information")
    return {"factor": factor or card.card["factor"], "score": round(score, 4), "interval": card.interval(score, fraction), "features": features, "removed": removed, "versions": versions,
            "warnings": warnings, "provisional": provisional, "sprint_elapsed": round(fraction, 4), "model": f"{card.card['version']}:{card.card['candidate']}"}
