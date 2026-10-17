# Core Domain Models

SQLAlchemy models for the Core API database:

| Module | Models |
|---|---|
| `user.py` | `User` |
| `group.py` | `Group`, `GroupMember` |
| `project.py` | `Project`, `ProjectDocument` |
| `agent_run.py` | `AgentRun`, `AgentRunStatus` |

Every new model must be imported in `__init__.py`, otherwise Alembic's autogenerate won't see it.
Schema changes always go through a migration (`docs/SERVER_DATABASE_GUIDE.md`, section 3).
