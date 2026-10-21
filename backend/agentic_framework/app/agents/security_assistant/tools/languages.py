"""Detect which languages a repository uses from file names only (nothing is executed)."""

import os
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", "target", "build", "dist",
    ".gradle", ".idea", ".next", "site-packages",
}
MAX_FILES = 50_000

EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
}
MANIFESTS = {
    "requirements.txt": "python", "pyproject.toml": "python", "pipfile": "python",
    "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "java",
    "tsconfig.json": "typescript", "package.json": "javascript",
}


def walk_repo(repo: Path):
    """Yield (dirpath, filenames) for the repo, skipping vendored/build directories."""
    seen = 0
    for dirpath, dirnames, filenames in os.walk(repo, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        seen += len(filenames)
        yield Path(dirpath), filenames
        if seen > MAX_FILES:
            return


def detect_languages(repo: Path) -> set[str]:
    found: set[str] = set()
    for _dir, names in walk_repo(repo):
        for name in names:
            lang = EXTENSIONS.get(Path(name).suffix.lower()) or MANIFESTS.get(name.lower())
            if lang:
                found.add(lang)
    return found
