"""Run the LLM Semantic Interpreter over the findings of a scan.

    python -m app.agents.security_assistant.interpret <findings.json> <repo folder> [options]

    --dry-run              print exactly what would be sent (redacted) and how many calls; calls nothing
    --allow-external-llm   required for a real run: without it nothing is sent to any LLM
    --only-category V1,V4  interpret only these categories
    --max-findings N       at most N LLM calls (groups are counted, see below)
    --delay S              seconds to wait between calls (free API tiers need this)
    --retries N            bounded retries per call for 429/500/503 (default 2)
    --out DIR              where interpreted.json and report.md are written (default: next to findings.json)

Before any call, duplicates are merged and dependency findings are grouped per package (see dedupe.py), and what was
merged is recorded. The LLM only judges findings that a scanner already reported; a failed call, rejected output or a
cited evidence id that does not exist gives "uncertain", never a guess.

Exit code: 0 ok, 2 some calls failed (result uncertain), 3 usage error, 4 refused (no --allow-external-llm).
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant.dedupe import FindingGroup, dedupe
from app.agents.security_assistant.interpreter.evidence import build_bundle
from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter
from app.agents.security_assistant.interpreter.llm import LLMClient, LLMError, get_default_client
from app.agents.security_assistant.interpreter.models import (
    EvidenceBundle, EvidenceItem, InterpretationResult, finding_key,
)
from app.agents.security_assistant.interpreter.prompts import PROMPT_VERSION, build_prompt
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.report import build_report, from_json, render_markdown
from app.agents.security_assistant.schemas import Category, ScanResult

NOTICE = (
    "NOTICE: this sends data to an external LLM (Groq). Per call: the finding (rule, tool, CWE, file path, "
    "line, message), about 17 lines of code around it and up to 3 short snippets of related code from the project; "
    "secrets are masked and personal data is replaced by placeholders (names only on labelled lines, so not "
    "complete). Not sent: the rest of the repository, the git history, other findings."
)
SECTION_MARK = "<!-- llm-interpretation -->"


@dataclass
class Call:
    group: FindingGroup
    bundle: EvidenceBundle
    system: str
    user: str


@dataclass
class Plan:
    calls: list[Call]
    merge_log: list[dict]
    total_findings: int  # in findings.json
    selected_findings: int  # after --only-category
    groups_total: int  # after merging and grouping
    groups_cut: int  # left out by --max-findings
    pii: PIIRedactor | None = None  # placeholders used in the prompts; the mapping stays local


def parse_categories(values: list[str] | None) -> list[Category] | None:
    if not values:
        return None
    names = [n.strip().upper() for v in values for n in v.split(",") if n.strip()]
    try:
        return [Category(n) for n in names]
    except ValueError as exc:
        raise ValueError(f"unknown category in --only-category (use V1..V5): {exc}") from exc


def _advisory_item(group: FindingGroup) -> EvidenceItem | None:
    if group.kind != "package" or not group.advisories:
        return None
    lines = [f"{a['id']} | severity {a['severity'] or '-'} | reported by {', '.join(a['tools'])} | {a['message']}"
             for a in group.advisories[:12]]
    if len(group.advisories) > 12:
        lines.append(f"... and {len(group.advisories) - 12} more advisories for this package")
    return EvidenceItem(id="E9", kind="context", label=f"advisories the scanners reported for the package '{group.package}'",
                        content="\n".join(lines))


def make_plan(result: ScanResult, repo: Path | None, *, only: list[Category] | None = None,
              max_findings: int | None = None, pii: PIIRedactor | None = None) -> Plan:
    pii = pii if pii is not None else PIIRedactor.from_env()  # one redactor per run: stable placeholders
    selected = [f for f in result.findings if not only or f.category in only]
    groups, log = dedupe(selected)
    cut = max(0, len(groups) - max_findings) if max_findings is not None else 0
    chosen = groups[: len(groups) - cut]
    calls = []
    for g in chosen:
        extra = [i for i in (_advisory_item(g),) if i]
        bundle = build_bundle(g.representative, repo, extra=extra, pii=pii)
        system, user = build_prompt(g.representative, bundle, pii)
        calls.append(Call(g, bundle, system, user))
    return Plan(calls, log, len(result.findings), len(selected), len(groups), cut, pii)


def _where(f) -> str:
    return f"{f.file_path}:{f.line}" if f.file_path and f.line else (f.file_path or f.sink or "-")


def render_dry_run(plan: Plan, model: str) -> str:
    L = [f"DRY RUN - nothing is sent. {len(plan.calls)} LLM call(s) would be made (model {model}).",
         f"Findings in file: {plan.total_findings}; selected: {plan.selected_findings}; after merging and grouping: "
         f"{plan.groups_total} group(s)" + (f"; {plan.groups_cut} left out by --max-findings" if plan.groups_cut else ""), ""]
    if plan.merge_log:
        L.append("MERGED / GROUPED BEFORE ANY CALL")
        for m in plan.merge_log:
            if m["type"].startswith("same advisory"):
                L.append(f"  merged  {m['package']} {m['advisory']}: kept {m['kept']}, merged {', '.join(m['merged'])}")
            else:
                L.append(f"  grouped {m['package']}: {m['findings_in_group']} finding(s), {len(m['advisories'])} advisory(ies) -> 1 call")
        L.append("")
    system = plan.calls[0].system if plan.calls else ""
    L += ["=" * 100, "SYSTEM PROMPT (identical in every call)", "=" * 100, system, ""]
    for n, c in enumerate(plan.calls, 1):
        f = c.group.representative
        where = plan.pii.redact_path(_where(f)) if plan.pii is not None else _where(f)  # the header is what is sent too
        L += ["=" * 100, f"CALL {n}/{len(plan.calls)}  {c.group.id}  {f.category.value}  {f.rule_id}  {where}"
              f"  ({len(c.group.members)} finding(s) covered, finding {finding_key(f)})", "=" * 100, c.user, ""]
    chars = sum(len(c.system) + len(c.user) for c in plan.calls)
    L.append(f"TOTAL: {len(plan.calls)} call(s), {chars} characters (about {chars // 4} tokens) would be sent.")
    if plan.pii is not None:
        L.append(f"Personal-data placeholders used in the prompts above: {len(plan.pii.mapping)} (the mapping is never printed or sent).")
    return "\n".join(L)


# ---- running -------------------------------------------------------------------------------------------------------
@dataclass
class Outcome:
    call: Call
    result: InterpretationResult


async def run_calls(plan: Plan, client: LLMClient, delay: float = 0.0, say=print) -> list[Outcome]:
    interpreter = SemanticInterpreter(client, plan.pii)
    outcomes: list[Outcome] = []
    for n, call in enumerate(plan.calls, 1):
        result = await interpreter.interpret(call.group.representative, call.bundle)
        outcomes.append(Outcome(call, result))
        f = call.group.representative
        note = " (LLM error)" if result.error else " (output rejected)" if result.output_rejected else " (downgraded)" if result.downgraded else ""
        say(f"[{n}/{len(plan.calls)}] {f.category.value} {f.rule_id} {_where(f)} -> {result.status} {result.confidence:.2f}{note}")
        if delay and n < len(plan.calls):
            await asyncio.sleep(delay)
    return outcomes


def _brief(f) -> dict:
    return {"finding_key": finding_key(f), "category": f.category.value, "tool": f.tool, "rule_id": f.rule_id,
            "file_path": f.file_path, "line": f.line,
            "fix_pattern": guide.guidance_for(f).id}


def summarize(plan: Plan, outcomes: list[Outcome]) -> dict:
    counts = {"confirmed": 0, "dismissed": 0, "uncertain": 0}
    why = {"llm_error": 0, "output_rejected": 0, "downgraded": 0, "model_said_uncertain": 0}
    analysed = 0
    for o in outcomes:
        n = len(o.call.group.members)
        analysed += n
        counts[o.result.status] += n
        if o.result.status == "uncertain":
            key = ("llm_error" if o.result.error else "output_rejected" if o.result.output_rejected
                   else "downgraded" if o.result.downgraded else "model_said_uncertain")
            why[key] += n
    return {"scanner_only_findings": plan.selected_findings, "analysed_findings": analysed,
            "analysed_calls": len(outcomes), **counts, "uncertain_because": why,
            "not_analysed_findings": plan.selected_findings - analysed,
            "not_selected_findings": plan.total_findings - plan.selected_findings}


def to_document(plan: Plan, outcomes: list[Outcome], model: str | None, args: dict) -> dict:
    return {
        "meta": {"model": model, "prompt_version": PROMPT_VERSION, "temperature": args.pop("temperature", None), **args, "calls_planned": len(plan.calls),
                 "calls_made": len(outcomes)},
        "summary": summarize(plan, outcomes),
        "merge_log": plan.merge_log,
        "groups": [{"group_id": o.call.group.id, "kind": o.call.group.kind, "package": o.call.group.package,
                    "representative": _brief(o.call.group.representative),
                    "members": [_brief(m) for m in o.call.group.members],
                    "result": o.result.model_dump(mode="json")} for o in outcomes],
    }


def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_section(doc: dict) -> str:
    s, meta = doc["summary"], doc["meta"]
    M = [SECTION_MARK, "## LLM interpretation", "",
         "> The LLM judges findings that a scanner already reported; it cannot add findings. Its answers are opinions "
         "to review, not scanner output: **dismissed** means the model argued for a false positive.", "",
         f"- **Model:** {meta['model']}  **Prompt:** {meta['prompt_version']}  **Calls:** {meta['calls_made']} "
         f"(delay {meta.get('delay_s', 0)} s, retries {meta.get('retries')})",
         "", "| scanner-only findings | confirmed | dismissed | uncertain | not analysed |", "|---|---|---|---|---|",
         f"| {s['scanner_only_findings']} | {s['confirmed']} | {s['dismissed']} | {s['uncertain']} | {s['not_analysed_findings']} |",
         ""]
    u = s["uncertain_because"]
    M.append(f"Uncertain because: LLM error {u['llm_error']}, output rejected {u['output_rejected']}, downgraded "
             f"(missing or fake evidence id) {u['downgraded']}, the model said uncertain {u['model_said_uncertain']}. "
             "Counts are findings: a call about a package answers for every advisory of it.")
    if s["not_selected_findings"]:
        M.append(f"{s['not_selected_findings']} finding(s) were outside --only-category and not interpreted.")
    if doc["merge_log"]:
        M += ["", "### Merged and grouped before the calls", "", "| what | package | detail |", "|---|---|---|"]
        for m in doc["merge_log"]:
            detail = (f"kept {m['kept']}, merged {', '.join(m['merged'])}" if "kept" in m
                      else f"{m['findings_in_group']} finding(s), advisories {', '.join(m['advisories'][:6])}"
                           + (" ..." if len(m['advisories']) > 6 else ""))
            M.append(f"| {_cell(m['type'])} | {_cell(m['package'])} | {_cell(detail)} |")
    M += ["", "### Results", "", "| group | category | rule | where | status | conf. | evidence | rationale |", "|---|---|---|---|---|---|---|---|"]
    for g in doc["groups"]:
        r, rep = g["result"], g["representative"]
        flag = " (LLM error)" if r["error"] else " (output rejected)" if r["output_rejected"] else " (downgraded)" if r["downgraded"] else ""
        where = rep["file_path"] + (f":{rep['line']}" if rep["line"] else "") if rep["file_path"] else "-"
        what = f"{g['package']} ({len(g['members'])} findings)" if g["kind"] == "package" else where
        M.append(f"| {g['group_id']} | {rep['category']} | {_cell(rep['rule_id'])} | {_cell(what)} | **{r['status']}**{flag} | "
                 f"{r['confidence']:.2f} | {_cell(', '.join(r['evidence_ids']) or '-')} | {_cell(r['error'] or r['downgrade_reason'] or r['rationale'])} |")
    confirmed = [g for g in doc["groups"] if g["result"]["status"] == "confirmed"]
    if confirmed:
        M += ["", "### How to fix the confirmed findings", "",
              "The standard advice for each type of issue is in the section \"How to fix (by type of issue)\" above. "
              "The text below is a note the LLM wrote for this code: a suggestion to review and test, not a finished patch.", ""]
        for g in confirmed:
            rep, r = g["representative"], g["result"]
            where = rep["file_path"] + (f":{rep['line']}" if rep["line"] else "") if rep["file_path"] else (g["package"] or "-")
            standard = guide.by_id(rep.get("fix_pattern"))
            M.append(f"**{g['group_id']} `{rep['rule_id']}` - {_cell(where)}**" + (f" (standard advice: {standard.title})" if standard else ""))
            note = (r["recommendation"].strip()
                    or (f"_The model's note was not kept: {r['recommendation_dropped']}. Use the standard advice._"
                        if r.get("recommendation_dropped") else "_The model gave no tailored advice; use the standard advice._"))
            M += ["", note, ""]
    return "\n".join(M) + "\n"


def write_outputs(out_dir: Path, result: ScanResult, skipped: list[str], repo: Path | None, doc: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(result, skipped=skipped, source=result.repo_path, repo=repo)
    md = out_dir / "report.md"
    md.write_text(render_markdown(report) + "\n" + render_section(doc), encoding="utf-8")
    js = out_dir / "interpreted.json"
    js.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return js, md


def render_results_table(outcomes: list[Outcome]) -> str:
    L = ["", f"{'group':<5}{'cat':<4}{'rule':<40}{'status':<10}{'conf':>5}  evidence      rationale / error"]
    for o in outcomes:
        f, r = o.call.group.representative, o.result
        text = r.error or r.downgrade_reason or r.rationale
        L.append(f"{o.call.group.id:<5}{f.category.value:<4}{f.rule_id[:39]:<40}{r.status:<10}{r.confidence:>5.2f}  "
                 f"{','.join(r.evidence_ids) or '-':<12}  {' '.join(text.split())[:150]}")
    return "\n".join(L)


async def main(argv: list[str] | None = None, client: LLMClient | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("findings", type=Path)
    ap.add_argument("repo", type=Path, nargs="?")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-external-llm", action="store_true")
    ap.add_argument("--only-category", action="append", metavar="V1,V4")
    ap.add_argument("--max-findings", type=int)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    try:
        only = parse_categories(args.only_category)
        result, skipped = from_json(args.findings.read_text(encoding="utf-8"))
    except (ValueError, OSError, KeyError) as exc:
        print(f"cannot read the input: {exc}", file=sys.stderr)
        return 3
    if args.repo is not None and not args.repo.is_dir():
        print(f"not a directory: {args.repo}", file=sys.stderr)
        return 3
    if args.repo is None:
        print("note: no repo folder given, so only the finding metadata is sent (no code snippets).")

    plan = make_plan(result, args.repo, only=only, max_findings=args.max_findings)
    if args.dry_run:
        model = getattr(client, "model", None) or "(configured at run time)"
        print(render_dry_run(plan, model))
        return 0
    if not args.allow_external_llm:
        print("REFUSED: not calling an external LLM without --allow-external-llm. Use --dry-run to see exactly what "
              "would be sent.\n" + NOTICE, file=sys.stderr)
        return 4
    try:
        client = client or get_default_client(retries=args.retries, backoff=max(0.5, args.delay))
    except LLMError as exc:
        print(f"cannot run: {exc}", file=sys.stderr)
        return 3
    print(NOTICE)
    print(f"Calling {client.model}: {len(plan.calls)} call(s) after merging ({plan.selected_findings} findings), "
          f"delay {args.delay:g}s, retries {args.retries}.")
    outcomes = await run_calls(plan, client, delay=args.delay)

    doc = to_document(plan, outcomes, client.model, {"findings_file": str(args.findings), "delay_s": args.delay,
                                                      "temperature": getattr(client, "temperature", None),
                                                      "retries": args.retries, "max_findings": args.max_findings,
                                                      "only_category": [c.value for c in only] if only else None})
    out = args.out or args.findings.parent
    js, md = write_outputs(out, result, skipped, args.repo, doc)
    mapping = plan.pii.save_mapping(out / "pii_mapping.local.json") if plan.pii is not None else None
    print(render_results_table(outcomes))
    if mapping:
        print(f"\nLOCAL ONLY: {mapping} maps the personal-data placeholders back to the originals. Do not share or commit it.")
    s = doc["summary"]
    print(f"\nscanner-only findings {s['scanner_only_findings']} -> confirmed {s['confirmed']}, dismissed {s['dismissed']}, "
          f"uncertain {s['uncertain']}, not analysed {s['not_analysed_findings']}; uncertain because {s['uncertain_because']}")
    print(f"Wrote {js} and {md}")
    return 2 if any(o.result.error for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
