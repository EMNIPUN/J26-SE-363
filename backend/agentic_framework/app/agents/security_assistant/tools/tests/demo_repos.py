"""Make scannable copies of the seeded fixtures: real git repositories where a fake AWS key pair was committed
and then deleted, so the secret scanners have something to find in the history.

    python -m app.agents.security_assistant.tools.tests.demo_repos <dest>

No secret is stored in this repository: the fake values are assembled here at run time.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_AWS_KEY = "AKIA" + "QYLPMN5HHHFPZAM2"
FAKE_AWS_SECRET = "Zk9xQ2v7Lm4Rt8Yp1Nc6Wd3Hs5Jb0Ga2Ue" + "+Ff7Xi"


def _writable_then_retry(func, path, _exc):
    """rmtree on Windows cannot delete the read-only object files git writes; make them writable and try again."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=demo", "-c", "user.email=demo@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def make_demo_repos(dest: Path) -> list[Path]:
    dest = Path(dest)
    made = []
    for fixture in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        repo = dest / fixture.name
        if repo.exists():
            shutil.rmtree(repo, onerror=_writable_then_retry)
        shutil.copytree(fixture, repo)
        _git(repo, "init", "-q")
        # commit messages carry task ids (see traceability_samples/tasks.json) so the trace command has something to match
        _git(repo, "add", "-A", "--", ".", ":!.github")
        _git(repo, "commit", "-q", "-m", "T-101 US-01: login and orders")
        if (repo / ".github").exists():
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "T-105: add CI workflow")
        (repo / "settings_old.py").write_text(
            f'AWS_ACCESS_KEY_ID = "{FAKE_AWS_KEY}"\nAWS_SECRET_ACCESS_KEY = "{FAKE_AWS_SECRET}"\n')
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "T-103: add old settings")
        (repo / "settings_old.py").unlink()
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "T-103: remove old settings")
        made.append(repo)
    return made


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    for repo in make_demo_repos(Path(sys.argv[1])):
        print(repo)
