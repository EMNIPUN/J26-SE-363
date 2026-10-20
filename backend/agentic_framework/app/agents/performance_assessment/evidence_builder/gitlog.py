"""Reading commit history and patches out of the read-only workspace (WorkspaceManager.read).

``fetch_commits`` returns every commit of every branch with its line counts; ``fetch_patches`` returns the unified diffs (no context lines) of chosen commits, which the
factors turn into clean line counts (code / comment / blank / format-only) with evidence.lines.stats_from_patch.
"""
import re

LOG_FORMAT = "--format=%x1e%H%x1f%P%x1f%aN%x1f%aE%x1f%aI%x1f%s%x1f%b%x1e"
SHA = re.compile(r"^[0-9a-f]{40}$")
CHUNK = 60
HEADER_PREFIXES = ("--- ", "+++ ", "index ", "new file mode", "deleted file mode", "old mode", "new mode", "similarity index", "rename from", "rename to", "copy from", "copy to")


def parse_log(text: str) -> list[dict]:
    """[{sha, parents, author_name, author_email, authored_at, subject, body, files: [(path, added|None, deleted|None)]}], newest first."""
    parts = text.split("\x1e")
    out = []
    for i in range(1, len(parts) - 1, 2):
        f = parts[i].split("\x1f")
        if len(f) < 6 or not SHA.match(f[0]):
            continue
        files = []
        for line in parts[i + 1].splitlines():
            m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", line)
            if m:
                a, d = m.group(1), m.group(2)
                files.append((m.group(3), None if a == "-" else int(a), None if d == "-" else int(d)))
        out.append({"sha": f[0], "parents": f[1].split(), "author_name": f[2], "author_email": f[3], "authored_at": f[4], "subject": f[5], "body": f[6] if len(f) > 6 else "", "files": files})
    return out


def parse_patches(text: str) -> dict[str, dict[str, str]]:
    """{sha: {path: patch}} from ``git log -p --unified=0 --format=tformat:@@@%H``. Binary files get an empty patch."""
    out, sha, path, buf, in_hunk = {}, None, None, [], False

    def flush():
        if sha and path is not None:
            out.setdefault(sha, {})[path] = "\n".join(buf)

    for line in text.splitlines():
        if line.startswith("@@@") and SHA.match(line[3:]):
            flush()
            sha, path, buf, in_hunk = line[3:], None, [], False
        elif line.startswith("diff --git "):
            flush()
            path, buf, in_hunk = line.rsplit(" b/", 1)[-1], [], False
        elif path is None:
            continue
        elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
            buf, in_hunk = [], True
        elif not in_hunk and line.startswith("@@"):
            in_hunk = True
            buf.append(line)
        elif in_hunk:
            buf.append(line)
        elif line.startswith(HEADER_PREFIXES):
            continue
    flush()
    return out


def fetch_commits(ws, repo_url: str, token=None) -> list[dict]:
    return parse_log(ws.read(repo_url, "log", "--all", "--numstat", "--no-renames", LOG_FORMAT, token=token))


def fetch_patches(ws, repo_url: str, shas: list[str], token=None) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    shas = [s for s in dict.fromkeys(shas) if SHA.match(s)]
    for i in range(0, len(shas), CHUNK):
        text = ws.read(repo_url, "log", "--no-walk=unsorted", "--no-merges", "-p", "--unified=0", "--no-renames", "--format=tformat:@@@%H", *shas[i:i + CHUNK], token=token)
        out.update(parse_patches(text))
    return out
