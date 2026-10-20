"""What a run needs from the outside, in one place: the store, the read-only workspace, the Scrum MCP client, GitHub, the language model, and the data a run builds up.

``Services`` is created once per worker (``from_environment``) or per test. Nothing in it holds a secret that could reach an event or a result: the GitHub token is passed to the workspace and
to GitHub's client only, the language-model keys stay inside the client.
"""
import asyncio
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

FACTOR_MODELS = Path(__file__).resolve().parents[1] / "factor_models"
CARD_DIRS = {"effort": "01_effort", "consistency": "02_consistency", "requirement_fulfillment": "03_requirement_fulfillment", "collaboration": "04_collaboration",
             "task_complexity": "05_task_complexity", "behavioral_pattern": "06_behavioral_pattern", "code_ownership": "07_code_ownership"}


def load_cards() -> dict:
    out = {}
    for name, folder in CARD_DIRS.items():
        p = FACTOR_MODELS / folder / "card.json"
        if p.exists():
            out[name] = json.loads(p.read_text(encoding="utf-8"))
    return out


class RunData:
    """What one run collects before the students are assessed. Written to the run's folder so a run that waited for a human (identity gate) continues after a restart."""

    FIELDS = ("roster", "sprint", "tasks_by_student", "evidence", "quality", "rev", "previous_marks", "as_of", "scrum_data_dir", "simulate_now", "installation_id")

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.roster, self.sprint, self.tasks_by_student, self.evidence, self.quality, self.rev, self.previous_marks, self.as_of = [], {}, {}, {}, {}, None, {}, None
        self.scrum_data_dir = self.simulate_now = self.installation_id = None
        self.prs = None
        self.patches: dict = {}

    @property
    def patches_path(self) -> Path:
        return self.folder / "patches.json"

    def save(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / "data.json").write_text(json.dumps({k: getattr(self, k) for k in self.FIELDS}, ensure_ascii=False), encoding="utf-8")
        self.patches_path.write_text(json.dumps(self.patches), encoding="utf-8")

    @classmethod
    def load(cls, folder: Path) -> "RunData":
        d = cls(folder)
        f = d.folder / "data.json"
        if f.exists():
            for k, v in json.loads(f.read_text(encoding="utf-8")).items():
                setattr(d, k, v)
        return d


class AsyncStore:
    """The store seen from async code: every call runs in a worker thread, so a database that answers slowly never stops the other students' work."""

    def __init__(self, store):
        self._s = store

    def __getattr__(self, name):
        fn = getattr(self._s, name)

        async def call(*a, **k):
            return await asyncio.to_thread(fn, *a, **k)

        return call


@dataclass
class Services:
    store: Any
    ws: Any
    scrum: Callable[..., Any]                      # returns an async context manager that yields the Scrum MCP client
    github: Any = None                            # object with ``async pulls_bundle(repo_url, since=None, max_prs=...)``, or None when GitHub is not connected
    llm: Any = None                               # rf_bench LLM (chat -> Reply); None: Requirement Fulfillment is not available and the auditor uses its default rules
    token: str | None = None
    github_app: Any = None                        # shared.github_app.GitHubApp: mints a short-lived token for the repository a team linked; None when the App is not configured
    work_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "assessment-runs")
    parallel_students: int = 4
    checkpointer: Any = None
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    cards: dict = field(default_factory=load_cards)
    _data: dict = field(default_factory=dict)

    async def token_for(self, data) -> str | None:
        """The token to read this team's repository with: the GitHub App's installation token when the team linked one (valid for an hour and renewed on demand, never written to disk), otherwise the worker's own."""
        iid = getattr(data, "installation_id", None)
        if iid and self.github_app is not None:
            try:
                return await asyncio.to_thread(self.github_app.installation_token, int(iid))
            except Exception:  # GitHub refused or is down: fall back to the worker's own token, if it has one
                return self.token
        return self.token

    @property
    def astore(self) -> AsyncStore:
        return AsyncStore(self.store)

    def data(self, run_id: str) -> RunData:
        if run_id not in self._data:
            self._data[run_id] = RunData.load(self.work_dir / str(run_id))
        return self._data[run_id]

    @classmethod
    def from_environment(cls, store=None, **over):
        """A worker's services from the environment: SERVER_DIRECT_URL (database), GITHUB_TOKEN, GROQ_API_KEYS (language model), ASSESSMENT_WORKSPACE (clone folder)."""
        import sys
        from app.agents.performance_assessment.com_agent.ingestion.github_rest import GitHubREST
        from app.agents.performance_assessment.com_agent.ingestion.scrum_mcp_client import RealScrumMCPClient
        from app.agents.performance_assessment.workspace import WorkspaceManager
        from shared.performance import PerformanceStore

        server = Path(__file__).resolve().parents[1] / "mcp_servers" / "scrum_board_server.py"
        token = os.environ.get("GITHUB_TOKEN") or None
        from shared.github_app import GitHubApp, GitHubAppConfig

        app_cfg = GitHubAppConfig.from_env()
        llm = None
        try:
            sys.path.insert(0, str(FACTOR_MODELS / "03_requirement_fulfillment"))
            from rf_bench.llm import GroqPool
            # the Groq settings live in performance_assessment/.env (git-ignored); only the GROQ_* lines are read from it
            os.environ.setdefault("RF_ENV_FILE", str(FACTOR_MODELS.parent / ".env"))
            llm = GroqPool()
        except Exception:  # no keys: the factor says "not available", the rest of the assessment continues
            llm = None
        base = Path(os.environ.get("ASSESSMENT_WORKSPACE") or (Path(tempfile.gettempdir()) / "assessment-workspace"))
        # GitHub works without a token for public repositories, within its 60 requests an hour
        args = dict(store=store or PerformanceStore(), ws=WorkspaceManager(base / "repos"), scrum=lambda data_dir=None: RealScrumMCPClient(command=sys.executable, args=[str(server)], env=({"SCRUM_DATA_DIR": str(data_dir)} if data_dir else {k: os.environ[k] for k in ("SCRUM_DATA_DIR",) if k in os.environ}) or None),
                    github=None, github_app=GitHubApp(app_cfg) if app_cfg.configured else None, llm=llm, token=token, work_dir=base / "runs")
        args.update(over)
        return cls(**args)
