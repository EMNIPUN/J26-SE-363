"""Deterministic filler code for the mock repositories.

The benchmark needs hundreds to thousands of changed lines around the few lines that decide a task. The filler is generic helper,
plumbing, test and style code with identifiers from a neutral vocabulary (no booking, user, payment ...), so it does not accidentally
satisfy an acceptance criterion. It is already "cleaned": no comment lines, no blank lines.
"""

import random
import re

NOUNS = ["record", "entry", "cache", "queue", "token", "label", "page", "row", "item", "config", "buffer", "handler", "filter", "mapper",
         "session", "store", "helper", "registry", "schema", "view", "state", "node", "batch", "window", "cursor", "stream", "bucket",
         "channel", "option", "layout", "panel", "widget", "plan", "slot", "frame", "range", "metric", "offset", "tag", "chunk"]
VERBS = ["build", "parse", "format", "merge", "split", "collect", "resolve", "render", "load", "apply", "convert", "normalise", "reset",
         "prepare", "flush", "wrap", "decode", "encode", "select", "attach", "update", "compare", "extract", "clone", "measure"]
ADJ = ["default", "local", "shared", "pending", "active", "cached", "primary", "inner", "outer", "safe", "base", "raw", "final"]
TYPES = ["String", "int", "long", "boolean", "double"]


class Gen:
    def __init__(self, seed):
        self.r = random.Random(seed)
        self.n = 0

    def noun(self):
        return self.r.choice(NOUNS)

    def name(self):
        self.n += 1
        return f"{self.r.choice(VERBS)}{self.noun().capitalize()}{self.r.choice(['', '', self.r.choice(ADJ).capitalize()])}"

    def var(self):
        return f"{self.r.choice(ADJ)}{self.noun().capitalize()}"

    def num(self):
        return self.r.choice([0, 1, 2, 3, 5, 8, 10, 16, 20, 32, 50, 64, 100, 128, 250, 500, 1000])

    def word(self):
        return self.r.choice(NOUNS + ADJ + VERBS)


def js_block(g, ts=False):
    n, a, b = g.name(), g.var(), g.var()
    ann = ": any" if ts else ""
    k = g.r.randint(0, 5)
    if k == 0:
        return [f"export function {n}({a}{ann}, {b}{ann}) {{", f"  const out = [];", f"  for (const x of {a}) {{ if (x.{g.noun()} > {g.num()}) out.push({b}(x)); }}", "  return out;", "}"]
    if k == 1:
        return [f"const {n} = ({a}{ann}) => {{", f"  if (!{a}) return null;", f"  return {{ ...{a}, {g.noun()}: {g.num()}, {g.noun()}: '{g.word()}' }};", "};"]
    if k == 2:
        return [f"export const {g.var()} = {{", f"  {g.noun()}: {g.num()},", f"  {g.noun()}: '{g.word()}',", f"  {g.noun()}: [{g.num()}, {g.num()}, {g.num()}],", "};"]
    if k == 3:
        return [f"function {n}({a}{ann}) {{", f"  const {b} = new Map();", f"  {a}.forEach((v, i) => {b}.set(v.{g.noun()}, i));", f"  return Array.from({b}.keys()).sort();", "}"]
    if k == 4:
        return [f"async function {n}({a}{ann}) {{", f"  const res = await fetch(`/{g.word()}/${{{a}}}`);", "  if (!res.ok) throw new Error(`failed ${res.status}`);", "  return res.json();", "}"]
    return [f"module.exports.{n} = function ({a}) {{", f"  return {a}.map(x => x.{g.noun()}).filter(Boolean).slice(0, {g.num() or 1});", "};"]


def vue_block(g):
    return js_block(g) if g.r.random() < .5 else [f"<div class=\"{g.noun()}-{g.word()}\" v-if=\"{g.var()}\">", f"  <span>{{{{ {g.var()}.{g.noun()} }}}}</span>", "</div>"]


def py_block(g):
    n, a, b = g.name().lower(), g.var().lower(), g.var().lower()
    k = g.r.randint(0, 4)
    if k == 0:
        return [f"def {n}({a}, {b}=None):", f"    out = []", f"    for x in {a}:", f"        if x.get('{g.noun()}', 0) > {g.num()}:", f"            out.append(x)", "    return out"]
    if k == 1:
        return [f"def {n}({a}):", f"    return {{k: v for k, v in {a}.items() if v is not None}}"]
    if k == 2:
        return [f"class {g.noun().capitalize()}{g.noun().capitalize()}:", f"    def __init__(self, {a}):", f"        self.{b} = {a}", f"        self.{g.noun()} = {g.num()}", f"    def {n}(self):", f"        return self.{b}"]
    if k == 3:
        return [f"{g.noun().upper()}_{g.noun().upper()} = {g.num()}", f"{g.noun().upper()}_{g.noun().upper()} = '{g.word()}'"]
    return [f"def {n}({a}):", f"    parts = str({a}).split('{g.r.choice([',', ':', '/', '-'])}')", f"    return [p.strip() for p in parts if p]"]


def java_block(g, kotlin=False):
    n, a, b = g.name(), g.var(), g.var()
    t = g.r.choice(TYPES)
    if kotlin:
        return [f"fun {n}({a}: List<String>, {b}: Int = {g.num()}): List<String> {{", f"    return {a}.filter {{ it.length > {b} }}.map {{ it.trim() }}", "}"]
    k = g.r.randint(0, 2)
    if k == 0:
        return [f"    public {t} {n}({t} {a}) {{", f"        if ({a} == null) return {a};", f"        return {a};", "    }"]
    if k == 1:
        return [f"    private static final {t} {g.noun().upper()}_{g.word().upper()} = {g.num() if t != 'String' else chr(34) + g.word() + chr(34)};"]
    return [f"    public List<{g.noun().capitalize()}> {n}(List<{g.noun().capitalize()}> {a}) {{", f"        return {a}.stream().filter(x -> x != null).limit({g.num() or 1}).collect(Collectors.toList());", "    }"]


def go_block(g):
    n, a = g.name(), g.var()
    return [f"func {n}({a} []string, limit int) ([]string, error) {{", f"\tif len({a}) == 0 {{ return nil, nil }}", f"\tif limit > len({a}) {{ limit = len({a}) }}", f"\treturn {a}[:limit], nil", "}"]


def css_block(g):
    return [f".{g.noun()}-{g.word()} {{", f"  margin: {g.num() % 24}px {g.num() % 16}px;", f"  padding: {g.num() % 20}px;", f"  display: {g.r.choice(['flex', 'block', 'grid', 'inline-block'])};", "}"]


def sql_block(g):
    return [f"CREATE INDEX idx_{g.noun()}_{g.word()} ON {g.noun()}s ({g.noun()}_id, {g.noun()}_at);"] if g.r.random() < .5 else [f"ALTER TABLE {g.noun()}s ADD COLUMN {g.word()}_{g.noun()} INT NOT NULL DEFAULT {g.num()};"]


def html_block(g):
    return [f"<section class=\"{g.noun()}\">", f"  <h3>{g.word().capitalize()} {g.noun()}</h3>", f"  <p>{g.word()} {g.noun()} {g.word()}</p>", "</section>"]


TEST_JS = lambda g: [f"it('{g.word()} {g.noun()}', () => {{", f"  expect({g.name()}([{g.num()}, {g.num()}])).toEqual([{g.num()}]);", "});"]  # noqa: E731
TEST_PY = lambda g: [f"def test_{g.name().lower()}():", f"    assert {g.name().lower()}([{g.num()}, {g.num()}]) == [{g.num()}]"]  # noqa: E731


def lines_for(path, n, seed, is_test=False):
    """n cleaned lines of plausible code for ``path`` (n >= 0), deterministic in (path, seed)."""
    g = Gen(f"{seed}:{path}")
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    out = []
    while len(out) < n:
        if is_test and ext in ("js", "jsx", "ts", "tsx"):
            out += TEST_JS(g)
        elif is_test and ext == "py":
            out += TEST_PY(g)
        elif ext in ("js", "jsx", "mjs", "cjs"):
            out += js_block(g)
        elif ext in ("ts", "tsx"):
            out += js_block(g, ts=True)
        elif ext == "vue":
            out += vue_block(g)
        elif ext == "py":
            out += py_block(g)
        elif ext == "java":
            out += java_block(g)
        elif ext in ("kt", "kts"):
            out += java_block(g, kotlin=True)
        elif ext == "go":
            out += go_block(g)
        elif ext in ("css", "scss", "sass", "less"):
            out += css_block(g)
        elif ext == "sql":
            out += sql_block(g)
        elif ext in ("html", "htm"):
            out += html_block(g)
        else:
            out += js_block(g)
    return out[:n]


# --- cleaning of the hand-written snippets ----------------------------------------------------------------------------------

_TRAIL = re.compile(r"\s+(//|#)\s.*$")
_COMMENT_ONLY = re.compile(r"^\s*(//|#|--|\*|/\*)")


def strip_snippet(text, keep_prose=False):
    """Snippet lines as a cleaning pass would leave them: comment-only lines and trailing comments removed.

    Returns (code_lines, hints): ``hints`` holds the filename given by a leading ``// path/file.ext`` comment and the code that a
    comment of the form ``// controller: <code>`` carries, which the generator turns into a line of a second file.
    """
    code, extra, header = [], [], None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\s*(?://|#)\s*([\w./-]+\.\w+)\s*$", line)
        if m and header is None and not code:
            header = m.group(1)
            continue
        m = re.match(r"^\s*(?://|#)\s*([\w./-]+\.\w+):\s+(.+)$", line)
        if m and header is None and not code:
            header = m.group(1)
            code.append(m.group(2).strip())
            continue
        m = re.match(r"^\s*(?://|#)\s*(controller|route|view|handler|client|server|api|ui|test)\s*:\s*(.+)$", line, re.I)
        if m:
            extra.append((m.group(1).lower(), m.group(2).strip()))
            continue
        if _COMMENT_ONLY.match(line) and not keep_prose:
            continue
        if not keep_prose and _TRAIL.search(line):
            head = _TRAIL.sub("", line)
            if head.count("'") % 2 == 0 and head.count('"') % 2 == 0 and head.count("`") % 2 == 0:
                line = head
        code.append(line)
    return code, {"header": header, "extra": extra}
