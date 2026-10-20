"""Cut the number of LLM calls before any call is made, and record what was merged.

1. Same advisory, same package, reported by several tools (OSV-Scanner and pip-audit both report PYSEC-2018-28
   for requests) -> one finding is kept (OSV-Scanner first), the others are noted as merged.
2. Dependency findings are then grouped per package: reachability is a question about the package, not about each
   advisory, so one call judges the package and the answer applies to every advisory of it.
3. The same place seen twice is one call (a "location" group): different tools reporting the same category at the same
   file and line (the config scanner and CodeQL both flag the MD5 hash on one line), and secrets (V4) of the same file and
   commit within two lines of each other (Gitleaks and TruffleHog on one key pair). Other findings are never merged, so
   two different weaknesses on one line (injection and a missing ownership check) still get a call each.

Nothing is dropped from the scanner output: every original finding stays a member of its group and inherits the
group's answer. This module never creates findings; a group always has a real scanner finding as representative.
"""

import re
from dataclasses import dataclass, field

from app.agents.security_assistant.interpreter.models import finding_key
from app.agents.security_assistant.schemas import Category, Finding

DEPENDENCY_TOOLS = ("osv-scanner", "pip-audit", "npm-audit")  # in the order a duplicate is kept
SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "MEDIUM": 2, "LOW": 1}
_CVE = re.compile(r"CVE-\d{4}-\d{4,}", re.I)
_SINK = re.compile(r"^(?P<name>[^@\s=<>(]+)(?:@(?P<v1>[^\s(]+)|==(?P<v2>\S+)|\s+(?P<range>[<>=~^][^(]*))?")


def package_of(f: Finding) -> tuple[str, str] | None:
    """(package name, version or range) of a dependency finding, from its sink."""
    if f.category is not Category.V5 or f.tool not in DEPENDENCY_TOOLS or not f.sink:
        return None
    m = _SINK.match(f.sink.strip())
    if not m:
        return None
    return m.group("name"), (m.group("v1") or m.group("v2") or (m.group("range") or "").strip() or "?")


@dataclass
class FindingGroup:
    id: str
    kind: str  # "single", "package" (one package, several advisories) or "location" (one place, several tools)
    representative: Finding
    members: list[Finding]
    package: str | None = None
    advisories: list[dict] = field(default_factory=list)  # for package and location groups: id, severity, message, tools


def _ids(f: Finding) -> set[str]:
    return {f.rule_id.upper(), *(c.upper() for c in _CVE.findall(f.message or ""))}


def _severity(f: Finding) -> int:
    return SEVERITY_ORDER.get((f.severity_tool or "").upper(), 0)


def _label(f: Finding) -> str:
    return f"{f.tool}:{f.rule_id}"


V4_ADJACENT_LINES = 2


def _clusters(singles: list[Finding]) -> list[list[int]]:
    """Indexes of `singles` that are the same issue seen twice (see rule 3 above), each cluster in order, clusters in the order of
    their first member. A finding that merges with nothing is a cluster of one."""
    parent = list(range(len(singles)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    secrets = sorted((i for i, f in enumerate(singles) if f.category is Category.V4 and f.file_path and f.line is not None),
                     key=lambda i: (singles[i].file_path, singles[i].source or "", singles[i].line))
    for a, b in zip(secrets, secrets[1:]):
        fa, fb = singles[a], singles[b]
        if (fa.file_path, fa.source) == (fb.file_path, fb.source) and fb.line - fa.line <= V4_ADJACENT_LINES:
            union(a, b)
    by_place: dict[tuple, list[int]] = {}
    for i, f in enumerate(singles):
        if f.category is not Category.V4 and f.file_path and f.line is not None:
            by_place.setdefault((f.category, f.file_path, f.line), []).append(i)
    for members in by_place.values():
        if len({singles[i].tool for i in members}) >= 2:  # only a second tool makes it a duplicate
            for i in members[1:]:
                union(members[0], i)
    out: dict[int, list[int]] = {}
    for i in range(len(singles)):
        out.setdefault(find(i), []).append(i)
    return sorted(out.values(), key=lambda c: c[0])


def dedupe(findings: list[Finding]) -> tuple[list[FindingGroup], list[dict]]:
    """Returns (groups in first-appearance order, merge log)."""
    log: list[dict] = []
    by_pkg: dict[str, list[Finding]] = {}
    order: list[tuple[str, object]] = []  # ("single", Finding) | ("location", [Finding]) | ("pkg", name.lower())
    singles: list[tuple[int, Finding]] = []  # (position in `order`, finding)
    for f in findings:
        pkg = package_of(f)
        if pkg is None:
            singles.append((len(order), f))
            order.append(("single", f))
            continue
        key = pkg[0].lower()
        if key not in by_pkg:
            by_pkg[key] = []
            order.append(("pkg", key))
        by_pkg[key].append(f)
    for cluster in _clusters([f for _pos, f in singles]):
        if len(cluster) > 1:
            members = [singles[i][1] for i in cluster]
            order[singles[cluster[0]][0]] = ("location", members)
            for i in cluster[1:]:
                order[singles[i][0]] = ("skip", None)

    groups: list[FindingGroup] = []
    for kind, item in order:
        if kind == "skip":
            continue
        gid = f"G{len(groups) + 1:02d}"
        if kind == "single":
            groups.append(FindingGroup(gid, "single", item, [item]))
            continue
        if kind == "location":
            members = item
            rep = max(members, key=lambda m: (_severity(m), -members.index(m)))  # highest severity; ties keep the first
            advisories = [{"id": m.rule_id, "severity": m.severity_tool, "message": (m.message or "")[:140], "tools": [m.tool],
                           "fixed_versions": []} for m in members if m is not rep]
            place = f"{rep.file_path}:{rep.line}"
            log.append({"type": "same place reported by several tools", "package": place, "kept": _label(rep),
                        "merged": [_label(m) for m in members if m is not rep]})
            groups.append(FindingGroup(gid, "location", rep, list(members), advisories=advisories))
            continue
        members = by_pkg[item]
        name = package_of(members[0])[0]
        # 1. merge the same advisory reported by several tools
        clusters: list[list[Finding]] = []
        for f in sorted(members, key=lambda x: DEPENDENCY_TOOLS.index(x.tool)):
            for cluster in clusters:
                if any(_ids(f) & _ids(c) for c in cluster):
                    cluster.append(f)
                    break
            else:
                clusters.append([f])
        kept = [c[0] for c in clusters]
        for c in clusters:
            if len(c) > 1:
                log.append({"type": "same advisory and package reported by several tools", "package": name,
                            "advisory": c[0].rule_id, "kept": _label(c[0]), "merged": [_label(x) for x in c[1:]]})
        # 2. one group per package
        advisories = [{"id": c[0].rule_id, "severity": c[0].severity_tool, "message": (c[0].message or "")[:140],
                       "tools": [x.tool for x in c],
                       "fixed_versions": sorted({v for x in c for v in x.fixed_versions})} for c in clusters]
        rep = max(kept, key=_severity)  # highest severity; ties keep the first
        versions = sorted({package_of(m)[1] for m in members})
        log.append({"type": "grouped per package", "package": name, "versions_seen": versions,
                    "advisories": [a["id"] for a in advisories], "findings_in_group": len(members),
                    "tools": sorted({m.tool for m in members})})
        groups.append(FindingGroup(gid, "package", rep, list(members), package=name, advisories=advisories))
    return groups, log


def member_keys(group: FindingGroup) -> list[str]:
    return [finding_key(m) for m in group.members]
