"""Step 9: clean line counts for every real commit, measured on the repositories.

Reads each commit's diff in memory, classifies every added and deleted line of source files with the shared cleaning
code (`evidence/lines.py`), and writes only counts to ``clean/commit_file_stats.csv``. No code, no text, no names
are written; paths go through the same scrubbing as the other evidence tables.

    python scripts/09_clean_commit_stats.py
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))  # factor_models/

from evidence.lines import SOURCE_KINDS, classify_path, stats_from_patch  # noqa: E402
from identity import DATASET, PRIVATE, Identities, opaque  # noqa: E402

OUT = DATASET / "clean"


def blocks(stream):
    """Yield (sha, path, patch_text) for every file in every commit of a `git log -p --unified=0` stream."""
    sha, path, patch = None, None, []
    for line in stream:
        if line.startswith("@@@"):
            if path is not None and sha:
                yield sha, path, "".join(patch)
            sha, path, patch = line[3:].strip(), None, []
        elif line.startswith("diff --git "):
            if path is not None and sha:
                yield sha, path, "".join(patch)
            head = line.rstrip("\n")
            path = head.rsplit(" b/", 1)[-1].strip('"') if " b/" in head else None
            patch = []
        elif path is not None:
            if line.startswith(("--- ", "+++ ", "index ", "new file", "deleted file", "similarity", "rename ", "old mode", "new mode", "Binary")):
                if line.startswith("Binary"):
                    patch = []
                continue
            patch.append(line)
    if path is not None and sha:
        yield sha, path, "".join(patch)


def main():
    OUT.mkdir(exist_ok=True)
    config = json.loads((PRIVATE / "teams_private.json").read_text(encoding="utf-8"))
    ids = Identities()
    rows, started = [], time.time()
    for team, info in config["teams"].items():
        for repo_id, (folder, _) in info["repos"].items():
            raw = json.loads((PRIVATE / "raw" / f"{repo_id}.json").read_text(encoding="utf-8"))
            wanted = {c["sha"] for c in raw["commits"]}
            path = Path(config["repos_dir"]) / folder
            if not (path / ".git").exists():
                print(f"  {repo_id}: repository not found, skipped")
                continue
            proc = subprocess.Popen(
                ["git", "-C", str(path), "log", "--all", "--no-merges", "-p", "--unified=0", "--format=tformat:@@@%H"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace")
            seen, n = set(), 0
            for sha, file_path, patch in blocks(proc.stdout):
                if sha not in wanted:
                    continue
                kind = classify_path(file_path)
                if kind not in SOURCE_KINDS:
                    continue
                s = stats_from_patch(file_path, patch)
                key = (sha, file_path)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "commit_id": opaque(sha), "repo_id": repo_id, "path": ids.scrub(file_path), "kind": kind,
                    **{f"a_{k}": v for k, v in s["added"].items()}, **{f"d_{k}": v for k, v in s["deleted"].items()}})
                n += 1
            proc.wait()
            print(f"  {repo_id}: {n} source-file diffs ({time.time() - started:.0f}s)", flush=True)
    with open(OUT / "commit_file_stats.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"commit_file_stats.csv: {len(rows)} rows")


if __name__ == "__main__":
    main()
