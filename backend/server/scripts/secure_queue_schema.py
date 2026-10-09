"""Check or lock down Procrastinate's job-queue objects in the public schema.

Run from backend/server/ after `python -m scripts.install_queue_schema`, and again after every
Procrastinate upgrade:

    uv run python -m scripts.secure_queue_schema --check
    uv run python -m scripts.secure_queue_schema --apply

--check only reads the catalog (in a read-only transaction) and prints PASS/FAIL lines.
--apply, in one transaction: enables row level security (not forced, no policies) on the queue
tables, revokes every privilege on the queue tables and sequences from PUBLIC and the Supabase
browser roles (anon, authenticated, service_role, where they exist), and revokes EXECUTE on the
queue functions from the same grantees. The owner (the role the backend and worker connect as)
keeps full access because owners bypass RLS that isn't forced. Running it again changes nothing.

The target is --db-url, else SERVER_DIRECT_URL, else SERVER_DATABASE_URL. Only local databases
are accepted unless --allow-remote is passed. A remote target is also refused when it came from
SERVER_DATABASE_URL (the Core API's URL) or uses port 6543 (Supabase's transaction pooler), and a
Supabase target must set sslmode=verify-full and sslrootcert, as in alembic/env.py. Output never
contains a user name or password.
"""

import argparse
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.database.safety import (
    UnsafeDatabaseTarget,
    check_schema_change_source,
    check_tls,
    describe,
    is_local,
    parse_url,
)

SCHEMA = "public"
PREFIX = "procrastinate_"
QUEUE_TABLES = (
    "procrastinate_jobs",
    "procrastinate_events",
    "procrastinate_periodic_defers",
    "procrastinate_workers",
)
BROWSER_ROLES = ("anon", "authenticated", "service_role")
TABLE_KINDS = frozenset({"r", "p"})
SEQUENCE_KIND = "S"
# Indexes and the composite type behind procrastinate_job_to_defer_v1 need no privileges of their own.
IGNORED_KINDS = frozenset({"i", "I", "c"})
ROUTINE_KINDS = frozenset({"f", "p"})
LOCK_TIMEOUT = "10s"
SQLSTATE_HINTS = {
    "28P01": "authentication failed",
    "28000": "authorization failed",
    "3D000": "database does not exist",
    "42501": "permission denied",
    "55P03": "lock timeout; stop the worker and retry",
}

_quote = postgresql.dialect().identifier_preparer.quote

SIGNATURE_SQL = (
    "quote_ident(CAST(n.nspname AS text)) || '.' || quote_ident(CAST(p.proname AS text))"
    " || '(' || pg_catalog.pg_get_function_identity_arguments(p.oid) || ')'"
)

Q_CURRENT_USER = text("SELECT CAST(current_user AS text) AS role_name")

Q_BROWSER_ROLES = text(
    "SELECT CAST(rolname AS text) AS rolname FROM pg_catalog.pg_roles"
    " WHERE CAST(rolname AS text) = ANY(CAST(:roles AS text[])) ORDER BY rolname"
)

# procrastinate_* relations plus any sequence owned by a procrastinate_* table.
Q_RELATIONS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(c.relkind AS text) AS kind,
           CAST(pg_catalog.pg_get_userbyid(c.relowner) AS text) AS owner,
           c.relrowsecurity AS rls,
           c.relforcerowsecurity AS forced,
           EXISTS (
               SELECT 1 FROM pg_catalog.aclexplode(c.relacl) AS a WHERE a.grantee = 0
           ) AS public_access
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = :schema
      AND (
          starts_with(CAST(c.relname AS text), :prefix)
          OR (
              c.relkind = 'S'
              AND c.oid IN (
                  SELECT d.objid
                  FROM pg_catalog.pg_depend AS d
                  JOIN pg_catalog.pg_class AS t ON t.oid = d.refobjid
                  JOIN pg_catalog.pg_namespace AS tn ON tn.oid = t.relnamespace
                  WHERE d.classid = CAST('pg_catalog.pg_class' AS regclass)
                    AND d.refclassid = CAST('pg_catalog.pg_class' AS regclass)
                    AND d.deptype IN ('a', 'i')
                    AND tn.nspname = :schema
                    AND starts_with(CAST(t.relname AS text), :prefix)
              )
          )
      )
    ORDER BY c.relname
    """
)

Q_ROUTINES = text(
    f"""
    SELECT {SIGNATURE_SQL} AS signature,
           CAST(p.prokind AS text) AS kind,
           CAST(pg_catalog.pg_get_userbyid(p.proowner) AS text) AS owner,
           p.prosecdef AS security_definer,
           EXISTS (
               SELECT 1
               FROM pg_catalog.aclexplode(
                   COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))
               ) AS a
               WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'
           ) AS public_execute
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    WHERE n.nspname = :schema AND starts_with(CAST(p.proname AS text), :prefix)
    ORDER BY 1
    """
)

Q_POLICIES = text(
    "SELECT CAST(tablename AS text) AS name, CAST(policyname AS text) AS policy"
    " FROM pg_catalog.pg_policies"
    " WHERE schemaname = :schema AND starts_with(CAST(tablename AS text), :prefix)"
    " ORDER BY tablename, policyname"
)

# any_access: the role can do anything at all; full_access: it holds every privilege.
Q_RELATION_ACCESS = text(
    """
    SELECT CAST(c.relname AS text) AS object,
           CAST(r.rolname AS text) AS role,
           CASE WHEN c.relkind = 'S'
                THEN has_sequence_privilege(r.oid, c.oid, 'USAGE, SELECT, UPDATE')
                ELSE has_table_privilege(
                         r.oid, c.oid, 'SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER'
                     )
                     OR has_any_column_privilege(r.oid, c.oid, 'SELECT, INSERT, UPDATE, REFERENCES')
           END AS any_access,
           CASE WHEN c.relkind = 'S'
                THEN has_sequence_privilege(r.oid, c.oid, 'USAGE')
                     AND has_sequence_privilege(r.oid, c.oid, 'SELECT')
                     AND has_sequence_privilege(r.oid, c.oid, 'UPDATE')
                ELSE has_table_privilege(r.oid, c.oid, 'SELECT')
                     AND has_table_privilege(r.oid, c.oid, 'INSERT')
                     AND has_table_privilege(r.oid, c.oid, 'UPDATE')
                     AND has_table_privilege(r.oid, c.oid, 'DELETE')
                     AND has_table_privilege(r.oid, c.oid, 'TRUNCATE')
                     AND has_table_privilege(r.oid, c.oid, 'REFERENCES')
                     AND has_table_privilege(r.oid, c.oid, 'TRIGGER')
           END AS full_access
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema
      AND CAST(c.relname AS text) = ANY(CAST(:names AS text[]))
      AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)

Q_ROUTINE_ACCESS = text(
    f"""
    SELECT {SIGNATURE_SQL} AS object,
           CAST(r.rolname AS text) AS role,
           has_function_privilege(r.oid, p.oid, 'EXECUTE') AS any_access,
           has_function_privilege(r.oid, p.oid, 'EXECUTE') AS full_access
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema
      AND starts_with(CAST(p.proname AS text), :prefix)
      AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)


@dataclass(frozen=True)
class Relation:
    name: str
    kind: str
    owner: str
    rls: bool
    forced: bool
    public_access: bool


@dataclass(frozen=True)
class Routine:
    signature: str
    kind: str
    owner: str
    security_definer: bool
    public_execute: bool


@dataclass(frozen=True)
class Access:
    any_access: bool
    full_access: bool


@dataclass
class QueueSchema:
    current_user: str
    browser_roles: tuple[str, ...]
    tables: list[Relation] = field(default_factory=list)
    sequences: list[Relation] = field(default_factory=list)
    routines: list[Routine] = field(default_factory=list)
    unexpected: list[str] = field(default_factory=list)
    policies: list[tuple[str, str]] = field(default_factory=list)
    access: dict[tuple[str, str], Access] = field(default_factory=dict)

    def role_access(self, name: str, role: str) -> Access | None:
        """None when the catalog returned no record; callers must treat that as a failure."""
        return self.access.get((name, role))


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    subject: str
    description: str


class HardeningFailed(RuntimeError):
    """--apply stopped; the transaction is rolled back."""


def inspect_queue_schema(connection: Connection) -> QueueSchema:
    """Read everything the checks and statements need from the catalog. Read-only."""
    params = {"schema": SCHEMA, "prefix": PREFIX}
    current_user = connection.execute(Q_CURRENT_USER).scalar_one()
    roles = connection.execute(Q_BROWSER_ROLES, {"roles": list(BROWSER_ROLES)}).mappings().all()
    schema = QueueSchema(current_user, tuple(row["rolname"] for row in roles))

    for row in connection.execute(Q_RELATIONS, params).mappings().all():
        relation = Relation(
            row["name"], row["kind"], row["owner"], row["rls"], row["forced"], row["public_access"]
        )
        if relation.kind in TABLE_KINDS and relation.name in QUEUE_TABLES:
            schema.tables.append(relation)
        elif relation.kind == SEQUENCE_KIND:
            schema.sequences.append(relation)
        elif relation.kind not in IGNORED_KINDS:
            schema.unexpected.append(f"{relation.name} (relkind {relation.kind})")

    for row in connection.execute(Q_ROUTINES, params).mappings().all():
        schema.routines.append(
            Routine(
                row["signature"],
                row["kind"],
                row["owner"],
                row["security_definer"],
                row["public_execute"],
            )
        )

    schema.policies = [
        (row["name"], row["policy"])
        for row in connection.execute(Q_POLICIES, params).mappings().all()
    ]

    roles_to_check = [*schema.browser_roles, schema.current_user]
    names = [relation.name for relation in schema.tables + schema.sequences]
    access_rows = list(
        connection.execute(
            Q_RELATION_ACCESS, {**params, "names": names, "roles": roles_to_check}
        ).mappings().all()
    )
    access_rows += connection.execute(
        Q_ROUTINE_ACCESS, {**params, "roles": roles_to_check}
    ).mappings().all()
    schema.access = {
        (row["object"], row["role"]): Access(row["any_access"], row["full_access"])
        for row in access_rows
    }
    return schema


def find_problems(schema: QueueSchema) -> list[str]:
    """Reasons not to touch the schema at all. --apply refuses to run while any exist."""
    problems = []
    if schema.current_user in BROWSER_ROLES:
        problems.append(
            f"connected as {schema.current_user}; connect as the role that owns the queue tables"
        )
    found = {table.name for table in schema.tables}
    missing = [name for name in QUEUE_TABLES if name not in found]
    if missing:
        problems.append(
            f"missing queue tables: {', '.join(missing)}; install the schema first "
            "(python -m scripts.install_queue_schema), then run this script"
        )
    if not schema.routines:
        problems.append("no procrastinate_* functions found; is the queue schema installed?")
    for item in schema.unexpected:
        problems.append(f"unexpected object {item}; review this script before securing it")
    for routine in schema.routines:
        if routine.kind not in ROUTINE_KINDS:
            problems.append(f"unexpected routine {routine.signature} (prokind {routine.kind})")
        if routine.security_definer:
            problems.append(f"{routine.signature} is SECURITY DEFINER; review it before securing")
    for table, policy in schema.policies:
        problems.append(f"{table} already has policy {policy}; this script expects no policies")
    for table in schema.tables:
        if table.forced:
            problems.append(f"{table.name} has FORCE ROW LEVEL SECURITY; the worker would lose access")
    owned = [(relation.name, relation.owner) for relation in schema.tables + schema.sequences]
    owned += [(routine.signature, routine.owner) for routine in schema.routines]
    for name, owner in owned:
        if owner != schema.current_user:
            problems.append(f"{name} is owned by another role; connect as the role that owns it")
    return problems


def _object_checks(
    schema: QueueSchema, name: str, public_access: bool, closed_text: str, owner_text: str
) -> list[CheckResult]:
    """Fails closed: a missing permission record for an existing role counts as a FAIL."""
    roles = schema.browser_roles
    results = []
    missing = [
        role for role in (*roles, schema.current_user) if schema.role_access(name, role) is None
    ]
    if missing:
        results.append(CheckResult(False, name, f"no permission record for {', '.join(missing)}"))
    browser_access = [schema.role_access(name, role) for role in roles]
    closed = not public_access and all(
        access is not None and not access.any_access for access in browser_access
    )
    owner = schema.role_access(name, schema.current_user)
    results.append(CheckResult(closed, name, closed_text))
    results.append(CheckResult(owner is not None and owner.full_access, name, owner_text))
    return results


def check_schema(schema: QueueSchema) -> list[CheckResult]:
    """PASS/FAIL for every queue object, from an inspected schema. Pure.

    Browser roles that don't exist in the database are not checked; for those that do, every
    queue object must have a permission record showing no access.
    """
    grantees = ", ".join(("PUBLIC", *schema.browser_roles))
    results = []
    for table in schema.tables:
        results.append(
            CheckResult(table.rls and not table.forced, table.name, "row level security on, not forced")
        )
    for relation in schema.tables + schema.sequences:
        results += _object_checks(
            schema,
            relation.name,
            relation.public_access,
            f"no privileges for {grantees}",
            "owner role keeps full access",
        )
    for routine in schema.routines:
        results += _object_checks(
            schema,
            routine.signature,
            routine.public_execute,
            f"no EXECUTE for {grantees}",
            "owner role can execute",
        )
    return results


def _qualified(name: str) -> str:
    return f"{_quote(SCHEMA)}.{_quote(name)}"


def hardening_statements(schema: QueueSchema) -> list[str]:
    """The statements --apply runs. Pure, and the same on every run, so applying is repeatable."""
    grantees = ", ".join(
        ["PUBLIC"] + [_quote(role) for role in schema.browser_roles if role != schema.current_user]
    )
    tables = sorted(table.name for table in schema.tables)
    sequences = sorted(sequence.name for sequence in schema.sequences)
    statements = [f"ALTER TABLE {_qualified(name)} ENABLE ROW LEVEL SECURITY" for name in tables]
    if tables:
        statements.append(
            f"REVOKE ALL ON TABLE {', '.join(map(_qualified, tables))} FROM {grantees}"
        )
    if sequences:
        statements.append(
            f"REVOKE ALL ON SEQUENCE {', '.join(map(_qualified, sequences))} FROM {grantees}"
        )
    for routine in sorted(schema.routines, key=lambda item: item.signature):
        statements.append(f"REVOKE EXECUTE ON ROUTINE {routine.signature} FROM {grantees}")
    return statements


def print_results(problems: Iterable[str], results: Iterable[CheckResult]) -> bool:
    ok = True
    for problem in problems:
        ok = False
        print(f"FAIL | schema | {problem}")
    for result in results:
        ok = ok and result.ok
        print(f"{'PASS' if result.ok else 'FAIL'} | {result.subject} | {result.description}")
    return ok


def run_check(engine: Engine) -> int:
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        schema = inspect_queue_schema(connection)
        connection.rollback()
    ok = print_results(find_problems(schema), check_schema(schema))
    print("Queue schema is secured." if ok else "Queue schema is NOT secured.")
    return 0 if ok else 1


def run_apply(engine: Engine) -> int:
    try:
        with engine.begin() as connection:
            connection.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            schema = inspect_queue_schema(connection)
            problems = find_problems(schema)
            if problems:
                print_results(problems, [])
                raise HardeningFailed("nothing was changed")
            for statement in hardening_statements(schema):
                print(f"RUN  | {statement}")
                connection.execute(text(statement))
            after = inspect_queue_schema(connection)
            if not print_results(find_problems(after), check_schema(after)):
                raise HardeningFailed("verification failed; all changes were rolled back")
    except HardeningFailed as error:
        print(f"Queue schema was NOT secured: {error}.")
        return 1
    print("Queue schema is secured.")
    return 0


def safe_error_summary(error: DBAPIError) -> str:
    """Exception class and SQLSTATE only.

    Driver and server messages can contain the user name (on Supabase it includes the project
    reference), the host or the database name, so they are never printed.
    """
    sqlstate = getattr(error.orig, "sqlstate", None)
    hint = SQLSTATE_HINTS.get(sqlstate or "", "details hidden")
    return f"database error {type(error.orig).__name__} (SQLSTATE {sqlstate or 'unknown'}: {hint})"


def target_source(db_url: str | None) -> tuple[str, URL]:
    """(where the URL came from, the URL)."""
    sources = (
        ("--db-url", db_url),
        ("SERVER_DIRECT_URL", settings.SERVER_DIRECT_URL),
        ("SERVER_DATABASE_URL", settings.SERVER_DATABASE_URL),
    )
    for name, raw in sources:
        if raw and raw.strip():
            url = parse_url(raw.strip(), name)
            if url.drivername == "postgresql":
                url = url.set(drivername="postgresql+psycopg")
            return name, url
    raise UnsafeDatabaseTarget(
        "No database URL: pass --db-url or set SERVER_DIRECT_URL or SERVER_DATABASE_URL"
    )


def check_target(url: URL, allow_remote: bool) -> None:
    if url.get_backend_name() != "postgresql":
        raise UnsafeDatabaseTarget(f"Refusing {describe(url)}: the queue schema lives in PostgreSQL")
    if not is_local(url) and not allow_remote:
        raise UnsafeDatabaseTarget(
            f"Refusing to run against {describe(url)}: it is not a local database. "
            "Pass --allow-remote only if you really mean to use that database."
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.secure_queue_schema",
        description="Check or secure Procrastinate's queue objects in the public schema.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only PASS/FAIL report")
    mode.add_argument("--apply", action="store_true", help="secure the queue objects (one transaction)")
    parser.add_argument("--db-url", help="target database (default: SERVER_DIRECT_URL, then SERVER_DATABASE_URL)")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-local database")
    args = parser.parse_args(argv)

    try:
        source, url = target_source(args.db_url)
        check_target(url, args.allow_remote)
        check_schema_change_source(url, source, "--db-url")
        check_tls(url)
    except UnsafeDatabaseTarget as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(f"Target database: {describe(url)}")
    if not is_local(url):
        print("WARNING: remote database allowed by --allow-remote", file=sys.stderr)

    engine = create_engine(url, poolclass=NullPool)
    try:
        return run_check(engine) if args.check else run_apply(engine)
    except DBAPIError as error:
        print(f"ERROR: {safe_error_summary(error)}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
