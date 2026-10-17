"""Real-scanner tests for Java: OSV-Scanner on Maven/Gradle and CodeQL's Spring authorisation handling."""

import shutil

import pytest

from app.agents.security_assistant.schemas import Category, RunStatus
from app.agents.security_assistant.tools.codeql import CodeQLTool
from app.agents.security_assistant.tools.dependencies import OsvScannerTool
from app.agents.security_assistant.tools.runner import run_all
from app.agents.security_assistant.tools.tests.test_integration import _codeql, _scan
from app.agents.security_assistant.tools.tests.test_tools import run

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not shutil.which("osv-scanner"), reason="osv-scanner not installed")
def test_osv_maven_resolves_transitive_dependencies(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, OsvScannerTool(), "vuln_java_repo")
    sinks = " ".join(f.sink or "" for f in result.findings)
    assert "log4j-core" in sinks  # declared in pom.xml
    assert "tomcat-embed-core" in sinks  # NOT declared: pulled in by spring-boot-starter-web
    assert not result.warnings


@pytest.mark.skipif(not shutil.which("osv-scanner"), reason="osv-scanner not installed")
def test_osv_gradle_reads_only_the_lockfile(make_repo, tmp_path):
    result = _scan(make_repo, tmp_path, OsvScannerTool(), "vuln_java_gradle_repo")
    assert {f.file_path for f in result.findings} == {"gradle.lockfile"}
    assert "log4j-core" in " ".join(f.sink or "" for f in result.findings)
    assert not result.warnings


@pytest.mark.skipif(not shutil.which("osv-scanner"), reason="osv-scanner not installed")
def test_osv_gradle_without_lockfile_is_not_silently_clean(make_repo, tmp_path):
    repo = make_repo("vuln_java_gradle_repo")
    (repo / "gradle.lockfile").unlink()
    result = run(run_all(repo, tools=[OsvScannerTool()], scan_dir=tmp_path / "scans"))
    rec = result.runs[0]
    assert rec.findings_count == 0
    assert rec.status in (RunStatus.NOT_APPLICABLE, RunStatus.SUCCEEDED)
    assert rec.reason and ("no supported manifest" in rec.reason or "NOT scanned" in rec.reason)


SPRING_CASES = """package demo;

import java.security.Principal;
import java.sql.Statement;
import org.springframework.context.annotation.Bean;
import org.springframework.security.access.annotation.Secured;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.*;

@RestController
class Cases {
    // ---- must NOT be reported: an authorisation rule or a check of the user exists
    @PreAuthorize("hasRole('ADMIN')") @GetMapping("/a/{id}")
    String preauthRole(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }

    @GetMapping("/p/{id}")
    String principalCheck(@PathVariable String id, Principal principal, Statement st) throws Exception {
        st.executeQuery("S " + id + principal.getName()); return "x"; }

    // ---- MUST be reported
    @PreAuthorize("isAuthenticated()") @GetMapping("/b/{id}")
    String isAuthOnly(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }

    @GetMapping("/api/orders/{id}")
    String authenticatedChainOnly(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }

    @Bean
    SecurityFilterChain chain(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(a -> a.requestMatchers("/admin/**").hasRole("ADMIN").anyRequest().authenticated());
        return http.build();
    }
}

@Secured("ROLE_ADMIN") @RestController
class ClassSecured {
    @GetMapping("/c/{id}")
    String classSecured(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }
}

@RestController @RequestMapping("/admin")
class AdminController {
    @GetMapping("/orders/{id}")
    String coveredByFilterChain(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }
}

@RestController
class Unprotected {
    @GetMapping("/open/{id}")
    String noProtection(@PathVariable String id, Statement st) throws Exception { st.executeQuery("S " + id); return "x"; }
}
"""


@pytest.mark.skipif(not shutil.which("codeql"), reason="codeql not installed")
def test_codeql_java_v1_understands_spring_authorisation(tmp_path):
    repo = tmp_path / "spring"
    (repo / "src/main/java/demo").mkdir(parents=True)
    (repo / "src/main/java/demo/Cases.java").write_text(SPRING_CASES)
    result = _codeql(repo, tmp_path)
    flagged = {f.message.split("'")[1] for f in result.findings if f.category is Category.V1}
    assert flagged == {"isAuthOnly", "authenticatedChainOnly", "noProtection"}, flagged


# ---- Safety: CodeQL must never run the student's build tools ------------------------------------------------
import os
import stat


def _canary(path, label, log):
    path.write_text(f'#!/bin/sh\necho "CANARY: {label} executed with $*" >> {log}\nexit 1\n')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.mark.skipif(not shutil.which("codeql"), reason="codeql not installed")
@pytest.mark.parametrize("fixture", ["vuln_java_gradle_repo", "vuln_java_repo"])
def test_codeql_never_executes_build_tools_or_wrapper_scripts(make_repo, tmp_path, monkeypatch, fixture):
    """Canary scripts stand in for gradle, mvn and the repo's own gradlew / mvnw (with wrapper layouts)."""
    log = tmp_path / "canary.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _canary(fake_bin / "gradle", "system gradle", log)
    _canary(fake_bin / "mvn", "system mvn", log)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    repo = make_repo(fixture)
    (repo / "gradle/wrapper").mkdir(parents=True)
    (repo / "gradle/wrapper/gradle-wrapper.properties").write_text(
        r"distributionUrl=https\://services.gradle.org/distributions/gradle-7.6-bin.zip" + "\n")
    (repo / ".mvn/wrapper").mkdir(parents=True)
    (repo / ".mvn/wrapper/maven-wrapper.properties").write_text(
        "distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.8.6/"
        "apache-maven-3.8.6-bin.zip\n")
    _canary(repo / "gradlew", "repo gradlew", log)
    _canary(repo / "mvnw", "repo mvnw", log)

    result = _codeql(repo, tmp_path)
    assert result.runs[0].status is RunStatus.SUCCEEDED
    assert not log.exists(), f"a build tool or wrapper was executed:\n{log.read_text()}"
