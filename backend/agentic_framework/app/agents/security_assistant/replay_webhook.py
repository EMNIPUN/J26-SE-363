"""Replay the sample GitHub payloads through handle_github_event, offline.

    uv run python -m app.agents.security_assistant.replay_webhook            # demo, no network
    uv run python -m app.agents.security_assistant.replay_webhook --run      # really clone + scan (needs
                                                                              # network, git and the scanners)

The payloads are signed here with a demo secret exactly as GitHub would sign them. By default the
pipeline is replaced by a stub that only prints what it would scan, so nothing is cloned.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.agents.security_assistant.webhook import DedupeStore, handle_github_event, sign

SAMPLES = Path(__file__).parent / "webhook_samples"
DEMO_SECRET = "demo-secret-not-for-production"
_RETARGET = None  # set by --repo-url


async def _stub_pipeline(repo_url, commit_sha, scan_type="full", **_):
    print(f"      (stub pipeline) would fetch {repo_url} at {commit_sha[:12]} and run a {scan_type} scan")
    from app.agents.security_assistant.schemas import ScanResult
    return ScanResult(run_id="demo", repo_path="-", repo_url=repo_url, commit_sha=commit_sha, scan_type=scan_type)


def _delivery(name: str, event: str, secret: str, *, tamper: bool = False, mutate=None) -> tuple[dict, bytes]:
    payload = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
    if _RETARGET:
        _RETARGET(payload)
    if mutate:
        mutate(payload)
    raw = json.dumps(payload).encode()
    signature = sign(secret, raw)
    if tamper:
        raw = raw + b" "  # body changed after signing
    return {"X-GitHub-Event": event, "X-Hub-Signature-256": signature, "X-GitHub-Delivery": "demo"}, raw


def _retargeter(repo_url: str, sha: str | None):
    """Point the sample payloads at a real public repository (for --run). Signatures are made after this change."""
    import subprocess

    sha = sha or subprocess.run(["git", "ls-remote", repo_url, "HEAD"], capture_output=True, text=True, check=True).stdout.split()[0]
    full = repo_url.rstrip("/").removesuffix(".git").split("github.com/")[-1]

    def apply(p: dict) -> None:
        repo = p["repository"]
        repo.update(full_name=full, name=full.split("/")[-1], html_url=f"https://github.com/{full}", clone_url=f"https://github.com/{full}.git")
        if "after" in p:
            p["after"] = sha
            p["head_commit"]["id"] = sha
            p["commits"][0]["id"] = sha
        if "pull_request" in p:
            p["pull_request"]["merge_commit_sha"] = sha

    return apply

async def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="really clone and scan instead of using the stub")
    ap.add_argument("--repo-url", help="with --run: scan this public https://github.com/owner/repo instead of the example repo in the payloads")
    ap.add_argument("--sha", help="with --repo-url: the 40-character commit to scan (default: the repo's current HEAD from git ls-remote)")
    args = ap.parse_args(argv)

    global _RETARGET
    _RETARGET = _retargeter(args.repo_url, args.sha) if args.repo_url else None
    kw = {} if args.run else {"pipeline": _stub_pipeline}
    store = DedupeStore()

    def draft(p): p["pull_request"]["draft"] = True
    def unmerged(p): p["pull_request"]["merged"] = False
    def gitlab(p): p["repository"]["clone_url"] = "https://gitlab.com/example/demo-shop.git"

    scenarios = [
        ("push to main", *_delivery("push.json", "push", DEMO_SECRET)),
        ("same push delivered again", *_delivery("push.json", "push", DEMO_SECRET)),
        ("merged pull request", *_delivery("pull_request_merged.json", "pull_request", DEMO_SECRET)),
        ("draft pull request", *_delivery("pull_request_merged.json", "pull_request", DEMO_SECRET, mutate=draft)),
        ("closed, not merged", *_delivery("pull_request_merged.json", "pull_request", DEMO_SECRET, mutate=unmerged)),
        ("body changed after signing", *_delivery("push.json", "push", DEMO_SECRET, tamper=True)),
        ("repository on gitlab.com", *_delivery("push.json", "push", DEMO_SECRET, mutate=gitlab)),
        ("ping event", {"X-GitHub-Event": "ping", "X-Hub-Signature-256": sign(DEMO_SECRET, b"{}")}, b"{}"),
    ]
    for title, headers, body in scenarios:
        print(f"- {title}")
        result = await handle_github_event(headers, body, secret=DEMO_SECRET, dedupe=store, **kw)
        print(f"    -> {result.status}: {result.reason}")
        if result.result is not None and args.run:
            print(f"       {len(result.result.findings)} findings, complete={result.result.complete}")
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":  # git/scanners are subprocesses: needs the Proactor loop
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
