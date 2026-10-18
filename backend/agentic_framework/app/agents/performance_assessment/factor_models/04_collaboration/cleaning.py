"""Collaboration: which reviews and comments count, and how their text is cleaned before it is scored.

Rules:
- Only the student's own contributions on other people's pull requests count. Bot accounts, self-replies and comments on
  one's own pull request do not.
- Text is cleaned before scoring: quoted replies (`> ...`), fenced code blocks, inline code, links, mentions, emoji and
  markdown symbols are removed, so quoting someone, pasting a stack trace or adding links cannot make a comment look
  substantive. A comment where one word makes up most of the text is padding and scores zero.
- Approvals and one-word replies ("LGTM", "ok", "👍") score zero.
- The substantiveness rule here is the rule-based stand-in for the proposal's encoder; the encoder takes the same cleaned text.
- Not used: the share of files a student touches that teammates also touch. It depends on what teammates do, not on the
  student, so it is left out of the features.

Features: Co_PRC_depth mean substantiveness of review text; Co_IC_depth of discussion comments; Co_MC replies and
mentions; Co_PCount distinct pull requests engaged with (plus merges for others); Co_CCount reviews and comments;
Co_IR share of own pull requests resolved; Co_prs_opened / Co_prs_merged / Co_prs_merged_for_others.
"""

import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.lines import CLEANING_VERSION  # noqa: E402

FEATURES_VERSION = "collaboration/1"
FEATURE_NAMES = ["Co_PRC_depth", "Co_IC_depth", "Co_MC", "Co_PCount", "Co_CCount", "Co_IR", "Co_prs_opened", "Co_prs_merged", "Co_prs_merged_for_others"]

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
QUOTE = re.compile(r"^\s*>.*$", re.M)
URL = re.compile(r"https?://\S+")
MENTION = re.compile(r"(?<![\w@])@[\w-]{2,39}")
SYMBOLS = re.compile(r"[#*_~|]+")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")
APPROVAL_ONLY = re.compile(r"^\W*(lgtm|ok(ay)?|good|great|nice|done|approved?|well done|all good|looks good|thanks?|ty|\+1)\W*$", re.I)
TECHNICAL = re.compile(r"\.(js|ts|jsx|tsx|java|py|css)\b|line \d+|function|endpoint|null|undefined|error|exception|query|index|validation|refactor|test|transaction|lock|race|thread|injection|escape", re.I)
BOT = re.compile(r"(\[bot\]$)|^(copilot|github-actions|vercel|netlify)", re.I)


def clean_text(body):
    """Prose only: no quotes, code, links, mentions, emoji or markdown symbols."""
    text = FENCE.sub(" ", body or "")
    text = QUOTE.sub(" ", text)
    text = INLINE.sub(" ", text)
    text = URL.sub(" ", text)
    text = MENTION.sub(" ", text)
    text = EMOJI.sub(" ", text)
    text = SYMBOLS.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_padding(text):
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
    if len(words) < 6:
        return False
    return Counter(words).most_common(1)[0][1] / len(words) > 0.5


def substance(body):
    """0-1 substantiveness of a review or comment, from its cleaned text."""
    text = clean_text(body)
    words = len(text.split())
    if words < 3 or APPROVAL_ONLY.match(text) or is_padding(text):
        return 0.0
    technical = TECHNICAL.search(body or "") is not None  # code mentions in the original still show the comment is technical
    return round(min(1.0, 0.2 + 0.6 * min(words, 40) / 40 + (0.2 if technical else 0.0)), 3)


def featurize(evidence):
    schema.validate(evidence)
    me = evidence["student_id"]
    reviews = [r for r in evidence.get("reviews", []) if r.get("reviewer") == me and r.get("pr_author") != me and not BOT.search(r.get("reviewer") or "")]
    comments = [m for m in evidence.get("comments", []) if m.get("author") == me and m.get("pr_author") != me]
    review_texts = [r["body"] for r in reviews if r.get("body")] + [m["body"] for m in comments if m.get("kind") == "review_comment"]
    discussion = [m["body"] for m in comments if m.get("kind") == "discussion"]
    merged_for_others = int(evidence.get("merged_for_others", 0))
    reviewed_prs = {r["pr_id"] for r in reviews if r.get("pr_id")} | {m["pr_id"] for m in comments if m.get("pr_id")}
    own = [p for p in evidence.get("pull_requests", []) if p.get("author") == me]
    resolved = [p for p in own if p.get("merged_at") or p.get("closed_at")]
    mean = lambda xs: round(statistics.mean(xs), 4) if xs else 0.0  # noqa: E731
    features = {
        "Co_PRC_depth": mean([substance(t) for t in review_texts]),
        "Co_IC_depth": mean([substance(t) for t in discussion]),
        "Co_MC": sum(int(bool(m.get("is_reply"))) + min(1, int(m.get("mentions", 0))) for m in comments),
        "Co_PCount": len(reviewed_prs) + merged_for_others if reviewed_prs else len(reviews) + merged_for_others,
        "Co_CCount": len(comments) + sum(1 for r in reviews if r.get("body")),
        "Co_IR": round(len(resolved) / len(own), 4) if own else None,
        "Co_prs_opened": len(own),
        "Co_prs_merged": len([p for p in own if p.get("merged_at")]),
        "Co_prs_merged_for_others": merged_for_others,
    }
    warnings = []
    if not evidence.get("pull_requests") and not evidence.get("reviews"):
        warnings.append("this team shows no pull-request activity in the sprint; collaboration cannot be read from reviews")
    return {"features": features, "removed": {}, "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
