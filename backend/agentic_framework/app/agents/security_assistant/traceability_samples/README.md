# Seeded requirement and task files

Small made-up files that match the Python demo repository (`tools/tests/demo_repos.py`, whose commits mention the task ids).
They also document the input formats of the `trace` command, which are the working contract with the Requirements agent
until that agent exists:

- `requirements.json`: `{"stories": [{"id", "title", "acceptance_criteria": [..]}]}`
- `tasks.json`: `{"tasks": [{"id", "title", "sprint", "story_id" (or null), "commits": [sha, ..]}]}`

Seeded on purpose: the CI workflow (`T-105`) has no story, so a finding in `.github/workflows/ci.yml` has no matching story.
