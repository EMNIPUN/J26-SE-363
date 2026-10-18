"""Line-level cleaning shared by every factor package.

Turns a file path and a unified diff into counts of the lines that are real work, and separates everything else.
No model, no network, no language model: plain deterministic code, so training and the agent get the same answer.

    kind = classify_path("src/app.jsx")                       # code | test | docs | config | generated | asset | data
    stats = stats_from_patch("src/app.jsx", patch_text)       # added / deleted lines by type
    clean_added, clean_deleted = clean_counts(kind, stats)    # lines that count as work

Line types (for the lines a diff adds or deletes):
    code         a line with something executable or declarative in it
    comment      a comment-only line, a docstring line, or commented-out code
    blank        an empty or whitespace-only line
    format_only  a line that only moved or was re-indented: the same text (ignoring whitespace) was also deleted or
                 added in the same file's diff
Only `code` lines in `code` and `test` files count as work. Documentation, configuration, generated files,
assets and data files never count.

Limits (written down so nobody trusts this more than it deserves):
- Comment detection looks at one line at a time with a small state for block comments and docstrings. A diff shows
  only changed lines, so a block comment that began before the changed region is recognised only when its lines start
  with `*` (the usual style).
- Code with a trailing comment counts as code.
- Moves between files, and copy-paste from another repository, are not detected.
- Format-only detection ignores very short lines (such as a lone `}`), which count as ordinary code.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

CLEANING_VERSION = "1.0.0"

GENERATED = re.compile(
    r"(^|/)(node_modules|dist|build|out|\.next|coverage|vendor|target|\.gradle|__pycache__|\.idea|\.vscode|\.vs|bin|obj"
    r"|\.mvn|docker-data|postgres-data|pgdata|mongo-data|uploads)/"
    r"|(^|/)(mvnw|mvnw\.cmd|gradlew|gradlew\.bat|\.DS_Store)$|\.log$"
    r"|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|composer\.lock|poetry\.lock|Pipfile\.lock)$"
    r"|\.min\.(js|css)$|\.map$|\.bundle\.js$|\.pyc$|\.class$",
    re.IGNORECASE,
)
ASSET = re.compile(r"\.(png|jpe?g|gif|svg|ico|webp|bmp|mp4|mp3|wav|woff2?|ttf|eot|otf|pdf|zip|jar|apk|psd)$", re.I)
DATA = re.compile(r"\.(csv|tsv|xlsx?|sqlite|db|geojson)$", re.I)
CODE = re.compile(r"\.(jsx?|tsx?|mjs|cjs|py|java|kt|kts|dart|go|cs|php|rb|vue|svelte|swift|c|cpp|h|hpp|sql|html?|css|scss|sass|less)$", re.I)
TEST = re.compile(r"(^|/)(tests?|__tests__|spec|androidTest)/|\.(test|spec)\.\w+$|(^|/)test_[^/]*\.\w+$|_test\.\w+$|Tests?\.\w+$", re.I)
DOCS = re.compile(r"\.(md|markdown|rst|txt|adoc)$|(^|/)(README|CHANGELOG|LICENSE)[^/]*$", re.I)

SOURCE_KINDS = ("code", "test")  # the only kinds whose lines can count as work


def classify_path(path):
    """code | test | docs | config | generated | asset | data."""
    if GENERATED.search(path):
        return "generated"
    if ASSET.search(path):
        return "asset"
    if DATA.search(path):
        return "data"
    if DOCS.search(path):
        return "docs"
    if TEST.search(path) and CODE.search(path):
        return "test"
    if CODE.search(path):
        return "code"
    return "config"


@dataclass
class Style:
    line_markers: tuple = ()
    blocks: tuple = ()          # ((start, end), ...)
    docstrings: bool = False
    star_continuation: bool = False  # lines starting with * inside a block whose start was not in the diff


C_LIKE = Style(("//",), (("/*", "*/"),), star_continuation=True)
CSS = Style((), (("/*", "*/"),), star_continuation=True)
HASH = Style(("#",), (), docstrings=True)
HTML = Style((), (("<!--", "-->"),))
VUE = Style(("//",), (("/*", "*/"), ("<!--", "-->")), star_continuation=True)
SQL = Style(("--",), (("/*", "*/"),), star_continuation=True)
PHP = Style(("//", "#"), (("/*", "*/"),), star_continuation=True)

STYLE_BY_EXT = {
    **{e: C_LIKE for e in "js jsx ts tsx mjs cjs java kt kts dart go cs swift c cpp h hpp".split()},
    "py": HASH, "rb": HASH, "css": CSS, "scss": CSS, "less": CSS, "sass": C_LIKE,
    "html": HTML, "htm": HTML, "vue": VUE, "svelte": VUE, "sql": SQL, "php": PHP,
}


def style_for(path):
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return STYLE_BY_EXT.get(ext, C_LIKE)


@dataclass
class State:
    block_end: str = None


def classify_line(line, style, state):
    """'blank' | 'comment' | 'code' for one line, updating the block-comment state."""
    s = line.strip()
    if not s:
        return "blank"
    if state.block_end:
        if state.block_end in s:
            after = s.split(state.block_end, 1)[1].strip()
            state.block_end = None
            return "comment" if not after else "code"
        return "comment"
    if style.docstrings and (s.startswith('"""') or s.startswith("'''")):
        delim = s[:3]
        if s.count(delim) < 2:
            state.block_end = delim
        return "comment"
    for start, end in style.blocks:
        if s.startswith(start):
            rest = s[len(start):]
            if end in rest:
                return "comment" if not rest.split(end, 1)[1].strip() else "code"
            state.block_end = end
            return "comment"
    for marker in style.line_markers:
        if s.startswith(marker):
            return "comment"
    if style.star_continuation and (s.startswith("* ") or s == "*" or s.startswith("*/")):
        return "comment"
    return "code"


def _empty():
    return {"code": 0, "comment": 0, "blank": 0, "format_only": 0}


def stats_from_patch(path, patch):
    """Added and deleted line counts by type for one file's unified diff."""
    style = style_for(path)
    add_state, del_state = State(), State()
    added, deleted = _empty(), _empty()
    add_code, del_code = Counter(), Counter()
    in_hunk = False
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            in_hunk = True
            add_state, del_state = State(), State()
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        if raw.startswith("+"):
            kind = classify_line(raw[1:], style, add_state)
            added[kind] += 1
            if kind == "code":
                add_code[re.sub(r"\s+", "", raw[1:])] += 1
        elif raw.startswith("-"):
            kind = classify_line(raw[1:], style, del_state)
            deleted[kind] += 1
            if kind == "code":
                del_code[re.sub(r"\s+", "", raw[1:])] += 1
        else:  # context line: keep the block-comment state in step
            classify_line(raw[1:] if raw.startswith(" ") else raw, style, add_state)
            classify_line(raw[1:] if raw.startswith(" ") else raw, style, del_state)
    for key, n in add_code.items():  # the same text deleted and added in one diff: moved or re-indented, not new work
        if len(key) < 6:
            continue
        moved = min(n, del_code.get(key, 0))
        if moved:
            added["code"] -= moved
            added["format_only"] += moved
            deleted["code"] -= moved
            deleted["format_only"] += moved
            del_code[key] -= moved
    return {"added": added, "deleted": deleted}


def clean_counts(kind, stats):
    """(added, deleted) lines that count as work for a file of this kind."""
    if kind not in SOURCE_KINDS or not stats:
        return 0, 0
    return stats["added"]["code"], stats["deleted"]["code"]


def removed_summary(files):
    """Where the lines went that did not count as work, over many files: {reason: lines} for added lines.

    files: iterable of (kind, stats). Reasons: comment, blank, format_only, docs_or_config, generated_or_data."""
    out = Counter()
    for kind, stats in files:
        if not stats:
            continue
        a = stats["added"]
        total = sum(a.values())
        if kind in SOURCE_KINDS:
            out["comment"] += a["comment"]
            out["blank"] += a["blank"]
            out["format_only"] += a["format_only"]
        elif kind in ("docs", "config"):
            out["docs_or_config"] += total
        else:
            out["generated_or_data"] += total
    return dict(out)


def strip_comments_and_blanks(path, text):
    """The text of a file or added block without comment-only and blank lines (for language-model prompts)."""
    style = style_for(path)
    state = State()
    kept = []
    for line in text.splitlines():
        if classify_line(line, style, state) == "code":
            kept.append(line)
    return "\n".join(kept)


def clean_patch(path, patch):
    """A unified diff reduced to the changed lines that are real work: comment, blank and format-only lines removed,
    headers and hunk markers kept. Used to build the diff a language model reads."""
    style = style_for(path)
    add_state, del_state = State(), State()
    out, in_hunk = [], False
    texts = {"+": Counter(), "-": Counter()}
    rows = []
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            in_hunk = True
            add_state, del_state = State(), State()
            rows.append(("@", raw, None))
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        sign = raw[0] if raw[:1] in "+-" else " "
        body = raw[1:]
        state = add_state if sign in "+ " else del_state
        kind = classify_line(body, style, state)
        if sign == " ":
            classify_line(body, style, del_state)
            continue
        rows.append((sign, raw, kind))
        if kind == "code":
            texts[sign][re.sub(r"\s+", "", body)] += 1
    moved = {k: min(texts["+"][k], texts["-"].get(k, 0)) for k in texts["+"] if len(k) >= 6}
    left = {"+": dict(moved), "-": dict(moved)}  # each side gives up the lines that also appear on the other side
    for sign, raw, kind in rows:
        if sign == "@":
            out.append(raw)
        elif kind == "code":
            key = re.sub(r"\s+", "", raw[1:])
            if left[sign].get(key, 0) > 0:
                left[sign][key] -= 1
                continue
            out.append(raw)
    return "\n".join(out)
