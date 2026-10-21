# Scrum simulator fixtures

This directory contains read-only Scrum-board fixtures used by the SELVIA
Performance Assessment module. A fixture is used only when its
`github_repo_url` matches the repository connected to the team.

The simulator is not a general sample-data fallback. If no fixture matches a
team repository, the API returns `404` and the assessment worker must not use
another project's sprints or tasks.

## How the flow works

1. A team connects a GitHub repository through the normal SELVIA GitHub
   integration.
2. The Core API obtains the team's connected repository URL.
3. `ScrumSimulator` loads the JSON files in this directory and validates them
   against the shared Scrum simulator contract.
4. The repository URL is normalized (HTTPS GitHub host, lowercase owner and
   repository, trailing slash removed) and compared with each fixture URL.
5. A matching fixture provides:
   - sprint metadata;
   - the project roster;
   - tasks assigned to fixture student IDs;
   - acceptance criteria;
   - optional task status history.
6. The assessment worker calls the Core API's internal Scrum routes. It passes
   the real repository URL on every request, so the Core API performs the
   repository match again.
7. The worker collects the selected sprint and tasks, then combines that Scrum
   evidence with GitHub repository evidence during assessment.

The implementation is in:

- `backend/server/app/modules/performance/scrum_simulator.py`
- `backend/server/app/api/v1/performance.py`
- `backend/agentic_framework/app/agents/performance_assessment/com_agent/ingestion/scrum_mcp_client.py`
- `backend/agentic_framework/app/agents/performance_assessment/assessment/graph.py`
- `backend/shared/src/shared/performance/contracts/scrum_simulator.schema.json`

## Fixture format

Each fixture is one JSON file with this top-level shape:

```json
{
  "schema_version": "1",
  "github_repo_url": "https://github.com/owner/repository",
  "project": {
    "project_id": "P-EXAMPLE",
    "project_name": "Example project",
    "project_domain": ""
  },
  "students": [
    {
      "student_id": "STU-001",
      "name": "Example student",
      "email": "student@example.com"
    }
  ],
  "sprints": [],
  "tasks": [],
  "status_history": {}
}
```

### Student mapping

`student_id` is the stable identifier used by tasks in the fixture.
`email` is the mapping value used to associate that fixture student with the
student already registered in the SELVIA team.

Do not add `account_id` or `github_login` to fixture files. Platform account
identity and linked GitHub identity already belong to SELVIA's team/member and
GitHub integration data. They must not be duplicated in a Scrum fixture.

Before enabling a fixture for a real team, fill every student's `email` with
the exact platform email used by the team member. Keep the value empty only
while preparing an incomplete fixture; an empty value cannot map a student to
an email-based platform roster.

Task `assignee_ids` must contain the corresponding fixture `student_id`
values, not platform account IDs or email addresses. Multiple IDs are allowed
for shared tasks.

## Available operations

The simulator supports these operations:

| Operation | Purpose |
|---|---|
| `list_sprints` | Return all fixture sprints with calculated task and story-point totals |
| `get_team_roster` | Return fixture student IDs, names, emails, and project team ID |
| `get_sprint_details` | Return one sprint's metadata and calculated totals |
| `get_student_tasks` | Return tasks for a sprint and fixture student ID |
| `get_task_acceptance_criteria` | Return one task's description and acceptance criteria |
| `get_task_status_history` | Return supplied status history or the task's final fixture status |

The worker-only route is:

```text
GET /api/v1/internal/scrum/{team_ref}/{operation}
```

Required query parameter:

```text
repo_url=https://github.com/owner/repository
```

Additional query parameters are used as appropriate:

```text
sprint_id=...
student_id=...
task_id=...
```

The route requires the `X-Internal-Token` header matching
`AI_BACKEND_INTERNAL_TOKEN`. It is intended for the assessment worker, not
for frontend clients.

## Enabling worker access

The worker normally uses the existing Scrum MCP provider. To use the
repository-matched Core API simulator, configure the worker environment:

```text
SCRUM_SIMULATOR_VIA_CORE_API=true
CORE_API_URL=http://localhost:8002/api/v1
AI_BACKEND_INTERNAL_TOKEN=<same value configured for the Core API>
```

`CORE_API_URL` may point to another Core API host in a deployed environment.
Do not commit tokens or `.env` contents.

## Adding or changing a fixture

1. Create or edit a `.json` file in this directory.
2. Set `github_repo_url` to the exact repository represented by the fixture.
3. Keep `schema_version` equal to `"1"`.
4. Use unique `student_id`, `sprint_id`, and `task_id` values within the
   fixture.
5. Put task ownership in `assignee_ids`.
6. Add the students' platform emails before running an assessment.
7. Validate the fixture by importing `ScrumSimulator` or running the server
   tests.
8. Confirm that an unrelated repository returns no match.

A fixture with an invalid shape causes simulator loading to fail explicitly;
it is not silently ignored. Multiple fixtures for the same normalized
repository are also rejected as an ambiguous configuration.

## Current fixture

`ethical-tourism-certification.json` represents:

- repository:
  `https://github.com/EMNIPUN/ethical-tourism-certification-system-backend`;
- project `P-ETCS`;
- four fixture students (`STU-001` through `STU-004`);
- four sprints;
- 27 tasks;
- Git-author-based ownership and email mappings supplied by the project
  history.

The student mappings currently identify Nipun Dhananjaya, Sadeesha Sathsara,
Chathush Vishmika, and Croos Eric Devon. The emails in the fixture are used
only to map these fixture students to the corresponding SELVIA team members;
GitHub login and platform account identifiers remain outside the fixture.

## Safety and data rules

- Never use a fixture for a repository it does not describe.
- Never copy sample students, marks, or sprints into a real unmatched team.
- Do not put passwords, tokens, GitHub app credentials, or other secrets in
  fixture files.
- Keep personal data to the minimum needed for email-based student mapping.
- Do not apply database migrations or write to the remote Supabase database
  while testing the simulator.
- The simulator is read-only; changes are made by editing version-controlled
  fixture JSON and redeploying/restarting the relevant service.
