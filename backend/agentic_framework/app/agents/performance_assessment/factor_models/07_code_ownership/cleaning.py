"""Code Ownership: who wrote the code that is still there, counted on real source lines only.

Rules:
- Blame is read with whitespace changes ignored (`git blame -w`), and only lines that are real work count: blank lines,
  comment-only lines, docstrings and commented-out code are not owned. Whole files that are generated, assets, data,
  documentation or configuration are not blamed at all.
- Lines the student added = counted added lines in source files (the same counted lines as Effort).
- Survival = student's surviving counted lines / counted lines the student added, at most 1.
- Primary-owner share = files where the student holds the most surviving counted lines / files with any surviving lines.
- Owned files (quiz candidates) = files where the student holds at least 20 surviving counted lines.
- Quiz snippets are real logic: at least 8 counted lines, not a getter, setter, constructor shell or `toString`.

The ingestion step runs blame and `summarize()` on the repository at its final version and hands the agent a small
`ownership` summary in the evidence; this module turns that summary into features.
"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evidence import schema  # noqa: E402
from evidence.lines import CLEANING_VERSION, SOURCE_KINDS, State, classify_line, classify_path, style_for  # noqa: E402

FEATURES_VERSION = "code_ownership/1"
FEATURE_NAMES = ["KO_survival", "KO_primary_owner_share", "KO_snippet_candidates", "KO_quiz_score"]
OWNED_MIN_LINES = 20
SNIPPET_MIN_LINES = 8
HEADER = re.compile(r"^([0-9a-f]{40}) \d+ \d+")
TRIVIAL_NAME = re.compile(r"^(get|set|is|has)[A-Z_]|^(toString|hashCode|equals|constructor|__init__|__str__|__repr__)$")


def meaningful_blame_counts(porcelain, path):
    """{sha: counted lines} from `git blame --line-porcelain -w` output of one file. Empty for files that are not source."""
    if classify_path(path) not in SOURCE_KINDS:
        return {}
    style, state, counts, current = style_for(path), State(), {}, None
    for line in porcelain.splitlines():
        m = HEADER.match(line)
        if m and not line.startswith("\t"):
            current = m.group(1)
        elif line.startswith("\t") and current:
            if classify_line(line[1:], style, state) == "code":
                counts[current] = counts.get(current, 0) + 1
    return counts


def summarize(per_file, sprint_shas, added_lines, owner_of=None, me=None):
    """Ownership summary from {file: {sha: counted lines}} for the files a student touched.

    sprint_shas: the student's counted commits in the sprint (their surviving lines are what survival measures).
    owner_of / me: optional {sha: student} for every commit in the repository and the student's id, so that primary
    ownership compares students (all of a student's lines in the file) and not single commits."""
    sprint = set(sprint_shas)
    surviving = files = primary = owned = 0
    for counts in per_file.values():
        if not counts:
            continue
        files += 1
        mine_n = sum(n for sha, n in counts.items() if sha in sprint)
        surviving += mine_n
        if mine_n >= OWNED_MIN_LINES:
            owned += 1
        totals = {}
        for sha, n in counts.items():
            who = "me" if sha in sprint or (owner_of and owner_of.get(sha) == me) else (owner_of.get(sha, sha) if owner_of else sha)
            totals[who] = totals.get(who, 0) + n
        top_other = max((n for who, n in totals.items() if who != "me"), default=0)
        if totals.get("me", 0) and totals["me"] >= top_other:
            primary += 1
    return {"added_lines": int(added_lines), "surviving_lines": int(surviving), "files": files, "primary_files": primary, "owned_files": owned}


def snippet_candidates(path, text):
    """Functions worth asking a student about: [{name, start, end, lines}] (1-based lines), real logic only."""
    kind = classify_path(path)
    if kind not in SOURCE_KINDS:
        return []
    style = style_for(path)
    out = []
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        lines = text.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not TRIVIAL_NAME.match(node.name):
                state = State()
                body = lines[node.lineno - 1:node.end_lineno]
                n = sum(1 for ln in body if classify_line(ln, style, state) == "code")
                if n >= SNIPPET_MIN_LINES:
                    out.append({"name": node.name, "start": node.lineno, "end": node.end_lineno, "lines": n})
        return out
    lines = text.splitlines()
    head = re.compile(r"(?:function\s+(\w+)\s*\(|(?:public|private|protected|static|async|\s)+[\w<>\[\],\s]+\s+(\w+)\s*\([^;{]*\)\s*(?:throws [\w, ]+)?\s*\{|(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{)")
    i = 0
    while i < len(lines):
        m = head.search(lines[i])
        name = next((g for g in m.groups() if g), None) if m else None
        if name and lines[i].rstrip().endswith("{") and not TRIVIAL_NAME.match(name):
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0 and j >= i:
                    break
                j += 1
            state = State()
            n = sum(1 for ln in lines[i:j + 1] if classify_line(ln, style, state) == "code")
            if n >= SNIPPET_MIN_LINES:
                out.append({"name": name, "start": i + 1, "end": j + 1, "lines": n})
            i = j + 1
        else:
            i += 1
    return out


def featurize(evidence):
    schema.validate(evidence)
    o = evidence.get("ownership") or {}
    added, surviving, files = o.get("added_lines", 0), o.get("surviving_lines", 0), o.get("files", 0)
    warnings = []
    if not added:
        warnings.append("the student added no counted source lines, so survival is undefined")
    features = {
        "KO_survival": round(min(1.0, surviving / added), 4) if added else None,
        "KO_primary_owner_share": round(o.get("primary_files", 0) / files, 4) if files else None,
        "KO_snippet_candidates": int(o.get("owned_files", 0)),
        "KO_quiz_score": (evidence.get("quiz") or {}).get("score"),
    }
    if features["KO_quiz_score"] is None:
        warnings.append("no quiz score yet: the active part of Code Ownership is pending")
    return {"features": features, "removed": {}, "versions": {"cleaning": CLEANING_VERSION, "features": FEATURES_VERSION}, "warnings": warnings}
