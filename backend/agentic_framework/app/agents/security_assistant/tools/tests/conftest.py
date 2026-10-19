import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _isolate_tool_settings(monkeypatch):
    """A developer .env may set these (other test suites load it); they would override test timeouts."""
    for name in list(os.environ):
        if name.startswith("SECURITY_ASSISTANT_TOOL_TIMEOUT") or name == "SECURITY_ASSISTANT_MAX_PARALLEL":
            monkeypatch.delenv(name)


# Built at test time so no secret is ever committed to this repository.
FAKE_AWS_KEY = "AKIA" + "QYLPMN5HHHFPZAM2"
# TruffleHog's AWS detector only reports a key ID that comes with its secret half.
FAKE_AWS_SECRET = "Zk9xQ2v7Lm4Rt8Yp1Nc6Wd3Hs5Jb0Ga2Ue" + "+Ff7Xi"
SECRET_FILE_TEXT = f'AWS_ACCESS_KEY_ID = "{FAKE_AWS_KEY}"\nAWS_SECRET_ACCESS_KEY = "{FAKE_AWS_SECRET}"\n'


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture
def make_repo(tmp_path):
    """Copy a fixture to a temp git repo; optionally commit a secret and remove it again."""

    def _make(name: str, with_secret: bool = False) -> Path:
        repo = tmp_path / name
        shutil.copytree(FIXTURES / name, repo)
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "init")
        if with_secret:
            (repo / "settings_old.py").write_text(SECRET_FILE_TEXT)
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "add config")
            (repo / "settings_old.py").unlink()
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "remove config")
        return repo

    return _make
