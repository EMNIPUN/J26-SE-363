"""Step 11: who wrote the code that survives, counted on real source lines only (Code Ownership).

For every source file a student touched, reads `git blame -w` at the final version, ignoring commits that only reformatted
code, and counts only lines that are real work (no blank lines, comments or docstrings; see 07_code_ownership/cleaning.py).
Results (commit -> number of counted lines, per file) are cached in ``private/cache/blame_clean_<repo>.json``: the cache holds
real commit ids, so it stays in the git-ignored private folder.

    python scripts/11_clean_blame_real.py
"""

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "07_code_ownership"))

from cleaning import meaningful_blame_counts  # noqa: E402
from evidence.lines import SOURCE_KINDS, classify_path  # noqa: E402
from identity import DATASET, PRIVATE, opaque  # noqa: E402

CACHE = PRIVATE / "cache"


def format_only_commits(stats):
    """Opaque commit ids whose source changes are almost all moved or re-indented lines."""
    g = stats.groupby("commit_id")[["a_code", "a_comment", "a_blank", "a_format_only"]].sum()
    total = g.sum(axis=1)
    return set(g[(total >= 30) & (g.a_format_only >= 0.8 * total)].index)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    stats = pd.read_csv(DATASET / "clean" / "commit_file_stats.csv")
    commits = pd.read_csv(DATASET / "evidence" / "commits.csv")
    fmt = format_only_commits(stats)
    bulk = set(commits[commits.is_bulk == 1].commit_id)
    print(f"format-only commits to ignore in blame: {len(fmt)}")
    for team, info in config["teams"].items():
        for repo_id, (folder, _) in info["repos"].items():
            out = CACHE / f"blame_clean_{repo_id}.json"
            if out.exists():
                continue
            path = Path(config["repos_dir"]) / folder
            raw = json.loads((PRIVATE / "raw" / f"{repo_id}.json").read_text(encoding="utf-8"))
            touched, ignore = set(), []
            for c in raw["commits"]:
                cid = opaque(c["sha"])
                if cid in fmt:
                    ignore.append(c["sha"])
                if cid in bulk:
                    continue
                for p, a, _ in c["files"]:
                    if a and classify_path(p) in SOURCE_KINDS:
                        touched.add(p)
            head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            existing = set(subprocess.run(["git", "-C", str(path), "ls-tree", "-r", "--name-only", head], capture_output=True,
                                          text=True, encoding="utf-8", errors="replace").stdout.splitlines())
            args = ["git", "-C", str(path), "blame", "--line-porcelain", "-w"]
            ignore_file = None
            if ignore:
                ignore_file = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
                ignore_file.write("\n".join(ignore) + "\n")
                ignore_file.close()
                args += ["--ignore-revs-file", ignore_file.name]
            result = defaultdict(dict)
            for f in sorted(touched & existing):
                r = subprocess.run(args + [head, "--", f], capture_output=True, text=True, encoding="utf-8", errors="replace")
                if r.returncode == 0:
                    result[f] = meaningful_blame_counts(r.stdout, f)
            out.write_text(json.dumps(result), encoding="utf-8")
            print(f"  {repo_id}: {len(result)} files blamed, {len(ignore)} format-only commits ignored", flush=True)


if __name__ == "__main__":
    main()
