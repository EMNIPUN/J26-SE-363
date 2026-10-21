"""Turn the hand-written student files in teams/ into feature tables with the same columns and formulas as
the real pipeline (scripts/03_compute_features.py), and check the authored data for mistakes.

    python materialize.py            # writes out/*.csv, out/code_examples.jsonl, out/validation_report.md

Nothing here invents numbers: every feature is computed from the commits, tasks, reviews, comments and quiz
answers written for the student.
"""
import csv
import hashlib
import importlib.util
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
import sys  # noqa: E402
sys.path.insert(0, str(HERE))
from complexity_ratings import RATINGS  # noqa: E402
sys.path.insert(0, str(HERE.parents[1]))  # factor_models/
from evidence.lines import classify_path  # noqa: E402
from evidence.registry import featurize_all, load_factors  # noqa: E402
import to_evidence  # noqa: E402
OUT = HERE / "out"
SPRINT_DAYS, DEADLINE_DAYS, BULK_CAP = 14, 3, 800
COUNTED = ("code", "test", "config_or_docs")
APPROVAL_ONLY = re.compile(r"^\W*(lgtm|ok(ay)?|good|great|nice|done|approved?|well done|all good|looks good|thanks?|ty|\+1)\W*$", re.I)
TECHNICAL = re.compile(r"`|\.(js|ts|jsx|tsx|java|py|css)\b|line \d+|function|endpoint|null|undefined|error|exception|query|index|validation|refactor|test|transaction|lock|finally|atomic|409|403", re.I)
TIERS = {"substantive", "brief", "approval"}
STATUSES = {"Done", "Partially Done", "In Progress", "To Do"}


def substance(text):
    """Same rule as the real pipeline: approvals and one-word replies score 0."""
    text = (text or "").strip()
    words = len(text.split())
    if words < 3 or APPROVAL_ONLY.match(text):
        return 0.0
    return round(min(1.0, 0.2 + 0.6 * min(words, 40) / 40 + (0.2 if TECHNICAL.search(text) else 0.0)), 3)


def longest_gap(active):
    longest = run = 0
    for d in range(SPRINT_DAYS):
        run = 0 if d in active else run + 1
        longest = max(longest, run)
    return longest


def bursts(active_days, churn, gap=4, share=0.2):
    if len(active_days) < 2:
        return False
    days = sorted(active_days)
    groups, cur = [], [days[0]]
    for d in days[1:]:
        if d - cur[-1] > gap:
            groups.append(cur)
            cur = [d]
        else:
            cur.append(d)
    groups.append(cur)
    total = sum(churn.values()) or 1
    return sum(1 for g in groups if sum(churn.get(d, 0) for d in g) / total >= share) >= 2


def component(path):
    parts = path.split("/")
    return "/".join(parts[-3:-1]) if len(parts) > 2 else parts[0]


def sha(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:10]


def load_teams():
    import sys
    sys.path.insert(0, str(HERE / "teams"))
    teams = {}
    for p in sorted((HERE / "teams").glob("S*.py")):
        spec = importlib.util.spec_from_file_location(p.stem, p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        teams[mod.TEAM["team"]] = mod.TEAM
    return teams


def scale_volume(teams):
    """Scale each student's own commits to the volume set in volume.py and add the neighbouring files each change
    touches. Works per student; teammates are never used. Returns rows describing what was applied."""
    from volume import LINES_PER_FILE, MAIN_SHARE, SPLIT, TARGET_NET_LOC
    applied = []
    for tid, team in teams.items():
        neighbours = defaultdict(set)
        for a, b in team["edges"]:
            neighbours[a].add(b)
            neighbours[b].add(a)
        by_dir = defaultdict(set)
        for node in neighbours:
            by_dir[node.rsplit("/", 1)[0]].add(node)
        for s, st in team["students"].items():
            sprints = [k for k in st if k.startswith(tid)]

            def net(commits):
                return sum(f[2] - f[3] for c in commits for f in c[4] if f[1] in COUNTED)
            active = sorted(net(st[k]["commits"]) for k in sprints if st[k]["commits"])
            authored = statistics.median(active) if active else 0
            target = TARGET_NET_LOC.get(s)
            k = 1.0 if (target is None or authored <= 0) else max(1.0, target / authored)
            for sp in sprints:
                new = []
                for i, (d, h, msg, task, files) in enumerate(st[sp]["commits"]):
                    code = [f for f in files if f[1] == "code"]
                    scaled = [(p, kind, round(a * k), round(dl * k)) for p, kind, a, dl in files]
                    if code and k > 1:
                        total_a = sum(f[2] for f in scaled if f[1] == "code")
                        total_d = sum(f[3] for f in scaled if f[1] == "code")
                        want = max(len(code), round(total_a / LINES_PER_FILE))
                        graph = {n for p, *_ in code for n in neighbours[p] | by_dir[p.rsplit("/", 1)[0]]} - {f[0] for f in files}
                        pool = {(n, "code") for n in graph}
                        for n in {p for p, *_ in code} | graph:
                            pool |= set(support_files(n))
                        pool = sorted(pool - {(f[0], f[1]) for f in files})
                        off = hash_idx(s, sp, i) % len(pool) if pool else 0
                        extra = (pool[off:] + pool[:off])[:max(0, want - len(code))]
                        if extra:
                            scaled = [(p, kind, round(a * MAIN_SHARE) if kind == "code" else a, round(dl * MAIN_SHARE) if kind == "code" else dl) for p, kind, a, dl in scaled]
                            rest_a, rest_d = total_a - sum(f[2] for f in scaled if f[1] == "code"), total_d - sum(f[3] for f in scaled if f[1] == "code")
                            for j, (p, kind) in enumerate(extra):
                                scaled.append((p, kind, rest_a // len(extra) + (1 if j < rest_a % len(extra) else 0), rest_d // len(extra) + (1 if j < rest_d % len(extra) else 0)))
                    parts = SPLIT.get(s, 1) if scaled else 1
                    for part in range(parts):
                        if parts == 1:
                            new.append((d, h, msg, task, scaled))
                            continue
                        share = [(p, kind, a // parts + (1 if part < a % parts else 0), dl // parts + (1 if part < dl % parts else 0)) for p, kind, a, dl in scaled]
                        new.append((d, min(23, h + part), msg if part == 0 else f"{msg} (part {part + 1})", task, share))
                st[sp]["commits_authored"] = st[sp]["commits"]
                st[sp]["commits"] = new
            applied.append(dict(student_id=s, target_net_loc=target if target is not None else "", authored_median_net_loc=authored, scale=round(k, 2)))
    return applied


def support_files(path):
    """Files that normally change together with a source file: its tests, its stylesheet (UI files), its fixture."""
    folder, name = path.rsplit("/", 1) if "/" in path else ("", path)
    stem, _, ext = name.rpartition(".")
    out = [(f"tests/{stem}_spec.{ext}", "test"), (f"fixtures/{stem}.json", "config_or_docs")]
    if ext in ("jsx", "tsx", "vue", "html"):
        out.append((f"{folder}/{stem}.css" if folder else f"{stem}.css", "code"))
    return out


COMPANIONS = ("helpers", "types", "constants", "utils")  # modules that normally sit beside a source file


def task_structure(team):
    """Files involved, dependency reach and component breadth of every task, measured before the task started.

    Files involved   the files the task changes plus the helper, types, test, fixture and stylesheet files that go with
                     each source file (so they exist whenever the source file does)
    Dependency reach files that import those files, directly or through other files, among the files that already
                     existed when the task's first commit was made (a file's creation time is its first commit by anyone)
    Component breadth number of distinct folders the files are in
    Tasks with no commits have no footprint (as in the real data) and get no values.
    """
    def when(sprint, d, h):
        return datetime.combine(date.fromisoformat(team["sprint_starts"][sprint]), datetime.min.time()) + timedelta(days=d, hours=h)

    def supports(p):
        folder, name = p.rsplit("/", 1) if "/" in p else ("", p)
        stem, _, ext = name.rpartition(".")
        pre = f"{folder}/" if folder else ""
        companions = [(f"{pre}{stem}_{suffix}.{ext}", "code") for suffix in COMPANIONS]
        return companions + support_files(p)

    created, edges = {}, set(team["edges"])
    for st in team["students"].values():
        for sp, rec in st.items():
            if not isinstance(rec, dict):
                continue
            for d, h, msg, task, files in rec["commits_authored"]:
                t = when(sp, d, h)
                for p, kind, a, dl in files:
                    if kind in COUNTED and (p not in created or t < created[p]):
                        created[p] = t
    for p in list(created):
        for q, kind in supports(p) if p.endswith(("js", "jsx", "ts", "tsx", "py", "go", "java", "kt", "dart", "vue")) else []:
            if q not in created or created[p] < created[q]:
                created[q] = created[p]
            if any(f"_{suffix}." in q for suffix in COMPANIONS):
                edges.add((p, q))
    importers = defaultdict(set)
    for a, b in edges:
        importers[b].add(a)

    def reach(node, t):
        """Files that import `node` directly or through one intermediate file (two hops, as in the real data)."""
        first = {a for a in importers[node] if a in created and created[a] < t}
        second = {b for a in first for b in importers[a] if b in created and created[b] < t}
        return len((first | second) - {node})

    out = {}
    for s, st in team["students"].items():
        for sp, rec in st.items():
            if not isinstance(rec, dict):
                continue
            for task in rec["tasks"]:
                mine = [(when(sp, c[0], c[1]), c[4]) for c in rec["commits_authored"] if c[3] == task["key"]]
                if not mine:
                    continue
                start = min(t for t, _ in mine)
                core = {f[0] for _, files in mine for f in files if f[1] in COUNTED}
                code = [p for p in core if p.endswith(("js", "jsx", "ts", "tsx", "py", "go", "java", "kt", "dart", "vue"))]
                foot = set(core)
                for p in code:
                    foot |= {q for q, _ in supports(p)}
                out[f"{sp}-{s}-{task['key']}"] = dict(
                    FI=len(foot), CB=len({component(p) for p in foot}),
                    # only the files the task actually changes carry reach; the companion modules it adds beside them are new
                    DR=sum(reach(p, start) for p in core if p in created and created[p] < start),
                    footprint=[{"path": p, "kind": classify_path(p), "reach_before": reach(p, start) if p in core and p in created and created[p] < start else 0}
                               for p in sorted(foot)])
    return out


def hash_idx(*parts):
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:6], 16)


def reach_table(edges):
    importers = defaultdict(set)
    for a, b in edges:
        importers[b].add(a)

    def reach(node):
        seen, stack = set(), [node]
        while stack:
            for a in importers[stack.pop()]:
                if a not in seen:
                    seen.add(a)
                    stack.append(a)
        return len(seen)
    return reach


def main():
    OUT.mkdir(exist_ok=True)
    teams = load_teams()
    for team in teams.values():  # structure is read from the commits as written, so keep a copy before volume scaling
        for st in team["students"].values():
            for k, v in st.items():
                if isinstance(v, dict):
                    v["commits_authored"] = list(v["commits"])
    from board_estimates import OVERRIDES, SUBTASKS_SQUEEZE
    from fulfilment import fulfilment_rating
    from ownership import KO
    for tid_, team_ in teams.items():  # survival and ownership read from the final repository, set per student and sprint
        for s_, st_ in team_["students"].items():
            for sp_, rec_ in st_.items():
                if isinstance(rec_, dict):
                    val = KO.get(s_, {}).get(sp_.split("-")[1])
                    if val is not None:
                        rec_["ko"] = dict(survival=val[0], primary_owner=val[1])
    for team_ in teams.values():  # fulfilment on the real 1-4 scale, following the criteria met
        for st_ in team_["students"].values():
            for rec_ in st_.values():
                if isinstance(rec_, dict):
                    for t_ in rec_["tasks"]:
                        t_["rating_written"] = t_["rating"]
                        t_["rating"] = fulfilment_rating(t_["rating"], t_["met"], t_["status"], bool(t_.get("by")))
    for tid_, team_ in teams.items():  # the team's own estimates, apart from how hard the task is
        for s_, st_ in team_["students"].items():
            for sp_, rec_ in st_.items():
                if isinstance(rec_, dict):
                    for t_ in rec_["tasks"]:
                        key_ = f"{sp_}-{s_[4:]}-{t_['key']}"
                        t_["sp"], t_["sub"] = OVERRIDES.get(key_, (t_["sp"], SUBTASKS_SQUEEZE.get(t_["sub"], 3)))
    applied = scale_volume(teams)
    task_rows = []
    clean_rows = []
    factors = load_factors(["effort", "consistency", "rf", "collab", "tc", "ko"])
    splitter = to_evidence.Splitter()
    feats, board, commits_out, reviews_out, comments_out, prs_out, quiz_out, students_out, code_out = [], [], [], [], [], [], [], [], []
    problems, notes = [], []

    for tid, team in teams.items():
        tc_features = task_structure(team)
        members = list(team["students"])
        for sprint in sorted({s for st in team["students"].values() for s in st if s.startswith(tid)}):
            start = date.fromisoformat(team["sprint_starts"][sprint])
            who = [s for s in members if sprint in team["students"][s]]
            team_files = defaultdict(set)  # path -> students
            for s in who:
                for d, h, msg, task, files in team["students"][s][sprint]["commits"]:
                    for path, kind, a, dl in files:
                        if kind in COUNTED:
                            team_files[path].add(s)
            sprint_has_prs = any(team["students"][s][sprint]["prs"] for s in who)

            for s in who:
                rec = team["students"][s][sprint]
                label = f"{s}/{sprint}"
                # ---- structural checks (on the commits as written, before volume scaling) -----------------
                keys = {t["key"] for t in rec["tasks"]}
                for d, h, msg, task, files in rec["commits_authored"]:
                    if not 0 <= d < SPRINT_DAYS or not 0 <= h < 24:
                        problems.append(f"{label}: commit day/hour out of range {d},{h}")
                    if task is not None and task not in keys:
                        problems.append(f"{label}: commit '{msg}' points to unknown task {task}")
                    for path, kind, a, dl in files:
                        if kind == "code" and not any(path in e for e in team["edges"]):
                            problems.append(f"{label}: file {path} is not in the team's import graph")
                for t in rec["tasks"]:
                    if t["status"] not in STATUSES:
                        problems.append(f"{label}/{t['key']}: bad status {t['status']}")
                    if len(t["met"]) != len(t["ac"]):
                        problems.append(f"{label}/{t['key']}: met list has {len(t['met'])} entries for {len(t['ac'])} criteria")
                    has_commit = any(c[3] == t["key"] for c in rec["commits"])
                    if t["status"] != "To Do" and not has_commit and not t.get("by"):
                        problems.append(f"{label}/{t['key']}: {t['status']} but no commit linked")
                    if t["status"] == "Done" and sum(t["met"]) == 0 and not t.get("by"):
                        problems.append(f"{label}/{t['key']}: Done with no criterion met")
                    if t["status"] == "To Do" and t["rating"] > 1:
                        problems.append(f"{label}/{t['key']}: To Do but rated {t['rating']}")
                for tier_item in rec.get("reviews", []):
                    if tier_item[4] not in TIERS:
                        problems.append(f"{label}: bad review tier {tier_item[4]}")
                    if tier_item[1] == s:
                        problems.append(f"{label}: reviews own PR")
                    if tier_item[1] not in members:
                        problems.append(f"{label}: reviews unknown author {tier_item[1]}")
                    tier_ok = (substance(tier_item[3]) >= 0.5) if tier_item[4] == "substantive" else (substance(tier_item[3]) == 0 if tier_item[4] == "approval" else True)
                    if not tier_ok:
                        problems.append(f"{label}: review tier '{tier_item[4]}' disagrees with its text: {tier_item[3][:40]}")

                # ---- Effort / Consistency -----------------------------------------------------------------
                work = rec["commits"]
                churn, active = defaultdict(int), set()
                added = deleted = capped = test_added = 0
                touched, code_added = set(), 0
                per_file_added = defaultdict(int)
                for d, h, msg, task, files in work:
                    a = sum(f[2] for f in files if f[1] in COUNTED)
                    dl = sum(f[3] for f in files if f[1] in COUNTED)
                    added += a
                    deleted += dl
                    capped += max(-BULK_CAP, min(BULK_CAP, a - dl))
                    test_added += sum(f[2] for f in files if f[1] == "test")
                    churn[d] += min(BULK_CAP, a + dl) or 1
                    active.add(d)
                    for path, kind, fa, fd in files:
                        if kind in COUNTED:
                            touched.add(path)
                        if kind == "code":
                            code_added += fa
                            per_file_added[path] += fa
                    sha_id = sha(label, d, h, msg)
                    commits_out.append(dict(commit_id=sha_id, team_id=tid, sprint_id=sprint, student_id=s,
                                            authored_at=(datetime.combine(start + timedelta(days=d), datetime.min.time()) + timedelta(hours=h)).isoformat(),
                                            subject=msg, task_key=f"{sprint}-{s}-{task}" if task else "", files="; ".join(f"{p}(+{fa}/-{fd})" for p, k, fa, fd in files),
                                            lines_added=a, lines_deleted=dl))
                tasks_done = [t for t in rec["tasks"] if t["status"] == "Done" and not t.get("by")]
                said = [c for c in rec.get("comments", []) if c[1] != s]
                given = rec.get("reviews", [])
                mfo = rec.get("merged_for_others", 0)
                row = {"record_id": f"{sprint}-{s}", "team_id": tid, "sprint_id": sprint, "student_id": s,
                       "project_domain": team["domain"], "team_size": len(members),
                       "E_CC": len(work), "E_LOC_net": added - deleted, "E_LOC_added": added, "E_LOC_deleted": deleted,
                       "E_LOC_net_capped": capped, "E_FC": len(touched), "E_CT": len(tasks_done),
                       "E_RD": len(given) + len(said) + mfo, "E_merge_commits": 0, "E_bulk_commits": 0, "E_bulk_lines": 0,
                       "E_test_lines": test_added}
                daily = [churn.get(d, 0) for d in range(SPRINT_DAYS)]
                total = sum(daily)
                if work:
                    mean = total / SPRINT_DAYS
                    cv = statistics.pstdev(daily) / mean if mean else 0
                    row.update({"C_AWR": round(len(active) / SPRINT_DAYS, 4), "C_DC": round(sum(daily[-DEADLINE_DAYS:]) / total, 4),
                                "C_LI_norm": round(longest_gap(active) / SPRINT_DAYS, 4),
                                "C_CV_norm": round(min(1.0, cv / math.sqrt(SPRINT_DAYS - 1)), 4),
                                "C_first_active_day": min(active), "C_bimodal": int(bursts(active, churn)), "C_no_activity": 0})
                else:
                    row.update({"C_AWR": 0.0, "C_DC": 1.0, "C_LI_norm": 1.0, "C_CV_norm": 1.0, "C_first_active_day": "", "C_bimodal": 0, "C_no_activity": 1})

                # ---- Requirement Fulfilment ------------------------------------------------------------------
                n = len(rec["tasks"])
                ac_total = sum(len(t["ac"]) for t in rec["tasks"])
                ac_met = sum(sum(t["met"]) for t in rec["tasks"] if not t.get("by"))
                untracked = [c for c in work if c[3] is None]
                row.update({
                    "RF_tasks_assigned": n, "RF_tasks_done": len(tasks_done),
                    "RF_tasks_partial": sum(1 for t in rec["tasks"] if t["status"] in ("Partially Done", "In Progress")),
                    "RF_tasks_not_started": sum(1 for t in rec["tasks"] if t["status"] == "To Do"),
                    "RF_done_by_teammate": sum(1 for t in rec["tasks"] if t.get("by")),
                    "RF_completion_rate": round(len(tasks_done) / n, 4) if n else "",
                    "RF_ac_total": ac_total, "RF_ac_met": ac_met, "RF_ac_ratio": round(ac_met / ac_total, 4) if ac_total else "",
                    "RF_llm_score": round(statistics.mean((t["rating"] - 1) / 4 for t in rec["tasks"]), 4) if n else "",
                    "RF_carried_over": sum(1 for t in rec["tasks"] if t.get("carried")),
                    "RF_untracked_ratio": round(len(untracked) / len(work), 4) if work else ""})

                # ---- Collaboration ------------------------------------------------------------------------------
                review_texts = [r[3] for r in given]
                discussion = [c[2] for c in said]
                own_prs = rec["prs"]
                resolved = [p for p in own_prs if p[2]]
                shared = [p for p in touched if team_files[p] - {s}]
                row.update({
                    "Co_PRC_depth": round(statistics.mean(substance(t) for t in review_texts), 4) if review_texts else 0.0,
                    "Co_IC_depth": round(statistics.mean(substance(t) for t in discussion), 4) if discussion else 0.0,
                    "Co_MC": sum(int(c[3]) + min(1, int(c[4])) for c in said),
                    "Co_PCount": len(given) + mfo, "Co_CCount": len(said) + len(given),
                    "Co_IR": round(len(resolved) / len(own_prs), 4) if own_prs else "",
                    "Co_prs_opened": len(own_prs), "Co_prs_merged": len(resolved), "Co_prs_merged_for_others": mfo,
                    "Co_shared_file_ratio": round(len(shared) / len(touched), 4) if touched else 0.0,
                    "Co_team_uses_prs": int(sprint_has_prs)})
                for d, author, state, text, tier in given:
                    reviews_out.append(dict(team_id=tid, sprint_id=sprint, reviewer_id=s, pr_author_id=author, day=d, state=state, tier=tier, body=text))
                for d, author, text, is_reply, mentions in rec.get("comments", []):
                    comments_out.append(dict(team_id=tid, sprint_id=sprint, author_id=s, pr_author_id=author, day=d, is_reply=is_reply, mentions=mentions, body=text))
                for d, title, merged in own_prs:
                    prs_out.append(dict(team_id=tid, sprint_id=sprint, author_id=s, day=d, title=title, merged=int(merged)))

                # ---- Task Complexity ----------------------------------------------------------------------------
                # structure is measured on the repository as it stood before each task's first commit, from the
                # commits as written (never the volume-scaled ones), so it cannot grow with how much a student writes
                fi, dr, cb, rated = [], [], [], []
                for t in rec["tasks"]:
                    full = f"{sprint}-{s}-{t['key']}"
                    m = tc_features.get(full)
                    rkey = f"{sprint}-{s[4:]}-{t['key']}"
                    ratings = RATINGS.get(rkey)
                    if ratings is None:
                        problems.append(f"{label}/{t['key']}: no Task Complexity ratings for {rkey}")
                    else:
                        rated.append(statistics.mean(ratings))
                    if m:
                        fi.append(m["FI"]); dr.append(m["DR"]); cb.append(m["CB"])
                    task_rows.append(dict(task_id=full, team_id=tid, sprint_id=sprint, student_id=s, task_title=t["title"], story_points=t["sp"],
                                          subtask_count=t["sub"], files_involved=m["FI"] if m else "", dependency_reach=m["DR"] if m else "",
                                          component_breadth=m["CB"] if m else "",
                                          technical_difficulty=ratings[0] if ratings else "", scope_breadth=ratings[1] if ratings else "",
                                          dependency_impact=ratings[2] if ratings else "", architectural_impact=ratings[3] if ratings else "",
                                          uncertainty=ratings[4] if ratings else "", R_avg=round(statistics.mean(ratings), 2) if ratings else "",
                                          TC_GT=round((statistics.mean(ratings) - 1) / 4, 4) if ratings else ""))
                sp = [t["sp"] for t in rec["tasks"]]
                row.update({"TC_SP": round(statistics.mean(sp), 3) if sp else "", "TC_SP_total": sum(sp),
                            "TC_SC": round(statistics.mean(t["sub"] for t in rec["tasks"]), 3) if n else "",
                            "TC_FI": round(statistics.mean(fi), 3) if fi else "", "TC_DR": round(statistics.mean(dr), 3) if dr else "",
                            "TC_CB": round(statistics.mean(cb), 3) if cb else "",
                            "TC_authored_score": round((statistics.mean(rated) - 1) / 4, 4) if rated else ""})

                # ---- Code Ownership -----------------------------------------------------------------------------
                ko, quiz = rec["ko"], rec["quiz"]
                surviving_by_file = {p: a * ko["survival"] for p, a in per_file_added.items()}
                row.update({"KO_lines_added_code": code_added,
                            "KO_survival": ko["survival"] if code_added else "",
                            "KO_primary_owner_share": ko["primary_owner"] if code_added else "",
                            "KO_snippet_candidates": sum(1 for v in surviving_by_file.values() if v >= 20),
                            "KO_quiz_score": round((quiz["rating"] - 1) / 4, 4)})
                quiz_out.append(dict(team_id=tid, sprint_id=sprint, student_id=s, tier=quiz["tier"], rating=quiz["rating"], snippet=quiz["snippet"],
                                     question=quiz["question"], answer=quiz["answer"]))
                feats.append(row)

                # ---- the same student-sprint as raw evidence, through the factor packages' own cleaning code --------
                evidence = to_evidence.build(team, s, sprint, rec, label, tc_features, splitter, sprint_has_prs)
                clean, removed, warns = featurize_all(evidence, factors)
                clean_rows.append({"record_id": row["record_id"], "team_id": tid, "sprint_id": sprint, "student_id": s,
                                   "project_domain": team["domain"], "team_size": len(members), **clean,
                                   "Co_team_uses_prs": int(sprint_has_prs), "TC_authored_score": row["TC_authored_score"],
                                   **{f"removed_{k}": removed.get(k, 0) for k in ("comment", "blank", "format_only", "docs_or_config", "generated_or_data")},
                                   **{f"{k}_raw": row.get(k, "") for k in ("E_CC", "E_LOC_net", "E_LOC_net_capped", "E_FC", "C_AWR", "C_DC", "C_LI_norm", "C_CV_norm",
                                                                         "TC_FI", "TC_DR", "TC_CB", "KO_survival", "KO_primary_owner_share", "KO_snippet_candidates")}})

                # ---- tasks and code -------------------------------------------------------------------------
                for t in rec["tasks"]:
                    tid_full = f"{sprint}-{s}-{t['key']}"
                    board.append(dict(task_id=tid_full, team_id=tid, sprint_id=sprint, story=t.get("story", ""), task_title=t["title"], description=t["desc"],
                                      acceptance_criteria="; ".join(f"{i + 1}. {a}" for i, a in enumerate(t["ac"])), story_points=t["sp"], subtask_count=t["sub"],
                                      assignee_id=s, status=t["status"], completed_by=t.get("by", s if t["status"] == "Done" else ""),
                                      carried_over_from=t.get("carried", ""), linked_commits=" ".join(sha(label, c[0], c[1], c[2]) for c in work if c[3] == t["key"]),
                                      ac_total=len(t["ac"]), ac_met=sum(t["met"]), llm_fulfilment_rating=t["rating"], basis="authored"))
                    code_out.append(dict(task_id=tid_full, criteria_met=t["met"], code=t["code"]))

        for s in members:
            st = team["students"][s]
            sprints_in = [k for k in st if k.startswith(tid)]
            students_out.append(dict(student_id=s, team_id=tid, behaviour_class=st["class"], scenario=st["scenario"], sprints=len(sprints_in)))

    def write(name, rows):
        if not rows:
            return
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    write("features_simulated.csv", feats)
    write("features_simulated_clean.csv", clean_rows)
    lines_out = ["File types with too few real lines for their own line split (overall source shares used):"]
    lines_out += [f"  {k[0]} .{k[1]}: {n} files" for k, n in sorted(splitter.fallbacks.items())]
    (OUT / "split_fallbacks.txt").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    write("scrum_board_simulated.csv", board)
    write("commits_simulated.csv", commits_out)
    write("reviews_simulated.csv", reviews_out)
    write("comments_simulated.csv", comments_out)
    write("pull_requests_simulated.csv", prs_out)
    write("quiz_simulated.csv", quiz_out)
    write("students_simulated.csv", students_out)
    write("volume_applied.csv", applied)
    write("task_complexity_tasks.csv", task_rows)
    with open(OUT / "code_examples.jsonl", "w", encoding="utf-8") as f:
        for r in code_out:
            f.write(json.dumps(r) + "\n")

    # ---- report ---------------------------------------------------------------------------------------------------
    lines = [f"# Simulated students: validation report\n", f"{len(students_out)} students, {len(feats)} student-sprints, {len(board)} tasks, "
             f"{len(commits_out)} commits, {len(reviews_out)} reviews, {len(comments_out)} discussion comments.\n"]
    by_class = defaultdict(int)
    for s in students_out:
        by_class[s["behaviour_class"]] += 1
    lines.append("\n## Students by class\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(by_class.items())))
    spr = defaultdict(int)
    for s in students_out:
        spr[s["sprints"]] += 1
    lines.append("\n\n## Sprints per student\n" + "\n".join(f"- {k} sprints: {v} students" for k, v in sorted(spr.items())))
    perfect = [r["record_id"] for r in feats if r["RF_ac_ratio"] == 1 and r["RF_completion_rate"] == 1 and r["C_AWR"] >= .6 and r["KO_quiz_score"] >= .75
               and r["Co_PRC_depth"] >= .6]
    lines.append(f"\n\n## Perfect-looking records (every factor strong): {len(perfect)} {perfect}")
    lines.append("\n\n## Problems found\n" + ("\n".join(f"- {p}" for p in problems) if problems else "- none"))
    (OUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(feats)} records, {len(board)} tasks, {len(problems)} problems")
    for p in problems:
        print(" -", p)


if __name__ == "__main__":
    main()
