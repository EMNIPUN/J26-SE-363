"""A dependency that a manifest declares but no scanner can check is a visible coverage gap (result, report, incomplete run)."""

import asyncio
import json
import sys

import pytest

from app.agents.security_assistant import assess
from app.agents.security_assistant.report import build_report, from_json, render_console, render_markdown, to_json
from app.agents.security_assistant.schemas import Category, Finding, ScanResult
from app.agents.security_assistant.tools.config_scan import ConfigScanTool
from app.agents.security_assistant.tools.coverage_gaps import find_dependency_gaps
from app.agents.security_assistant.tools.dependencies import OsvScannerTool
from app.agents.security_assistant.tools.runner import run_all
from app.agents.security_assistant.tools.tests.conftest import FIXTURES


def run(coro):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def put(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return root


def lock(*names):
    return {"lockfileVersion": 3, "packages": {"": {}, **{f"node_modules/{n}": {"version": "1.0.0"} for n in names}}}


# ---- the real fixtures -----------------------------------------------------------------------------------------------------------------
def test_only_the_js_demo_has_a_gap_and_it_names_express():
    gaps = {d.name: find_dependency_gaps(d) for d in FIXTURES.iterdir() if d.is_dir()}
    assert gaps["vuln_py_repo"] == gaps["vuln_java_repo"] == gaps["vuln_java_gradle_repo"] == []
    assert gaps["vuln_js_repo"] == ["package.json declares 1 dependency that package-lock.json does not list, so no scanner checked it: express"]


# ---- npm ---------------------------------------------------------------------------------------------------------------------------------
def test_npm_declared_but_not_locked(tmp_path):
    put(tmp_path, {"package.json": {"dependencies": {"express": "4.17.1", "lodash": "4.17.15"}, "devDependencies": {"jest": "29"}},
                   "package-lock.json": lock("lodash")})
    gap, = find_dependency_gaps(tmp_path)
    assert "declares 2 dependencies that package-lock.json does not list" in gap and "express, jest" in gap


def test_npm_everything_locked_scoped_packages_and_local_dependencies(tmp_path):
    put(tmp_path, {"package.json": {"dependencies": {"@scope/pkg": "1", "left-pad": "1", "mine": "file:../mine", "ws": "workspace:*"}},
                   "package-lock.json": lock("@scope/pkg", "left-pad")})
    assert find_dependency_gaps(tmp_path) == []


def test_npm_without_any_lockfile_and_with_other_lockfiles(tmp_path):
    put(tmp_path / "a", {"package.json": {"dependencies": {"express": "4"}}})
    put(tmp_path / "b", {"package.json": {"dependencies": {"express": "4", "chalk": "5"}}, "yarn.lock": 'express@^4:\n  version "4.1.0"\n'})
    gaps = find_dependency_gaps(tmp_path)
    assert any(g.startswith("a/package.json has no lockfile") and "express" in g for g in gaps)
    assert any(g.startswith("b/package.json declares 1 dependency that yarn.lock does not mention") and "chalk" in g for g in gaps)


def test_npm_a_broken_lockfile_is_a_gap_not_a_crash(tmp_path):
    put(tmp_path, {"package.json": {"dependencies": {"express": "4"}}, "package-lock.json": "{not json"})
    assert "cannot be read" in find_dependency_gaps(tmp_path)[0]


# ---- Python --------------------------------------------------------------------------------------------------------------------------------
def test_python_requirements_without_an_exact_version(tmp_path):
    put(tmp_path, {"requirements.txt": "# comment\nflask==1.0\nrequests>=2.0\nnumpy\nclick[extra]~=8.0\npytest==7.1 ; python_version>'3'\n"
                                       "-r other.txt\n--hash=sha256:abc\ngit+https://x/y.git\nloose==1.*\n"})
    gap, = find_dependency_gaps(tmp_path)
    assert "without an exact version" in gap and "click, loose, numpy, requests" in gap and "flask" not in gap and "pytest" not in gap


def test_python_pinned_requirements_are_not_a_gap(tmp_path):
    put(tmp_path, {"requirements.txt": "flask==1.0\nrequests==2.19.0\n", "requirements-dev.txt": "pytest===7.1.0\n"})
    assert find_dependency_gaps(tmp_path) == []


def test_python_pyproject_dependencies_need_a_lock_or_pinned_requirements(tmp_path):
    pyproject = '[project]\nname = "x"\ndependencies = ["Flask>=2", "my_lib[extra]>=1", "requests"]\n'
    put(tmp_path / "none", {"pyproject.toml": pyproject})
    put(tmp_path / "locked", {"pyproject.toml": pyproject, "uv.lock": '[[package]]\nname = "flask"\n[[package]]\nname = "my-lib"\n[[package]]\nname = "requests"\n'})
    put(tmp_path / "partly", {"pyproject.toml": pyproject, "poetry.lock": '[[package]]\nname = "Flask"\n'})
    put(tmp_path / "pinned", {"pyproject.toml": pyproject, "requirements.txt": "flask==2.0\nmy-lib==1.0\nrequests==2.0\n"})
    gaps = find_dependency_gaps(tmp_path)
    assert any(g.startswith("none/pyproject.toml declares 3 dependencies") for g in gaps)
    assert any(g.startswith("partly/pyproject.toml declares 2 dependencies") and "my-lib, requests" in g for g in gaps)
    assert not any(g.startswith(("locked/", "pinned/")) for g in gaps)


def test_python_poetry_dependencies(tmp_path):
    put(tmp_path, {"pyproject.toml": '[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "^2"\n'})
    gap, = find_dependency_gaps(tmp_path)
    assert gap.endswith("checked it: requests") and "declares 1 dependency" in gap  # "python" is the interpreter, not a dependency


# ---- Maven and Gradle ----------------------------------------------------------------------------------------------------------------------
POM = '<project>{extra}<properties><v>1.2</v></properties><dependencies>{deps}</dependencies></project>'
DEP = "<dependency><groupId>{g}</groupId><artifactId>{a}</artifactId>{v}</dependency>"


def test_maven_a_dependency_without_a_version_that_nothing_can_supply(tmp_path):
    deps = DEP.format(g="org.x", a="lib", v="") + DEP.format(g="org.y", a="ok", v="<version>1.0</version>") \
        + DEP.format(g="org.z", a="prop", v="<version>${v}</version>") + DEP.format(g="org.w", a="undefined", v="<version>${nope}</version>")
    put(tmp_path / "bare", {"pom.xml": POM.format(extra="", deps=deps)})
    put(tmp_path / "managed", {"pom.xml": POM.format(extra="<parent><artifactId>spring-boot-starter-parent</artifactId></parent>", deps=deps)})
    gaps = find_dependency_gaps(tmp_path)
    assert len(gaps) == 1 and gaps[0].startswith("bare/pom.xml declares 2 dependencies") and "org.w:undefined, org.x:lib" in gaps[0]


def test_maven_plugin_and_managed_dependencies_are_not_counted(tmp_path):
    pom = ("<project><dependencyManagement><dependencies>" + DEP.format(g="a", a="b", v="") + "</dependencies></dependencyManagement>"
           "<build><plugins><plugin><dependencies>" + DEP.format(g="c", a="d", v="") + "</dependencies></plugin></plugins></build>"
           "<!-- " + DEP.format(g="e", a="f", v="") + " --></project>")
    put(tmp_path, {"pom.xml": pom})
    assert find_dependency_gaps(tmp_path) == []


def test_gradle_without_a_lockfile_and_with_a_lockfile_that_misses_one(tmp_path):
    build = "dependencies {\n  implementation 'org.a:one:1.0'\n  api(\"org.b:two:2.0\")\n  testImplementation 'org.c:three'\n}\n"
    put(tmp_path / "nolock", {"build.gradle": build})
    put(tmp_path / "lock", {"build.gradle": build, "gradle.lockfile": "# generated\norg.a:one:1.0=compileClasspath\norg.b:two:2.0=runtimeClasspath\nempty=\n"})
    put(tmp_path / "full", {"build.gradle.kts": build.replace("'", '"'), "gradle.lockfile": "org.a:one:1.0=x\norg.b:two:2.0=x\norg.c:three:3=x\n"})
    gaps = find_dependency_gaps(tmp_path)
    assert any(g.startswith("nolock/build.gradle has no gradle.lockfile") and "3 declared dependencies" in g for g in gaps)
    assert any(g.startswith("lock/build.gradle declares 1 dependency that gradle.lockfile does not list") and "org.c:three" in g for g in gaps)
    assert not any(g.startswith("full/") for g in gaps)


def test_many_names_are_cut_in_the_message(tmp_path):
    put(tmp_path, {"package.json": {"dependencies": {f"pkg{i:02d}": "1" for i in range(12)}}, "package-lock.json": lock()})
    assert "pkg00, pkg01, pkg02, pkg03, pkg04, pkg05, pkg06, pkg07 and 4 more" in find_dependency_gaps(tmp_path)[0]


# ---- the result, the report and the run -------------------------------------------------------------------------------------------------
def test_run_all_records_the_gaps_when_a_dependency_tool_is_part_of_the_scan_and_not_otherwise():
    js = FIXTURES / "vuln_js_repo"
    assert run(run_all(js, tools=[OsvScannerTool()])).coverage_gaps and "express" in run(run_all(js, tools=[OsvScannerTool()])).coverage_gaps[0]
    assert run(run_all(js, tools=[ConfigScanTool()])).coverage_gaps == []  # a scan without a dependency tool says nothing about dependencies


def test_a_gap_makes_the_report_incomplete_in_the_console_the_markdown_and_findings_json():
    gap = "package.json declares 1 dependency that package-lock.json does not list, so no scanner checked it: express"
    result = ScanResult(run_id="r", repo_path="x", coverage_gaps=[gap])
    rep = build_report(result)
    assert rep.complete is False and rep.coverage_gaps == [gap]
    console, md = render_console(rep), render_markdown(rep)
    assert "RESULT: INCOMPLETE - 1 dependency coverage gap" in console and f"COVERAGE GAP: {gap}" in console
    assert "Result: INCOMPLETE" in md and f"**Coverage gap:** {gap}" in md
    back, _skipped = from_json(to_json(rep))
    assert back.coverage_gaps == [gap]
    assert build_report(ScanResult(run_id="r", repo_path="x")).complete is True  # no gap, no failed tool: complete as before


def saved_without_gap_info(tmp_path, repo):
    path = tmp_path / "findings.json"
    path.write_text(to_json(build_report(ScanResult(run_id="r", repo_path=str(repo), findings=[
        Finding(category=Category.V5, rule_id="GHSA-x", tool="osv-scanner", file_path="package-lock.json", sink="lodash@4.17.15 (npm)")]))),
        encoding="utf-8")
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["scan"].pop("coverage_gaps")  # a findings.json from before this check existed
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_assess_checks_the_repo_for_an_older_findings_json_and_reports_the_gap_as_an_incomplete_reason(tmp_path):
    report = run(assess.run_pipeline(str(FIXTURES / "vuln_js_repo"), reuse_scan=saved_without_gap_info(tmp_path, FIXTURES / "vuln_js_repo"),
                                     out_dir=tmp_path / "out"))
    assert report["scan"]["coverage_gaps"] and "express" in report["scan"]["coverage_gaps"][0] and report["scan"]["complete"] is False
    assert report["run"]["complete"] is False and any(r.startswith("dependency coverage gap:") and "express" in r for r in report["run"]["incomplete_reasons"])
    assert "Coverage gap" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")


def test_a_repo_without_a_gap_adds_no_reason(tmp_path):
    report = run(assess.run_pipeline(str(FIXTURES / "vuln_py_repo"), reuse_scan=saved_without_gap_info(tmp_path, FIXTURES / "vuln_py_repo"),
                                     out_dir=tmp_path / "out"))
    assert report["scan"]["coverage_gaps"] == [] and not any("coverage gap" in r for r in report["run"]["incomplete_reasons"])
