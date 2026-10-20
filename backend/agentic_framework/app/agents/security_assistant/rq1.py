"""RQ1 comparison: scanner only versus scanner + LLM, on the seeded repositories.

    python -m app.agents.security_assistant.rq1 --repo vuln_py_repo=findings.json,interpreted.json [--repo NAME=findings.json] \\
            [--seeded-results seeded_results.json] [--out DIR]

Ground truth for the seeded repositories is `tools/tests/fixtures/PLANTED_BUGS.md`. A finding is a *true positive* when it
matches a planted bug: same category, same file (by name) and a line the bug lists (a bug without a line matches on file
alone). Every other finding is counted as a false positive, which is a strict reading: a scanner can report a real problem the
team did not plant (the report says so in `notes`). The LLM columns count only findings whose status is "confirmed"; "uncertain"
is reported separately and not counted as confirmed.

The second suite is the deliberate false positives in `interpreter/seeded/cases.json` (5 real, 5 look-alikes that are
safe). Scanner only reports all 10. The LLM columns for it come only from a saved run
(`python -m app.agents.security_assistant.interpreter.evaluate_seeded --live --save seeded_results.json`).

Nothing here calls an LLM and nothing is invented: a repository without a saved scan, or a suite without saved LLM results,
gets a row that says so with empty numbers.

Outputs in --out: rq1_comparison.csv (one row per repo and suite plus a TOTAL row), rq1_findings.csv (one row per finding),
rq1_cases.csv (one row per deliberate false positive).
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.agents.security_assistant.interpreter.seeded import load_cases

PLANTED = Path(__file__).parent / "tools" / "tests" / "fixtures" / "PLANTED_BUGS.md"
CATEGORIES = {"V1", "V2", "V3", "V4", "V5"}
COLUMNS = ["suite", "name", "run", "findings_analysed", "planted_expected", "planted_known_miss",
           "scanner_only_reported", "scanner_only_tp", "scanner_only_fp", "scanner_only_precision",
           "scanner_only_bugs_found", "scanner_only_recall",
           "llm_confirmed", "llm_dismissed", "llm_uncertain", "llm_tp_kept", "llm_fp_kept", "llm_precision",
           "llm_fp_removed", "llm_true_findings_dismissed", "llm_dismissed_file_only", "llm_v5_dismissed_unreachable",
           "llm_bugs_found", "llm_bugs_set_aside_unreachable", "llm_recall", "notes"]


@dataclass
class Bug:
    repo: str
    number: int
    category: str
    text: str
    file: str | None
    lines: set[int]  # empty = any line
    needs_codeql: bool
    known_miss: bool
    expected: str = ""  # the "Expected from" cell: tools and rule ids the table says should report it


def _lines(spec: str | None) -> set[int]:
    out: set[int] = set()
    for part in (spec or "").split(","):
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        if m:
            out.update(range(int(m.group(1)), int(m.group(2) or m.group(1)) + 1))
    return out


def parse_planted(path: Path = PLANTED) -> dict[str, list[Bug]]:
    """The tables of PLANTED_BUGS.md as {repo name: bugs}."""
    repos: dict[str, list[Bug]] = {}
    current = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        header = re.match(r"^## (vuln_\w+)", line)
        if header:
            current = header.group(1)
            repos[current] = []
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if current is None or len(cells) < 6 or not cells[0].isdigit() or cells[1] not in CATEGORIES:
            continue
        where = cells[3]
        m = re.search(r"`?([\w./-]+\.\w+)`?(?::(\d+(?:[-,]\d+)*))?", where)
        repos[current].append(Bug(current, int(cells[0]), cells[1], cells[2], m.group(1) if m else None,
                                  _lines(m.group(2)) if m else set(), cells[5].lower().startswith("yes"),
                                  "not detected" in cells[4].lower(), cells[4]))
    return repos


def matches(bug: Bug, category: str, file_path: str | None, line: int | None) -> bool:
    if bug.category != category or not bug.file or not file_path:
        return False
    if Path(file_path).name != Path(bug.file).name:
        return False
    # a finding without a line (a dependency advisory in a manifest) matches on file alone, whatever lines the bug lists
    return not bug.lines or line is None or line in bug.lines


@dataclass
class Item:
    category: str
    file_path: str | None
    line: int | None
    rule_id: str
    status: str | None  # confirmed | dismissed | uncertain | None = not interpreted
    matched: list[int] = field(default_factory=list)


def _ratio(a: int, b: int) -> str:
    return f"{a / b:.3f}" if b else ""


def evaluate_repo(name: str, bugs: list[Bug], items: list[Item], codeql_ran: bool, llm: bool, run: str) -> dict:
    expected = [b for b in bugs if not b.known_miss and (codeql_ran or not b.needs_codeql)]
    for it in items:
        it.matched = [b.number for b in bugs if matches(b, it.category, it.file_path, it.line)]
    tp = [i for i in items if i.matched]
    row = {"suite": "seeded repo", "name": name, "run": run, "findings_analysed": len(items),
           "planted_expected": len(expected), "planted_known_miss": sum(b.known_miss for b in bugs),
           "scanner_only_reported": len(items), "scanner_only_tp": len(tp), "scanner_only_fp": len(items) - len(tp),
           "scanner_only_precision": _ratio(len(tp), len(items))}
    found = {n for i in items for n in i.matched} & {b.number for b in expected}
    row["scanner_only_bugs_found"], row["scanner_only_recall"] = len(found), _ratio(len(found), len(expected))
    notes = []
    if not codeql_ran:
        notes.append("CodeQL did not run: its planted bugs are not expected")
    if any(i.matched and any(b.file and not b.lines for b in bugs if b.number in i.matched) for i in items):
        notes.append("a bug without a line (dependency, history) is matched on file alone")
    if len(items) - len(tp):
        notes.append("'fp' = not in PLANTED_BUGS.md; some may be real problems nobody planted")
    if llm:
        conf = [i for i in items if i.status == "confirmed"]
        dis = [i for i in items if i.status == "dismissed"]
        unc = [i for i in items if i.status == "uncertain"]
        # A V5 dismissal means "the vulnerable package is not reachable from the project's code": a judgement about use, not a
        # claim that the advisory is wrong. It is counted in its own column and does not count as lost recall.
        v5_dis = [i for i in dis if i.category == "V5" and i.matched]
        other_dis = [i for i in dis if i.matched and i.category != "V5"]
        expected_nums = {b.number for b in expected}
        found_llm = {n for i in conf for n in i.matched} & expected_nums
        set_aside = ({n for i in v5_dis for n in i.matched} & expected_nums) - found_llm  # only reachable-or-not dismissals left
        row.update({"llm_confirmed": len(conf), "llm_dismissed": len(dis), "llm_uncertain": len(unc),
                    "llm_tp_kept": sum(bool(i.matched) for i in conf), "llm_fp_kept": sum(not i.matched for i in conf),
                    "llm_precision": _ratio(sum(bool(i.matched) for i in conf), len(conf)),
                    "llm_fp_removed": sum(not i.matched for i in dis),
                    "llm_true_findings_dismissed": len(other_dis),
                    "llm_dismissed_file_only": sum(all(not b.lines for b in bugs if b.number in i.matched) for i in other_dis),
                    "llm_v5_dismissed_unreachable": len(v5_dis),
                    "llm_bugs_found": len(found_llm), "llm_bugs_set_aside_unreachable": len(set_aside),
                    "llm_recall": _ratio(len(found_llm), len(expected) - len(set_aside))})
        if v5_dis:
            notes.append(f"{len(v5_dis)} dependency finding(s) matching planted bugs were dismissed as unreachable (own column, not lost "
                         f"recall); {len(set_aside)} planted bug(s) have only such dismissals and are left out of the recall denominator")
        if other_dis:
            notes.append(f"the LLM dismissed {len(other_dis)} non-dependency finding(s) that match planted bugs (lost true positives)")
            if row["llm_dismissed_file_only"]:
                notes.append(f"{row['llm_dismissed_file_only']} of them match a bug only by file, so the ground truth cannot judge them")
    else:
        notes.append("no saved LLM run for this repository: scanner-only columns only")
    row["notes"] = "; ".join(notes)
    return row


def items_from_report(findings_doc: dict, report: dict) -> list[Item]:
    """Items from an `assess` report.json: its findings carry one status per group, not the members, so the scan is grouped again
    with the same deterministic `dedupe` the run used (the group ids are identical) and every member inherits its group's status."""
    from app.agents.security_assistant.dedupe import dedupe
    from app.agents.security_assistant.report import from_json

    status = {f["group_id"]: f["status"] for f in report["findings"]}
    groups, _ = dedupe(from_json(json.dumps(findings_doc))[0].findings)
    return [Item(m.category.value, m.file_path, m.line, m.rule_id, status.get(g.id)) for g in groups for m in g.members]


def items_from(findings_doc: dict | None, interpreted: dict | None) -> list[Item]:
    if interpreted is not None and "report_version" in interpreted:
        return items_from_report(findings_doc, interpreted)
    if interpreted is not None:  # every member of a group inherits the group's status
        return [Item(m["category"], m["file_path"], m["line"], m["rule_id"], g["result"]["status"])
                for g in interpreted["groups"] for m in g["members"]]
    return [Item(f["category"], f.get("file_path"), f.get("line"), f["rule_id"], None) for f in (findings_doc or {})["findings"]]


def codeql_succeeded(findings_doc: dict | None) -> bool:
    return any(r["tool"] == "codeql" and r["status"] == "succeeded" for r in (findings_doc or {}).get("runs", []))


def seeded_suite(results: dict | None) -> tuple[dict, list[dict]]:
    cases = load_cases()
    truth = {c.id: c.ground_truth for c in cases}
    real = sum(t == "confirmed" for t in truth.values())
    row = {"suite": "deliberate false positives", "name": "interpreter/seeded/cases.json", "findings_analysed": len(cases),
           "run": "scanner only", "scanner_only_reported": len(cases), "scanner_only_tp": real, "scanner_only_fp": len(cases) - real,
           "scanner_only_precision": _ratio(real, len(cases))}
    detail = [{"case": c.id, "category": c.finding.category.value, "ground_truth": c.ground_truth, "scanner_only": "reported",
               "llm_status": "", "llm_correct": ""} for c in cases]
    if results is None:
        row["notes"] = ("no saved LLM result: run interpreter.evaluate_seeded --live --save FILE and pass --seeded-results; "
                        "no number is invented")
        return row, detail
    status = {r["id"]: r for r in results["cases"]}
    for d in detail:
        r = status.get(d["case"])
        if r:
            d["llm_status"], d["llm_correct"] = r["status"], str(r["status"] == d["ground_truth"])
    ran = [d for d in detail if d["llm_status"]]
    conf = [d for d in ran if d["llm_status"] == "confirmed"]
    row.update({"run": f"{results['model']}" + ("" if results.get("live") else " (MOCK ORACLE - not a model result)"),
                "llm_confirmed": len(conf), "llm_dismissed": sum(d["llm_status"] == "dismissed" for d in ran),
                "llm_uncertain": sum(d["llm_status"] == "uncertain" for d in ran),
                "llm_tp_kept": sum(d["ground_truth"] == "confirmed" for d in conf),
                "llm_fp_kept": sum(d["ground_truth"] == "dismissed" for d in conf),
                "llm_precision": _ratio(sum(d["ground_truth"] == "confirmed" for d in conf), len(conf)),
                "llm_fp_removed": sum(d["ground_truth"] == "dismissed" and d["llm_status"] == "dismissed" for d in ran),
                "llm_true_findings_dismissed": sum(d["ground_truth"] == "confirmed" and d["llm_status"] == "dismissed" for d in ran),
                "notes": f"{len(ran)} of {len(cases)} cases have a saved LLM result"})
    return row, detail


def total_row(rows: list[dict]) -> dict | None:
    done = [r for r in rows if r["suite"] == "seeded repo" and "llm_confirmed" in r]
    if not done:
        return None
    total = {c: "" for c in COLUMNS}
    total.update({"suite": "seeded repo", "name": "TOTAL (repos with a saved LLM run)", "run": "see rows"})
    for col in ("findings_analysed", "planted_expected", "planted_known_miss", "scanner_only_reported", "scanner_only_tp",
                "scanner_only_fp", "scanner_only_bugs_found", "llm_confirmed", "llm_dismissed", "llm_uncertain", "llm_tp_kept",
                "llm_fp_kept", "llm_fp_removed", "llm_true_findings_dismissed", "llm_dismissed_file_only",
                "llm_v5_dismissed_unreachable", "llm_bugs_found", "llm_bugs_set_aside_unreachable"):
        total[col] = sum(int(r[col]) for r in done)
    total["scanner_only_precision"] = _ratio(total["scanner_only_tp"], total["scanner_only_reported"])
    total["llm_precision"] = _ratio(total["llm_tp_kept"], total["llm_confirmed"])
    total["scanner_only_recall"] = _ratio(total["scanner_only_bugs_found"], total["planted_expected"])
    total["llm_recall"] = _ratio(total["llm_bugs_found"], total["planted_expected"] - total["llm_bugs_set_aside_unreachable"])
    return total


def run_comparison(repo_args: list[str], seeded_results: Path | None, planted: Path = PLANTED) -> tuple[list[dict], list[dict], list[dict]]:
    bugs_by_repo = parse_planted(planted)
    given: dict[str, tuple[dict | None, dict | None]] = {}
    for arg in repo_args:
        name, _, files = arg.partition("=")
        if name not in bugs_by_repo:
            raise ValueError(f"unknown repository {name!r}; PLANTED_BUGS.md lists {', '.join(bugs_by_repo)}")
        paths = [p for p in files.split(",") if p]
        findings = json.loads(Path(paths[0]).read_text(encoding="utf-8")) if paths else None
        interpreted = json.loads(Path(paths[1]).read_text(encoding="utf-8")) if len(paths) > 1 else None
        given[name] = (findings, interpreted)
    rows, details = [], []
    for name, bugs in bugs_by_repo.items():
        findings, interpreted = given.get(name, (None, None))
        if findings is None and interpreted is None:
            rows.append({"suite": "seeded repo", "name": name, "run": "none", "planted_expected": len([b for b in bugs if not b.known_miss]),
                         "planted_known_miss": sum(b.known_miss for b in bugs),
                         "notes": "no saved scan for this repository: nothing is computed (a scan needs CodeQL and a Docker image)"})
            continue
        items = items_from(findings, interpreted)
        meta = (interpreted or {}).get("meta", {})
        if interpreted and "report_version" in interpreted:  # an assess report.json
            meta = {"model": meta.get("llm_model"), "prompt_version": meta.get("interpreter_prompt")}
        run = (f"{meta.get('model')} / {meta.get('prompt_version')}" if interpreted else "scanner only")
        row = evaluate_repo(name, bugs, items, codeql_succeeded(findings), interpreted is not None, run)
        if interpreted and meta.get("only_category"):
            row["notes"] += f"; LLM run limited to {','.join(meta['only_category'])}"
        rows.append(row)
        for it in items:
            details.append({"repo": name, "category": it.category, "rule_id": it.rule_id, "file": it.file_path or "", "line": it.line or "",
                            "matches_planted_bug": ",".join(map(str, it.matched)), "ground_truth": "true positive" if it.matched else "not planted",
                            "llm_status": it.status or ""})
    suite_row, case_rows = seeded_suite(json.loads(Path(seeded_results).read_text(encoding="utf-8")) if seeded_results else None)
    rows.append(suite_row)
    if (t := total_row(rows)) is not None:
        rows.append(t)
    return rows, details, case_rows


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in columns} for r in rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", action="append", default=[], metavar="NAME=findings.json[,interpreted.json]")
    ap.add_argument("--seeded-results", type=Path)
    ap.add_argument("--planted", type=Path, default=PLANTED)
    ap.add_argument("--out", type=Path, default=Path("scan_output") / "rq1")
    args = ap.parse_args(argv)
    try:
        rows, details, cases = run_comparison(args.repo, args.seeded_results, args.planted)
    except (ValueError, OSError, KeyError) as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 3
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "rq1_comparison.csv", rows, COLUMNS)
    write_csv(args.out / "rq1_findings.csv", details, ["repo", "category", "rule_id", "file", "line", "matches_planted_bug", "ground_truth", "llm_status"])
    write_csv(args.out / "rq1_cases.csv", cases, ["case", "category", "ground_truth", "scanner_only", "llm_status", "llm_correct"])
    for r in rows:
        print(f"{r['suite']:<27}{r['name'][:38]:<39}scanner-only {r.get('scanner_only_tp', '-')}/{r.get('scanner_only_reported', '-')} "
              f"(precision {r.get('scanner_only_precision') or '-'}, fp {r.get('scanner_only_fp', '-')})"
              + (f" | +LLM confirmed {r['llm_confirmed']}: precision {r.get('llm_precision') or '-'}, fp {r.get('llm_fp_kept', '-')}"
                 if r.get("llm_confirmed") != "" and "llm_confirmed" in r else ""))
    print(f"Wrote {args.out / 'rq1_comparison.csv'}, rq1_findings.csv and rq1_cases.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
