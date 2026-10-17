import uuid
from datetime import UTC, datetime

import pytest
from shared.contracts import UserRole
from sqlalchemy import LargeBinary, create_engine, event, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.database.base import Base
from app.models import (
    AgentRun,
    AgentRunStatus,
    Group,
    GroupMember,
    Project,
    ProjectDocument,
    User,
)

APP_TABLES = {"users", "groups", "group_members", "projects", "project_documents", "agent_runs"}


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    event.listen(
        engine, "connect", lambda dbapi_conn, _: dbapi_conn.execute("PRAGMA foreign_keys=ON")
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def add_user(db: Session, sub: str = "kc-lecturer-1", role: UserRole = UserRole.LECTURER, **fields) -> User:
    user = User(keycloak_sub=sub, role=role, name=fields.pop("name", "Dr. Perera"), **fields)
    db.add(user)
    db.flush()
    return user


def add_group(db: Session, code: str = "J26-SE-363") -> Group:
    group = Group(code=code, name=f"Group {code}")
    db.add(group)
    db.flush()
    return group


def add_project(db: Session, group: Group, lecturer: User, title: str = "SELVIA") -> Project:
    project = Project(group_id=group.id, created_by_id=lecturer.id, title=title)
    db.add(project)
    db.flush()
    return project


# --- metadata -----------------------------------------------------------------


def test_all_application_tables_are_registered():
    assert set(Base.metadata.tables) == APP_TABLES


def test_agent_run_status_values():
    assert [status.value for status in AgentRunStatus] == ["queued", "running", "succeeded", "failed"]


def test_postgres_ddl_uses_jsonb_and_status_check():
    ddl = str(CreateTable(AgentRun.__table__).compile(dialect=postgresql.dialect()))

    assert "response JSONB" in ddl
    assert "error JSONB" in ddl
    assert "CONSTRAINT ck_agent_runs_status CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))" in ddl


# --- users and groups --------------------------------------------------------------


def test_keycloak_subject_is_unique(session):
    add_user(session, sub="kc-1")
    session.add(User(keycloak_sub="kc-1", role=UserRole.STUDENT, name="Someone Else"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_student_number_is_optional_but_unique(session):
    add_user(session, sub="kc-1")
    add_user(session, sub="kc-2")
    add_user(session, sub="kc-3", role=UserRole.STUDENT, student_number="IT21000001")
    session.add(User(keycloak_sub="kc-4", role=UserRole.STUDENT, name="Kamal", student_number="IT21000001"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_user_role_must_be_a_known_role(session):
    session.add(User(keycloak_sub="kc-1", role="superuser", name="Nobody"))

    with pytest.raises(StatementError):
        session.flush()


def test_group_code_is_unique(session):
    add_group(session, "J26-SE-363")
    session.add(Group(code="J26-SE-363", name="Duplicate"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_user_can_be_in_several_groups(session):
    student = add_user(session, sub="kc-student", role=UserRole.STUDENT)
    for code in ("J26-SE-363", "J26-SE-364"):
        session.add(GroupMember(group_id=add_group(session, code).id, user_id=student.id))

    session.flush()

    assert len(student.memberships) == 2


def test_group_membership_pair_is_unique(session):
    student = add_user(session, sub="kc-student", role=UserRole.STUDENT)
    group = add_group(session)
    session.add(GroupMember(group_id=group.id, user_id=student.id))
    session.flush()
    session.add(GroupMember(group_id=group.id, user_id=student.id))

    with pytest.raises(IntegrityError):
        session.flush()


# --- projects and documents ----------------------------------------------------------


def test_project_requires_a_group(session):
    lecturer = add_user(session)
    session.add(Project(created_by_id=lecturer.id, title="SELVIA"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_project_group_must_exist(session):
    lecturer = add_user(session)
    session.add(Project(group_id=uuid.uuid4(), created_by_id=lecturer.id, title="SELVIA"))

    with pytest.raises(IntegrityError):
        session.flush()


def test_project_titles_are_not_unique(session):
    lecturer = add_user(session)
    add_project(session, add_group(session, "J26-SE-363"), lecturer, title="Smart Campus")
    add_project(session, add_group(session, "J26-SE-364"), lecturer, title="Smart Campus")

    titles = session.scalars(select(Project.title)).all()

    assert titles == ["Smart Campus", "Smart Campus"]


def test_project_records_its_group_and_lecturer_with_timestamps(session):
    lecturer = add_user(session)
    group = add_group(session)
    project = add_project(session, group, lecturer)

    assert project.group is group
    assert project.created_by is lecturer
    assert project.created_at is not None
    assert project.updated_at is not None


def test_project_documents_store_a_storage_reference_not_file_bytes():
    columns = ProjectDocument.__table__.columns

    assert not any(isinstance(column.type, LargeBinary) for column in columns)
    assert columns["storage_key"].unique
    assert not columns["storage_key"].nullable


def test_deleting_a_project_deletes_its_documents(session):
    project = add_project(session, add_group(session), add_user(session))
    session.add(
        ProjectDocument(
            project_id=project.id,
            original_filename="guidance.pdf",
            content_type="application/pdf",
            storage_key=f"projects/{project.id}/guidance.pdf",
        )
    )
    session.flush()

    session.delete(project)
    session.flush()

    assert session.scalars(select(ProjectDocument)).all() == []


# --- agent runs -------------------------------------------------------------------


def test_agent_run_defaults_to_queued_and_stores_json(session):
    response = {
        "request_id": "req-1",
        "status": "succeeded",
        "result": {"sprints": [{"number": 1, "tasks": ["Set up repo"]}]},
    }
    run = AgentRun(
        request_id="req-1",
        action="planning.analyze_guidance",
        requester_id="kc-lecturer-1",
        requester_role=UserRole.LECTURER,
        project_id="p-1",
    )
    session.add(run)
    session.flush()
    assert run.status is AgentRunStatus.QUEUED

    run.status = AgentRunStatus.SUCCEEDED
    run.response = response
    session.commit()
    session.expire_all()

    stored = session.get(AgentRun, run.id)
    assert stored.status is AgentRunStatus.SUCCEEDED
    assert stored.response == response
    assert stored.error is None


def test_agent_run_request_id_is_unique(session):
    for _ in range(2):
        session.add(AgentRun(request_id="req-1", requester_id="kc-1", requester_role=UserRole.STUDENT))

    with pytest.raises(IntegrityError):
        session.flush()


def test_agent_run_rejects_unknown_status_from_the_orm(session):
    session.add(
        AgentRun(request_id="req-1", requester_id="kc-1", requester_role=UserRole.STUDENT, status="cancelled")
    )

    with pytest.raises(StatementError):
        session.flush()


def test_agent_run_status_check_constraint_rejects_raw_sql(session):
    now = datetime.now(UTC)

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO agent_runs (id, request_id, requester_id, requester_role, status, created_at, updated_at) "
                "VALUES (:id, 'req-1', 'kc-1', 'student', 'cancelled', :now, :now)"
            ),
            {"id": uuid.uuid4().hex, "now": now},
        )
