"""Read-only preflight for the Core API database, run before migrating Supabase.

Run from backend/server/ against the URL that `alembic upgrade` will use (SERVER_DIRECT_URL, the
session pooler on port 5432):

    uv run python -m scripts.supabase_preflight

The URL comes only from SELVIA_PREFLIGHT_DATABASE_URL or, when that is unset, from a hidden
prompt; the expected Supabase project reference likewise comes from
SELVIA_PREFLIGHT_EXPECTED_PROJECT_REF or a hidden prompt. There is no fallback to
SERVER_DIRECT_URL, SERVER_DATABASE_URL or any .env file: this module never imports
app.core.config.

Before connecting, the target must be a Supabase host with the expected project reference, and the
URL must set sslmode=verify-full and sslrootcert, a readable PEM file with the Supabase CA
certificate (verify-ca and require only with --allow-unverified-tls, as a WARN). libpq then
verifies the certificate chain and host name during the TLS handshake, before the password is
sent. --local-test instead accepts only a local *_test
database, for testing this script. In both modes PGHOSTADDR, PGSERVICE, PGSERVICEFILE and
PGOPTIONS must be unset and the URL must not set `service` or `options`.

After connecting, inside a READ ONLY transaction, the database name, role, server version, current
schema, search_path and Supabase's own schemas and roles are read, printed and checked, and you are
asked to confirm (--yes skips the question, never the checks). search_path is checked after those
identity reads but before anything else. Only then are the catalog and the Alembic version table
read, in a second READ ONLY transaction that is rolled back.

The report covers the Core API tables' column, constraint and index definitions against the models,
the Alembic revision against this repository, row level security, table and column grants,
policies and default privileges, the roles used for migrations, the Core API and the worker,
Procrastinate's objects against the installed version's schema.sql, the roles the Data API's
authenticator role can switch to (directly or through nested memberships), access by PUBLIC, the
browser roles and those roles to every relation (views, materialized views, foreign tables and
sequences included) and routine in the public schema, SECURITY DEFINER routines, and anything else
in the public schema.

The identity block prints the connected database role (current_user) on purpose, so you can confirm
it. Output never contains the URL, its user field (on the pooler, `postgres.<project-ref>`), the
password, the certificate path, the project reference, a refused host, or the value of a refused
environment variable. Database errors show the driver class, the SQLSTATE and a fixed hint, never
the server's message, plus whether they happened while connecting or after connecting.

Exit codes:
  0  no FAIL or LIMITED finding (WARNs still need review);
  1  at least one FAIL or LIMITED finding, a database error (including a failed or lost
     connection) or an unexpected error;
  2  refused: a missing or invalid URL or project reference, the target or TLS checks, a libpq
     environment variable or URL parameter, the identity checks, an identity change between the
     transactions, a transaction that isn't read-only, or no confirmation.
Ctrl+C isn't caught: Python prints its standard traceback instead of a sanitised error line and
exits with its own interrupt status; closing the connection rolls back any open transaction.
"""

import argparse
import getpass
import importlib.util
import os
import re
import sys
import traceback
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib.metadata import version as package_version
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import URL, Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

SERVER_DIR = Path(__file__).resolve().parents[1]


def _load_safety():
    path = SERVER_DIR / "app" / "database" / "safety.py"
    spec = importlib.util.spec_from_file_location("_preflight_safety", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Loaded by file path: importing the app.database package imports app.core.config, which reads
# backend/server/.env.
safety = _load_safety()

URL_ENV = "SELVIA_PREFLIGHT_DATABASE_URL"
PROJECT_REF_ENV = "SELVIA_PREFLIGHT_EXPECTED_PROJECT_REF"
SUPABASE_DATABASE = "postgres"
SUPABASE_HOST_SUFFIXES = (".supabase.com", ".supabase.co")
SUPABASE_SCHEMAS = ("auth", "storage")
PROJECT_HOST = re.compile(r"^(?:db\.)?([a-z0-9]+)\.supabase\.co$")
# Refused hosts are never printed: a malformed one may contain a project reference that
# PROJECT_HOST can't find to mask, or a private IP address.
HOST_NOT_ACCEPTED = "a host in the URL is not an accepted Supabase host; host details are omitted"
VERIFIED_SSLMODE = "verify-full"
UNVERIFIED_SSLMODE = "require"
# Checks the certificate chain but not the host name, so it also needs --allow-unverified-tls.
CHAIN_ONLY_SSLMODE = "verify-ca"
SYSTEM_ROOT_CERTS = "system"
# libpq reads sslrootcert as PEM; a CA file is a few KB, so this cap only guards against a wrong path.
PEM_CERTIFICATE = b"-----BEGIN CERTIFICATE-----"
MAX_ROOT_CERT_BYTES = 1024 * 1024
# Read by libpq for anything the URL doesn't set; each could move the connection away from the
# validated host or change the session the checks run in.
UNSAFE_LIBPQ_VARIABLES = {
    "PGHOSTADDR": "connects to that IP address instead of the validated host",
    "PGSERVICE": "applies the settings of a pg_service.conf entry",
    "PGSERVICEFILE": "points libpq at a service file whose settings could apply",
    "PGOPTIONS": "changes session settings such as search_path or the role",
}
TRANSACTION_POOLER_PORT = 6543
STATEMENT_TIMEOUT = "30s"
LOCK_TIMEOUT = "5s"
CONNECT_TIMEOUT_SECONDS = 10

SCHEMA = "public"
VERSION_TABLE = "alembic_version"
# From this revision on, RLS is on and the browser roles have no access (see the migration).
SECURITY_REVISION = "4f6d2a9c8e1b"
QUEUE_PREFIX = "procrastinate_"
QUEUE_TABLES = (
    "procrastinate_jobs",
    "procrastinate_events",
    "procrastinate_periodic_defers",
    "procrastinate_workers",
)
BROWSER_ROLES = ("anon", "authenticated", "service_role")
# The Data API logs in as this role and runs each request after SET ROLE to the role in the JWT.
AUTHENTICATOR = "authenticator"
TABLE_KINDS = frozenset({"r", "p"})
KIND_NAMES = {
    "r": "table",
    "p": "partitioned table",
    "v": "view",
    "m": "materialized view",
    "S": "sequence",
    "f": "foreign table",
}
TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
APP_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")
COLUMN_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "REFERENCES")
SEQUENCE_PRIVILEGES = ("USAGE", "SELECT", "UPDATE")
OBJECT_KINDS = ("r", "p", "v", "m", "f", "S")
TRUE_OPTION_VALUES = frozenset({"true", "on", "yes", "1", "t", "y"})
DEFAULT_ACL_OBJECTS = {"r": "tables", "S": "sequences", "f": "functions", "T": "types", "n": "schemas"}
MIGRATION_DEFAULT_ACL_OBJECTS = frozenset({"r", "S", "f"})
SQLSTATE_HINTS = {
    "08001": "could not connect",
    "08006": "connection failure",
    "28P01": "authentication failed",
    "28000": "authorization failed",
    "3D000": "database does not exist",
    "42501": "permission denied",
    "55P03": "lock timeout",
    "57014": "statement timeout",
}
# libpq's English messages for failures before a session exists; checked in order.
CONNECTION_FAILURE_HINTS = (
    ("password authentication failed", "authentication failed: wrong user name or password"),
    ("no password supplied", "the server asked for a password and the URL has none"),
    ("no pg_hba.conf entry", "pg_hba.conf has no entry allowing this user, database and host"),
    # Before "does not exist": libpq reports a missing file as 'root certificate file "…" does not exist'.
    ("certificate file", "a certificate file could not be read (the path is not printed)"),
    ("does not exist", "the database or role does not exist"),
    ("connection refused", "connection refused: is the server running on that host and port?"),
    ("timeout expired", "the connection timed out"),
    ("could not translate host name", "the host name could not be resolved"),
    ("certificate", "the server certificate could not be verified"),
    ("ssl", "TLS negotiation failed"),
)
QUEUE_OBJECT = re.compile(r"^CREATE (?:UNIQUE )?(TABLE|FUNCTION|TYPE|TRIGGER|INDEX) (\w+)", re.MULTILINE)

PASS, INFO, WARN, FAIL, LIMITED = "PASS", "INFO", "WARN", "FAIL", "LIMITED"
LEVELS = (PASS, INFO, WARN, FAIL, LIMITED)
BLOCKING = frozenset({FAIL, LIMITED})

_quote = postgresql.dialect().identifier_preparer.quote

# --- the Core API tables as the models and migration c9da91ebdddb define them ---------------
# Kept here because importing app.models would read backend/server/.env;
# tests/test_supabase_preflight.py checks this copy against the models.

UUID = "uuid"
TEXT = "text"
JSONB = "jsonb"
TIMESTAMPTZ = "timestamp with time zone"


def varchar(length: int) -> str:
    return f"character varying({length})"


FK_NO_ACTION, FK_RESTRICT, FK_CASCADE = "a", "r", "c"
FK_ACTIONS = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}
FK_MATCH_SIMPLE = "s"
ROLE_VALUES = frozenset({"student", "lecturer", "admin"})
STATUS_VALUES = frozenset({"queued", "running", "succeeded", "failed"})


@dataclass(frozen=True)
class ForeignKey:
    columns: tuple[str, ...]
    table: str
    referred: tuple[str, ...]
    on_delete: str  # pg_constraint.confdeltype
    on_update: str = FK_NO_ACTION


@dataclass(frozen=True)
class Index:
    columns: tuple[str, ...]
    unique: bool = False


@dataclass(frozen=True)
class TableSpec:
    """Columns have no server default, identity or generation; every constraint is validated and
    not deferrable; every index is a plain btree index without expressions or a WHERE clause."""

    columns: Mapping[str, tuple[str, bool]]  # name -> (type as format_type() prints it, NOT NULL)
    primary_key: tuple[str, ...]
    unique: Mapping[str, tuple[str, ...]]  # constraint name -> columns
    foreign_keys: Mapping[str, ForeignKey]
    checks: Mapping[str, tuple[str, frozenset[str]]]  # name -> (column, allowed values)
    indexes: Mapping[str, Index]  # indexes that don't back a constraint

    def constraint_kinds(self, table: str) -> dict[str, str]:
        """Constraint name -> pg_constraint.contype."""
        kinds = {f"pk_{table}": "p"}
        kinds |= {name: "u" for name in self.unique}
        kinds |= {name: "f" for name in self.foreign_keys}
        kinds |= {name: "c" for name in self.checks}
        return kinds


TIMESTAMPS = {"created_at": (TIMESTAMPTZ, True), "updated_at": (TIMESTAMPTZ, True)}

APP_TABLES: dict[str, TableSpec] = {
    "users": TableSpec(
        columns={
            "id": (UUID, True),
            "keycloak_sub": (varchar(255), True),
            "role": (varchar(8), True),
            "name": (varchar(255), True),
            "student_number": (varchar(32), False),
            **TIMESTAMPS,
        },
        primary_key=("id",),
        unique={
            "uq_users_keycloak_sub": ("keycloak_sub",),
            "uq_users_student_number": ("student_number",),
        },
        foreign_keys={},
        checks={"ck_users_role": ("role", ROLE_VALUES)},
        indexes={},
    ),
    "groups": TableSpec(
        columns={
            "id": (UUID, True),
            "code": (varchar(64), True),
            "name": (varchar(255), True),
            **TIMESTAMPS,
        },
        primary_key=("id",),
        unique={"uq_groups_code": ("code",)},
        foreign_keys={},
        checks={},
        indexes={},
    ),
    "group_members": TableSpec(
        columns={"id": (UUID, True), "group_id": (UUID, True), "user_id": (UUID, True)},
        primary_key=("id",),
        unique={"uq_group_members_group_id_user_id": ("group_id", "user_id")},
        foreign_keys={
            "fk_group_members_group_id_groups": ForeignKey(("group_id",), "groups", ("id",), FK_CASCADE),
            "fk_group_members_user_id_users": ForeignKey(("user_id",), "users", ("id",), FK_CASCADE),
        },
        checks={},
        indexes={"ix_group_members_user_id": Index(("user_id",))},
    ),
    "projects": TableSpec(
        columns={
            "id": (UUID, True),
            "group_id": (UUID, True),
            "created_by_id": (UUID, True),
            "title": (varchar(255), True),
            "description": (TEXT, False),
            **TIMESTAMPS,
        },
        primary_key=("id",),
        unique={},
        foreign_keys={
            "fk_projects_created_by_id_users": ForeignKey(("created_by_id",), "users", ("id",), FK_RESTRICT),
            "fk_projects_group_id_groups": ForeignKey(("group_id",), "groups", ("id",), FK_RESTRICT),
        },
        checks={},
        indexes={
            "ix_projects_created_by_id": Index(("created_by_id",)),
            "ix_projects_group_id": Index(("group_id",)),
        },
    ),
    "project_documents": TableSpec(
        columns={
            "id": (UUID, True),
            "project_id": (UUID, True),
            "original_filename": (varchar(255), True),
            "content_type": (varchar(255), True),
            "storage_key": (varchar(1024), True),
            **TIMESTAMPS,
        },
        primary_key=("id",),
        unique={"uq_project_documents_storage_key": ("storage_key",)},
        foreign_keys={
            "fk_project_documents_project_id_projects": ForeignKey(
                ("project_id",), "projects", ("id",), FK_CASCADE
            ),
        },
        checks={},
        indexes={"ix_project_documents_project_id": Index(("project_id",))},
    ),
    "agent_runs": TableSpec(
        columns={
            "id": (UUID, True),
            "request_id": (varchar(64), True),
            "action": (varchar(128), False),
            "requester_id": (varchar(255), True),
            "requester_role": (varchar(8), True),
            "student_id": (varchar(255), False),
            "group_id": (varchar(255), False),
            "project_id": (varchar(255), False),
            "sprint_id": (varchar(255), False),
            "task_id": (varchar(255), False),
            "status": (varchar(9), True),
            "response": (JSONB, False),
            "error": (JSONB, False),
            **TIMESTAMPS,
        },
        primary_key=("id",),
        unique={"uq_agent_runs_request_id": ("request_id",)},
        foreign_keys={},
        checks={
            "ck_agent_runs_requester_role": ("requester_role", ROLE_VALUES),
            "ck_agent_runs_status": ("status", STATUS_VALUES),
        },
        indexes={
            "ix_agent_runs_group_id": Index(("group_id",)),
            "ix_agent_runs_project_id": Index(("project_id",)),
            "ix_agent_runs_requester_id": Index(("requester_id",)),
            "ix_agent_runs_status": Index(("status",)),
        },
    ),
}

# --- queries: catalog reads, one data read (the Alembic version), no writes ------------------

Q_SET_READ_ONLY = text("SET TRANSACTION READ ONLY")
Q_STATEMENT_TIMEOUT = text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
Q_LOCK_TIMEOUT = text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
Q_READ_ONLY_STATUS = text("SHOW transaction_read_only")

Q_IDENTITY = text(
    "SELECT CAST(pg_catalog.current_database() AS text) AS database_name,"
    " CAST(current_user AS text) AS role_name,"
    " CAST(session_user AS text) AS session_role,"
    " pg_catalog.current_setting('server_version') AS server_version,"
    " CAST(pg_catalog.current_schema() AS text) AS schema_name,"
    " pg_catalog.current_setting('search_path') AS search_path"
)

Q_SCHEMAS_PRESENT = text(
    "SELECT CAST(nspname AS text) FROM pg_catalog.pg_namespace"
    " WHERE CAST(nspname AS text) = ANY(CAST(:names AS text[])) ORDER BY 1"
)

Q_ROLES_PRESENT = text(
    "SELECT CAST(rolname AS text) FROM pg_catalog.pg_roles"
    " WHERE CAST(rolname AS text) = ANY(CAST(:names AS text[])) ORDER BY 1"
)

Q_ROLES = text(
    "SELECT CAST(rolname AS text) AS name, rolsuper, rolbypassrls, rolcanlogin"
    " FROM pg_catalog.pg_roles WHERE CAST(rolname AS text) = ANY(CAST(:names AS text[]))"
)

Q_AUTHENTICATOR = text(
    "SELECT rolsuper, rolbypassrls, rolcanlogin FROM pg_catalog.pg_roles"
    " WHERE CAST(rolname AS text) = :name"
)

# Every membership grant. set_option exists from PostgreSQL 16 (SET ROLE needs it on each grant in
# the chain); before that any membership allows SET ROLE, hence the default of true.
Q_ROLE_MEMBERSHIPS = text(
    """
    SELECT CAST(m.rolname AS text) AS member,
           CAST(g.rolname AS text) AS granted,
           COALESCE(CAST(pg_catalog.to_jsonb(a) ->> 'set_option' AS boolean), true) AS can_set
    FROM pg_catalog.pg_auth_members AS a
    JOIN pg_catalog.pg_roles AS m ON m.oid = a.member
    JOIN pg_catalog.pg_roles AS g ON g.oid = a.roleid
    """
)

Q_SCHEMA_ACCESS = text(
    "SELECT CAST(r.rolname AS text) AS role_name,"
    " pg_catalog.has_schema_privilege(r.oid, n.oid, 'USAGE') AS can_use,"
    " pg_catalog.has_schema_privilege(r.oid, n.oid, 'CREATE') AS can_create"
    " FROM pg_catalog.pg_roles AS r CROSS JOIN pg_catalog.pg_namespace AS n"
    " WHERE n.nspname = :schema AND CAST(r.rolname AS text) = ANY(CAST(:names AS text[]))"
)

Q_RELATIONS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(c.relkind AS text) AS kind,
           CAST(pg_catalog.pg_get_userbyid(c.relowner) AS text) AS owner,
           c.relrowsecurity AS rls,
           c.relforcerowsecurity AS forced,
           EXISTS (
               SELECT 1 FROM pg_catalog.pg_depend AS d
               WHERE d.classid = CAST('pg_catalog.pg_class' AS pg_catalog.regclass)
                 AND d.objid = c.oid AND d.deptype = 'e'
           ) AS extension_member,
           COALESCE(c.reloptions, CAST(ARRAY[] AS text[])) AS options,
           (
               SELECT CAST(t.relname AS text)
               FROM pg_catalog.pg_depend AS d
               JOIN pg_catalog.pg_class AS t ON t.oid = d.refobjid
               WHERE c.relkind = 'S'
                 AND d.classid = CAST('pg_catalog.pg_class' AS pg_catalog.regclass)
                 AND d.refclassid = CAST('pg_catalog.pg_class' AS pg_catalog.regclass)
                 AND d.objid = c.oid AND d.deptype IN ('a', 'i')
               ORDER BY 1
               LIMIT 1
           ) AS owned_by
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    ORDER BY 1
    """
)

Q_COLUMNS = text(
    """
    SELECT CAST(c.relname AS text) AS table_name,
           CAST(a.attname AS text) AS name,
           pg_catalog.format_type(a.atttypid, a.atttypmod) AS type,
           a.attnotnull AS not_null,
           pg_catalog.pg_get_expr(d.adbin, d.adrelid) AS default_value,
           CAST(a.attidentity AS text) AS identity,
           CAST(a.attgenerated AS text) AS generated
    FROM pg_catalog.pg_attribute AS a
    JOIN pg_catalog.pg_class AS c ON c.oid = a.attrelid
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    LEFT JOIN pg_catalog.pg_attrdef AS d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
    WHERE n.nspname = :schema AND CAST(c.relname AS text) = ANY(CAST(:names AS text[]))
      AND a.attnum > 0 AND NOT a.attisdropped
    """
)

# contype 'n' (NOT NULL, stored as a constraint since PostgreSQL 18) is compared through the columns.
Q_CONSTRAINTS = text(
    """
    SELECT CAST(c.relname AS text) AS table_name,
           CAST(co.conname AS text) AS name,
           CAST(co.contype AS text) AS kind,
           ARRAY(
               SELECT CAST(a.attname AS text)
               FROM pg_catalog.unnest(co.conkey) WITH ORDINALITY AS k(attnum, ord)
               JOIN pg_catalog.pg_attribute AS a ON a.attrelid = co.conrelid AND a.attnum = k.attnum
               ORDER BY k.ord
           ) AS columns,
           CAST(fn.nspname AS text) AS referred_schema,
           CAST(f.relname AS text) AS referred_table,
           ARRAY(
               SELECT CAST(a.attname AS text)
               FROM pg_catalog.unnest(co.confkey) WITH ORDINALITY AS k(attnum, ord)
               JOIN pg_catalog.pg_attribute AS a ON a.attrelid = co.confrelid AND a.attnum = k.attnum
               ORDER BY k.ord
           ) AS referred_columns,
           CAST(co.confdeltype AS text) AS on_delete,
           CAST(co.confupdtype AS text) AS on_update,
           CAST(co.confmatchtype AS text) AS match_type,
           co.condeferrable AS deferrable,
           co.convalidated AS validated,
           pg_catalog.pg_get_constraintdef(co.oid) AS definition
    FROM pg_catalog.pg_constraint AS co
    JOIN pg_catalog.pg_class AS c ON c.oid = co.conrelid
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    LEFT JOIN pg_catalog.pg_class AS f ON f.oid = co.confrelid
    LEFT JOIN pg_catalog.pg_namespace AS fn ON fn.oid = f.relnamespace
    WHERE n.nspname = :schema AND CAST(c.relname AS text) = ANY(CAST(:names AS text[]))
      AND co.contype <> 'n'
    """
)

# Expression columns (attnum 0) come back as NULL names; INCLUDE columns are listed too.
Q_INDEXES = text(
    """
    SELECT CAST(t.relname AS text) AS table_name,
           CAST(i.relname AS text) AS name,
           EXISTS (
               SELECT 1 FROM pg_catalog.pg_constraint AS co
               WHERE co.conindid = i.oid AND co.conrelid = t.oid AND co.contype IN ('p', 'u', 'x')
           ) AS backs_constraint,
           ARRAY(
               SELECT CAST(a.attname AS text)
               FROM pg_catalog.unnest(CAST(x.indkey AS int2[])) WITH ORDINALITY AS k(attnum, ord)
               LEFT JOIN pg_catalog.pg_attribute AS a ON a.attrelid = x.indrelid AND a.attnum = k.attnum
               ORDER BY k.ord
           ) AS columns,
           x.indisunique AS is_unique,
           x.indisvalid AS is_valid,
           CAST(am.amname AS text) AS method,
           x.indexprs IS NOT NULL AS has_expressions,
           pg_catalog.pg_get_expr(x.indpred, x.indrelid) AS predicate
    FROM pg_catalog.pg_index AS x
    JOIN pg_catalog.pg_class AS i ON i.oid = x.indexrelid
    JOIN pg_catalog.pg_class AS t ON t.oid = x.indrelid
    JOIN pg_catalog.pg_namespace AS n ON n.oid = t.relnamespace
    JOIN pg_catalog.pg_am AS am ON am.oid = i.relam
    WHERE n.nspname = :schema AND CAST(t.relname AS text) = ANY(CAST(:names AS text[]))
    """
)

Q_TRIGGERS = text(
    "SELECT CAST(c.relname AS text) AS table_name, CAST(t.tgname AS text) AS name"
    " FROM pg_catalog.pg_trigger AS t"
    " JOIN pg_catalog.pg_class AS c ON c.oid = t.tgrelid"
    " JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace"
    " WHERE n.nspname = :schema AND NOT t.tgisinternal"
)

# Direct grants to anyone but the owner, on every relation in the schema; a NULL ACL (owner only)
# yields no rows.
Q_GRANTS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CASE WHEN a.grantee = 0 THEN 'PUBLIC'
                ELSE CAST(pg_catalog.pg_get_userbyid(a.grantee) AS text) END AS grantee,
           CAST(a.privilege_type AS text) AS privilege
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(c.relacl) AS a
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
      AND a.grantee <> c.relowner
    """
)

# Effective privileges, including those inherited through role membership and PUBLIC.
Q_TABLE_ACCESS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(r.rolname AS text) AS role_name,
           ARRAY(
               SELECT p FROM pg_catalog.unnest(CAST(:privileges AS text[])) AS p
               WHERE pg_catalog.has_table_privilege(r.oid, c.oid, p)
           ) AS privileges
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p')
      AND CAST(c.relname AS text) = ANY(CAST(:names AS text[]))
      AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)

# Privileges a role holds on at least one column, from a table grant, a column grant, membership
# or PUBLIC; has_table_privilege alone misses column-level grants.
Q_COLUMN_ACCESS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(r.rolname AS text) AS role_name,
           ARRAY(
               SELECT p FROM pg_catalog.unnest(CAST(:privileges AS text[])) AS p
               WHERE pg_catalog.has_any_column_privilege(r.oid, c.oid, p)
           ) AS privileges
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p')
      AND CAST(c.relname AS text) = ANY(CAST(:names AS text[]))
      AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)

# Effective privileges on every relation in the schema, sequences included. column_privileges
# also counts column-level grants, which the relation-level check misses.
Q_OBJECT_ACCESS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(r.rolname AS text) AS role_name,
           CASE WHEN c.relkind = 'S' THEN ARRAY(
                    SELECT p FROM pg_catalog.unnest(CAST(:sequence_privileges AS text[])) AS p
                    WHERE pg_catalog.has_sequence_privilege(r.oid, c.oid, p)
                )
                ELSE ARRAY(
                    SELECT p FROM pg_catalog.unnest(CAST(:privileges AS text[])) AS p
                    WHERE pg_catalog.has_table_privilege(r.oid, c.oid, p)
                ) END AS privileges,
           CASE WHEN c.relkind = 'S' THEN CAST(ARRAY[] AS text[])
                ELSE ARRAY(
                    SELECT p FROM pg_catalog.unnest(CAST(:column_privileges AS text[])) AS p
                    WHERE pg_catalog.has_any_column_privilege(r.oid, c.oid, p)
                ) END AS column_privileges
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
      AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)

# Direct column grants to anyone but the owner, on every relation in the schema.
Q_COLUMN_GRANTS = text(
    """
    SELECT CAST(c.relname AS text) AS name,
           CAST(a.attname AS text) AS column_name,
           CASE WHEN x.grantee = 0 THEN 'PUBLIC'
                ELSE CAST(pg_catalog.pg_get_userbyid(x.grantee) AS text) END AS grantee,
           CAST(x.privilege_type AS text) AS privilege
    FROM pg_catalog.pg_attribute AS a
    JOIN pg_catalog.pg_class AS c ON c.oid = a.attrelid
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(a.attacl) AS x
    WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
      AND a.attnum > 0 AND NOT a.attisdropped AND x.grantee <> c.relowner
    """
)

Q_POLICIES = text(
    "SELECT CAST(tablename AS text) AS name, CAST(policyname AS text) AS policy"
    " FROM pg_catalog.pg_policies WHERE schemaname = :schema"
)

SIGNATURE_SQL = (
    "pg_catalog.quote_ident(CAST(n.nspname AS text)) || '.'"
    " || pg_catalog.quote_ident(CAST(p.proname AS text))"
    " || '(' || pg_catalog.pg_get_function_identity_arguments(p.oid) || ')'"
)

Q_ROUTINES = text(
    f"""
    SELECT CAST(p.proname AS text) AS name,
           {SIGNATURE_SQL} AS signature,
           CAST(pg_catalog.pg_get_userbyid(p.proowner) AS text) AS owner,
           CAST(p.prokind AS text) AS kind,
           p.prosecdef AS security_definer,
           EXISTS (
               SELECT 1
               FROM pg_catalog.aclexplode(
                   COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))
               ) AS a
               WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'
           ) AS public_execute,
           EXISTS (
               SELECT 1 FROM pg_catalog.pg_depend AS d
               WHERE d.classid = CAST('pg_catalog.pg_proc' AS pg_catalog.regclass)
                 AND d.objid = p.oid AND d.deptype = 'e'
           ) AS extension_member
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    WHERE n.nspname = :schema
    ORDER BY 2
    """
)

Q_ROUTINE_ACCESS = text(
    f"""
    SELECT {SIGNATURE_SQL} AS signature,
           CAST(r.rolname AS text) AS role_name,
           pg_catalog.has_function_privilege(r.oid, p.oid, 'EXECUTE') AS can_execute
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    CROSS JOIN pg_catalog.pg_roles AS r
    WHERE n.nspname = :schema AND CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))
    """
)

# Standalone types only: no array types and no row types of tables or views.
Q_TYPES = text(
    """
    SELECT CAST(t.typname AS text) AS name,
           EXISTS (
               SELECT 1 FROM pg_catalog.pg_depend AS d
               WHERE d.classid = CAST('pg_catalog.pg_type' AS pg_catalog.regclass)
                 AND d.objid = t.oid AND d.deptype = 'e'
           ) AS extension_member
    FROM pg_catalog.pg_type AS t
    JOIN pg_catalog.pg_namespace AS n ON n.oid = t.typnamespace
    LEFT JOIN pg_catalog.pg_class AS c ON c.oid = t.typrelid
    WHERE n.nspname = :schema AND t.typcategory <> 'A' AND (t.typrelid = 0 OR c.relkind = 'c')
    """
)

Q_VERSION_TABLES = text(
    "SELECT CAST(n.nspname AS text) AS schema_name,"
    " pg_catalog.has_table_privilege(c.oid, 'SELECT') AS readable"
    " FROM pg_catalog.pg_class AS c"
    " JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace"
    " WHERE c.relname = :name AND c.relkind IN ('r', 'p') ORDER BY 1"
)

Q_DEFAULT_ACL = text(
    """
    SELECT CAST(pg_catalog.pg_get_userbyid(d.defaclrole) AS text) AS owner_role,
           COALESCE(CAST(n.nspname AS text), '') AS schema_name,
           CAST(d.defaclobjtype AS text) AS object_type,
           CASE WHEN a.grantee = 0 THEN 'PUBLIC'
                ELSE CAST(pg_catalog.pg_get_userbyid(a.grantee) AS text) END AS grantee,
           CAST(a.privilege_type AS text) AS privilege
    FROM pg_catalog.pg_default_acl AS d
    LEFT JOIN pg_catalog.pg_namespace AS n ON n.oid = d.defaclnamespace
    CROSS JOIN LATERAL pg_catalog.aclexplode(d.defaclacl) AS a
    WHERE (d.defaclnamespace = 0 OR n.nspname = :schema) AND a.grantee <> d.defaclrole
    """
)

# USAGE: the role has the owner's privileges, which is what ALTER TABLE and the RLS bypass check.
Q_ACTS_AS_OWNER = text(
    "SELECT CAST(r.rolname AS text) AS role_name, CAST(o.rolname AS text) AS owner,"
    " pg_catalog.pg_has_role(r.oid, o.oid, 'USAGE') AS acts_as_owner"
    " FROM pg_catalog.pg_roles AS r CROSS JOIN pg_catalog.pg_roles AS o"
    " WHERE CAST(r.rolname AS text) = ANY(CAST(:roles AS text[]))"
    " AND CAST(o.rolname AS text) = ANY(CAST(:owners AS text[]))"
)

QUERIES = (
    Q_SET_READ_ONLY,
    Q_STATEMENT_TIMEOUT,
    Q_LOCK_TIMEOUT,
    Q_READ_ONLY_STATUS,
    Q_IDENTITY,
    Q_SCHEMAS_PRESENT,
    Q_ROLES_PRESENT,
    Q_ROLES,
    Q_AUTHENTICATOR,
    Q_ROLE_MEMBERSHIPS,
    Q_SCHEMA_ACCESS,
    Q_RELATIONS,
    Q_COLUMNS,
    Q_CONSTRAINTS,
    Q_INDEXES,
    Q_TRIGGERS,
    Q_GRANTS,
    Q_TABLE_ACCESS,
    Q_COLUMN_ACCESS,
    Q_OBJECT_ACCESS,
    Q_COLUMN_GRANTS,
    Q_POLICIES,
    Q_ROUTINES,
    Q_ROUTINE_ACCESS,
    Q_TYPES,
    Q_VERSION_TABLES,
    Q_DEFAULT_ACL,
    Q_ACTS_AS_OWNER,
)


def version_rows_query():
    return text(
        f"SELECT CAST(version_num AS text) FROM {_quote(SCHEMA)}.{_quote(VERSION_TABLE)} ORDER BY 1"
    )


# --- data ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    level: str
    subject: str
    message: str


class PreflightRefused(RuntimeError):
    """The target or the connected database failed a check; nothing past that point was read."""


@dataclass(frozen=True)
class Identity:
    database: str
    role: str
    session_role: str
    server_version: str
    schema: str | None
    supabase_schemas: tuple[str, ...]
    supabase_roles: tuple[str, ...]
    search_path: str = ""


@dataclass(frozen=True)
class Roles:
    connection: str
    app: str
    worker: str

    def all(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.connection, self.app, self.worker)))


@dataclass(frozen=True)
class Revisions:
    ordered: tuple[str, ...]  # base first
    heads: tuple[str, ...]


@dataclass(frozen=True)
class QueueSpec:
    version: str
    tables: frozenset[str]
    functions: frozenset[str]
    types: frozenset[str]
    triggers: frozenset[str]
    indexes: frozenset[str]


@dataclass(frozen=True)
class Expectations:
    roles: Roles
    revisions: Revisions
    queue: QueueSpec
    present_roles: tuple[str, ...] = ()  # browser roles the identity check found


@dataclass(frozen=True)
class RoleInfo:
    superuser: bool
    bypassrls: bool
    can_login: bool


@dataclass(frozen=True)
class Relation:
    kind: str
    owner: str
    rls: bool
    forced: bool
    extension_member: bool = False
    options: tuple[str, ...] = ()  # pg_class.reloptions, e.g. "security_invoker=true"
    owned_by: str | None = None  # for a sequence: the table owning it (serial or identity column)


@dataclass(frozen=True)
class Routine:
    name: str
    signature: str
    owner: str
    security_definer: bool
    public_execute: bool
    extension_member: bool = False
    kind: str = "f"  # pg_proc.prokind: f function, p procedure, a aggregate, w window


@dataclass(frozen=True)
class ColumnInfo:
    type: str
    not_null: bool
    default: str | None = None
    identity: str = ""  # pg_attribute.attidentity; "" for none
    generated: str = ""  # pg_attribute.attgenerated; "" for none


@dataclass(frozen=True)
class ConstraintInfo:
    kind: str  # pg_constraint.contype
    columns: tuple[str, ...] = ()
    referred_schema: str | None = None
    referred_table: str | None = None
    referred_columns: tuple[str, ...] = ()
    on_delete: str = ""
    on_update: str = ""
    match_type: str = ""
    deferrable: bool = False
    validated: bool = True
    definition: str = ""  # pg_get_constraintdef()


@dataclass(frozen=True)
class IndexInfo:
    columns: tuple[str | None, ...]  # None for an expression
    unique: bool = False
    valid: bool = True
    method: str = "btree"
    has_expressions: bool = False
    predicate: str | None = None


@dataclass(frozen=True)
class DefaultGrant:
    owner_role: str
    schema: str  # "" for defaults that apply in every schema
    object_type: str
    grantee: str
    privilege: str


@dataclass
class Snapshot:
    """Everything read from the database. Sections that failed are named in `limited`."""

    roles: dict[str, RoleInfo] = field(default_factory=dict)
    schema_access: dict[str, tuple[bool, bool]] = field(default_factory=dict)  # (USAGE, CREATE)
    relations: dict[str, Relation] = field(default_factory=dict)
    columns: dict[str, dict[str, ColumnInfo]] = field(default_factory=dict)
    constraints: dict[str, dict[str, ConstraintInfo]] = field(default_factory=dict)
    indexes: dict[str, dict[str, IndexInfo]] = field(default_factory=dict)  # not backing a constraint
    triggers: dict[str, set[str]] = field(default_factory=dict)
    grants: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    access: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)
    column_access: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)
    # Every relation in public, sequences included: (name, role) -> privileges.
    object_access: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)
    object_column_access: dict[tuple[str, str], frozenset[str]] = field(default_factory=dict)
    column_grants: dict[str, dict[str, set[tuple[str, str]]]] = field(default_factory=dict)  # (column, privilege)
    policies: dict[str, list[str]] = field(default_factory=dict)
    routines: list[Routine] = field(default_factory=list)
    routine_access: dict[tuple[str, str], bool] = field(default_factory=dict)
    types: dict[str, bool] = field(default_factory=dict)  # name -> extension member
    version_schemas: list[str] = field(default_factory=list)
    version_rows: list[str] | None = None  # None: absent or unreadable
    default_grants: list[DefaultGrant] = field(default_factory=list)
    acts_as_owner: dict[tuple[str, str], bool] = field(default_factory=dict)
    authenticator: RoleInfo | None = None  # None: the role doesn't exist (or see `limited`)
    api_roles: tuple[str, ...] = ()  # roles authenticator can SET ROLE to, itself excluded
    limited: dict[str, str] = field(default_factory=dict)


# --- repository expectations ---------------------------------------------------------------


def load_revisions() -> Revisions:
    script = ScriptDirectory.from_config(Config(str(SERVER_DIR / "alembic.ini")))
    ordered = tuple(reversed([revision.revision for revision in script.walk_revisions()]))
    return Revisions(ordered, tuple(script.get_heads()))


def load_queue_spec() -> QueueSpec:
    spec = importlib.util.find_spec("procrastinate")
    if spec is None or spec.origin is None:
        raise RuntimeError("procrastinate is not installed in this environment")
    sql = (Path(spec.origin).parent / "sql" / "schema.sql").read_text(encoding="utf-8")
    found: dict[str, set[str]] = {kind: set() for kind in ("TABLE", "FUNCTION", "TYPE", "TRIGGER", "INDEX")}
    for kind, name in QUEUE_OBJECT.findall(sql):
        found[kind].add(name)
    return QueueSpec(
        package_version("procrastinate"),
        frozenset(found["TABLE"]),
        frozenset(found["FUNCTION"]),
        frozenset(found["TYPE"]),
        frozenset(found["TRIGGER"]),
        frozenset(found["INDEX"]),
    )


# --- target -------------------------------------------------------------------------------


def _interactive() -> bool:
    return sys.stdin is not None and sys.stdin.isatty()


def _secret_input(prompt: str) -> str:
    return getpass.getpass(prompt)


def _ask(prompt: str) -> str:
    return input(prompt)


def read_secret(environ: Mapping[str, str], name: str, prompt: str) -> tuple[str, str]:
    """The value of `name`, else a hidden prompt; returns (value, where it came from)."""
    raw = (environ.get(name) or "").strip()
    if raw:
        return raw, name
    if _interactive():
        raw = _secret_input(prompt).strip()
        if raw:
            return raw, "hidden prompt"
    raise PreflightRefused(
        f"{name} is not set and nothing was entered; there is no fallback to any other setting"
    )


def target_url(raw: str) -> URL:
    url = safety.parse_url(raw, URL_ENV)
    if url.get_backend_name() != "postgresql":
        raise PreflightRefused("the target must be a PostgreSQL URL")
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def project_refs(url: URL) -> set[str]:
    """Project references in the URL: the pooler user `role.<ref>` and `[db.]<ref>.supabase.co` hosts."""
    refs = set()
    user = url.username or ""
    if "." in user:
        refs.add(user.split(".", 1)[1].lower())
    for host in safety.target_hosts(url):
        match = PROJECT_HOST.match(host.lower())
        if match:
            refs.add(match.group(1))
    return refs


def redacted_target(url: URL) -> str:
    """Backend, host, port and database, with any project reference masked; never the user name."""
    description = safety.describe(url)
    for ref in project_refs(url):
        description = re.sub(re.escape(ref), "<project-ref>", description, flags=re.IGNORECASE)
    return description


def check_connection_overrides(url: URL, environ: Mapping[str, str]) -> None:
    """Refuse libpq settings from outside the URL that could redirect the connection or alter the
    session. Names are reported, values never are."""
    present = sorted(name for name in UNSAFE_LIBPQ_VARIABLES if name in environ)
    if present:
        reasons = "; ".join(f"{name} {UNSAFE_LIBPQ_VARIABLES[name]}" for name in present)
        raise PreflightRefused(
            f"unset {', '.join(present)} in this shell first ({reasons}); values are not printed"
        )
    for key in ("service", "options"):
        if key in url.query:
            raise PreflightRefused(
                f"the URL sets the libpq '{key}' parameter, which can change where or how the "
                "checks run; remove it"
            )


def check_root_cert(sslmode: str, root_cert: object) -> None:
    """sslrootcert must be `system` or a readable file holding a PEM certificate; its path and
    contents are never printed."""
    if not isinstance(root_cert, str) or not root_cert.strip():
        raise PreflightRefused(
            f"sslmode={sslmode} needs sslrootcert: the path to the Supabase CA certificate "
            "(download it from the project's database settings)"
        )
    if root_cert == SYSTEM_ROOT_CERTS:
        return
    path = Path(root_cert)
    if not path.is_file():
        raise PreflightRefused("the sslrootcert file does not exist (the path is not printed)")
    try:
        with path.open("rb") as file:
            content = file.read(MAX_ROOT_CERT_BYTES)
    except OSError:
        raise PreflightRefused("the sslrootcert file can't be read (the path is not printed)") from None
    if PEM_CERTIFICATE not in content:
        raise PreflightRefused(
            "the sslrootcert file holds no PEM certificate (no '-----BEGIN CERTIFICATE-----' line); "
            "use the CA certificate downloaded from the Supabase dashboard (the path is not printed)"
        )


def check_tls(url: URL, allow_unverified_tls: bool) -> Finding:
    """verify-full passes; require and verify-ca only with --allow-unverified-tls, as a WARN."""
    sslmode = url.query.get("sslmode")
    if sslmode == UNVERIFIED_SSLMODE:
        if not allow_unverified_tls:
            raise PreflightRefused(
                "sslmode=require encrypts but never checks the server certificate, so it can't "
                "detect an impostor; use sslmode=verify-full with sslrootcert set to the Supabase "
                "CA certificate (or pass --allow-unverified-tls to accept the risk)"
            )
        return Finding(
            WARN,
            "TLS",
            "sslmode=require: encrypted, but the server certificate is not verified "
            "(--allow-unverified-tls); prefer verify-full",
        )
    if sslmode not in (VERIFIED_SSLMODE, CHAIN_ONLY_SSLMODE):
        raise PreflightRefused(
            "the URL must set sslmode=verify-full and sslrootcert (the Supabase CA certificate); "
            "the password is never sent without verified TLS"
        )
    if sslmode == CHAIN_ONLY_SSLMODE and not allow_unverified_tls:
        raise PreflightRefused(
            "sslmode=verify-ca checks the certificate chain but not that it was issued for this "
            "host name; use sslmode=verify-full (or pass --allow-unverified-tls to accept the risk)"
        )
    check_root_cert(sslmode, url.query.get("sslrootcert"))
    if sslmode == CHAIN_ONLY_SSLMODE:
        return Finding(
            WARN,
            "TLS",
            "sslmode=verify-ca: the certificate chain is verified, but not that it was issued for "
            "this host name (--allow-unverified-tls); prefer verify-full",
        )
    return Finding(PASS, "TLS", "sslmode=verify-full: certificate chain and host name verified")


def check_supabase_target(url: URL, expected_ref: str, allow_unverified_tls: bool = False) -> list[Finding]:
    if "service" in url.query:
        raise PreflightRefused("the URL names a libpq service; give the Supabase host explicitly")
    hosts = safety.target_hosts(url)
    if not hosts or not all(host.lower().endswith(SUPABASE_HOST_SUFFIXES) for host in hosts):
        raise PreflightRefused(
            f"{HOST_NOT_ACCEPTED} (use --local-test only for the local *_test database)"
        )
    tls = check_tls(url, allow_unverified_tls)
    refs = project_refs(url)
    if not refs:
        raise PreflightRefused("the URL contains no Supabase project reference to confirm")
    if refs != {expected_ref.strip().lower()}:
        raise PreflightRefused(
            f"the URL's project reference does not match {PROJECT_REF_ENV} (neither value is printed)"
        )
    findings = [Finding(PASS, "target", "Supabase host; project reference matches the expected one"), tls]
    if url.port == TRANSACTION_POOLER_PORT:
        findings.append(
            Finding(
                WARN,
                "target",
                "port 6543 is the transaction pooler; migrations use SERVER_DIRECT_URL "
                "(port 5432), so run the preflight with that URL",
            )
        )
    return findings


def check_local_test_target(url: URL) -> list[Finding]:
    if not safety.is_local(url):
        raise PreflightRefused(
            "--local-test accepts only localhost, 127.0.0.1 or ::1; host details are omitted"
        )
    if not (url.database or "").endswith(safety.DISPOSABLE_DATABASE_SUFFIX):
        raise PreflightRefused(
            f"--local-test accepts only a database whose name ends with "
            f"'{safety.DISPOSABLE_DATABASE_SUFFIX}'"
        )
    return [Finding(INFO, "target", "local test database (--local-test): Supabase checks skipped")]


# --- connection identity -------------------------------------------------------------------


def begin_read_only(connection: Connection) -> None:
    """Make the transaction READ ONLY and prove it before anything else is read."""
    connection.execute(Q_SET_READ_ONLY)
    connection.execute(Q_STATEMENT_TIMEOUT)
    connection.execute(Q_LOCK_TIMEOUT)
    if connection.execute(Q_READ_ONLY_STATUS).scalar_one() != "on":
        raise PreflightRefused("the transaction is not read-only; stopping before any inspection")


def read_identity(connection: Connection) -> Identity:
    row = connection.execute(Q_IDENTITY).mappings().one()
    schemas = connection.execute(Q_SCHEMAS_PRESENT, {"names": list(SUPABASE_SCHEMAS)}).scalars()
    roles = connection.execute(Q_ROLES_PRESENT, {"names": list(BROWSER_ROLES)}).scalars()
    return Identity(
        row["database_name"],
        row["role_name"],
        row["session_role"],
        row["server_version"],
        row["schema_name"],
        tuple(schemas),
        tuple(roles),
        row["search_path"],
    )


def search_path_schemas(search_path: str) -> list[str]:
    return [item.strip().strip('"') for item in search_path.split(",") if item.strip()]


def identity_problems(identity: Identity, expected_database: str, supabase: bool) -> list[str]:
    problems = []
    if identity.database != expected_database:
        problems.append(
            f"connected to database {identity.database!r}, expected {expected_database!r}"
        )
    schemas = search_path_schemas(identity.search_path)
    if "pg_catalog" in schemas and schemas.index("pg_catalog") > 0:
        problems.append(
            "search_path lists pg_catalog after another schema, so objects there could replace the "
            "built-in operators and types the checks use"
        )
    if supabase:
        missing = [name for name in SUPABASE_SCHEMAS if name not in identity.supabase_schemas]
        missing += [name for name in BROWSER_ROLES if name not in identity.supabase_roles]
        if missing:
            problems.append(
                f"this does not look like a Supabase database: no {', '.join(missing)}"
            )
    return problems


def print_identity(identity: Identity) -> None:
    print("Connected, in a read-only transaction:")
    print(f"  database:         {identity.database}")
    print(f"  role:             {identity.role} (session role {identity.session_role})")
    print(f"  server version:   {identity.server_version}")
    print(f"  current schema:   {identity.schema or '<none>'}")
    print(f"  search_path:      {identity.search_path or '<empty>'}")
    print(f"  Supabase schemas: {', '.join(identity.supabase_schemas) or 'none'}")
    print(f"  Supabase roles:   {', '.join(identity.supabase_roles) or 'none'}")


def confirmed(assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not _interactive():
        raise PreflightRefused(
            "no terminal to confirm the identity above; review it and rerun with --yes"
        )
    return _ask("Is this the intended database? Type 'yes' to continue: ").strip().lower() == "yes"


def identity_findings(identity: Identity, target_findings: list[Finding]) -> list[Finding]:
    findings = [
        *target_findings,
        Finding(PASS, "transaction", "READ ONLY confirmed (transaction_read_only = on)"),
        Finding(INFO, "database", f"{identity.database}, PostgreSQL {identity.server_version}"),
        Finding(INFO, "role", f"{identity.role} (session role {identity.session_role})"),
    ]
    if identity.schema == SCHEMA:
        findings.append(Finding(PASS, "current schema", SCHEMA))
    else:
        findings.append(
            Finding(
                FAIL,
                "current schema",
                f"{identity.schema or '<none>'}: Alembic creates the tables in the current schema, "
                "but the security migration and the queue script expect public",
            )
        )
    return findings


# --- inspection (read-only) -----------------------------------------------------------------


def _section(connection: Connection, snapshot: Snapshot, name: str, read: Callable[[], None]) -> None:
    """Run one group of catalog reads in a savepoint; a failure is recorded, not guessed around.

    A lost connection ends the inspection: the next read would run outside this transaction."""
    try:
        with connection.begin_nested():
            read()
    except DBAPIError as error:
        if error.connection_invalidated:
            raise
        snapshot.limited[name] = safe_error_summary(error)


def assumable_roles(memberships: Iterable[tuple[str, str, bool]], start: str) -> tuple[str, ...]:
    """Roles `start` can SET ROLE to: (member, granted role, SET option) grants followed
    transitively, each grant in the chain needing the SET option. `start` itself is excluded."""
    granted: dict[str, list[str]] = {}
    for member, role, can_set in memberships:
        if can_set:
            granted.setdefault(member, []).append(role)
    reached: set[str] = set()
    pending = [start]
    while pending:
        for role in granted.get(pending.pop(), ()):
            if role not in reached and role != start:
                reached.add(role)
                pending.append(role)
    return tuple(sorted(reached))


def inspect_database(connection: Connection, roles: Roles) -> Snapshot:
    """Read the catalog (and the Alembic version) inside the caller's transaction. No writes."""
    s = Snapshot()
    schema = {"schema": SCHEMA}
    detail_tables = sorted({*APP_TABLES, *QUEUE_TABLES})
    secured_tables = sorted({*APP_TABLES, VERSION_TABLE, *QUEUE_TABLES})

    def read_api_roles():
        rows = connection.execute(Q_AUTHENTICATOR, {"name": AUTHENTICATOR}).mappings().all()
        if not rows:
            return
        memberships = [
            (row["member"], row["granted"], row["can_set"])
            for row in connection.execute(Q_ROLE_MEMBERSHIPS).mappings()
        ]
        s.api_roles = assumable_roles(memberships, AUTHENTICATOR)
        s.authenticator = RoleInfo(rows[0]["rolsuper"], rows[0]["rolbypassrls"], rows[0]["rolcanlogin"])

    # The privilege reads below cover every role the Data API can assume, so this runs first.
    _section(connection, s, "data api roles", read_api_roles)
    role_names = sorted({*BROWSER_ROLES, *roles.all(), *s.api_roles})

    def read_roles():
        for row in connection.execute(Q_ROLES, {"names": role_names}).mappings():
            s.roles[row["name"]] = RoleInfo(row["rolsuper"], row["rolbypassrls"], row["rolcanlogin"])
        for row in connection.execute(Q_SCHEMA_ACCESS, {**schema, "names": role_names}).mappings():
            s.schema_access[row["role_name"]] = (row["can_use"], row["can_create"])

    def read_relations():
        for row in connection.execute(Q_RELATIONS, schema).mappings():
            s.relations[row["name"]] = Relation(
                row["kind"],
                row["owner"],
                row["rls"],
                row["forced"],
                row["extension_member"],
                tuple(row["options"] or ()),
                row["owned_by"],
            )

    def read_table_details():
        params = {**schema, "names": detail_tables}
        for row in connection.execute(Q_COLUMNS, params).mappings():
            s.columns.setdefault(row["table_name"], {})[row["name"]] = ColumnInfo(
                row["type"],
                row["not_null"],
                row["default_value"],
                (row["identity"] or "").strip(),
                (row["generated"] or "").strip(),
            )
        for row in connection.execute(Q_CONSTRAINTS, params).mappings():
            s.constraints.setdefault(row["table_name"], {})[row["name"]] = ConstraintInfo(
                row["kind"],
                tuple(row["columns"] or ()),
                row["referred_schema"],
                row["referred_table"],
                tuple(row["referred_columns"] or ()),
                (row["on_delete"] or "").strip(),
                (row["on_update"] or "").strip(),
                (row["match_type"] or "").strip(),
                row["deferrable"],
                row["validated"],
                row["definition"] or "",
            )
        for row in connection.execute(Q_INDEXES, params).mappings():
            if not row["backs_constraint"]:
                s.indexes.setdefault(row["table_name"], {})[row["name"]] = IndexInfo(
                    tuple(row["columns"] or ()),
                    row["is_unique"],
                    row["is_valid"],
                    row["method"],
                    row["has_expressions"],
                    row["predicate"],
                )
        for row in connection.execute(Q_TRIGGERS, schema).mappings():
            s.triggers.setdefault(row["table_name"], set()).add(row["name"])

    def read_privileges():
        params = {**schema, "names": secured_tables}
        for row in connection.execute(Q_GRANTS, schema).mappings():
            s.grants.setdefault(row["name"], {}).setdefault(row["grantee"], set()).add(row["privilege"])
        access_params = {**params, "roles": role_names, "privileges": list(TABLE_PRIVILEGES)}
        for row in connection.execute(Q_TABLE_ACCESS, access_params).mappings():
            s.access[(row["name"], row["role_name"])] = frozenset(row["privileges"])
        column_params = {**params, "roles": role_names, "privileges": list(COLUMN_PRIVILEGES)}
        for row in connection.execute(Q_COLUMN_ACCESS, column_params).mappings():
            s.column_access[(row["name"], row["role_name"])] = frozenset(row["privileges"])
        object_params = {
            **schema,
            "roles": role_names,
            "privileges": list(TABLE_PRIVILEGES),
            "sequence_privileges": list(SEQUENCE_PRIVILEGES),
            "column_privileges": list(COLUMN_PRIVILEGES),
        }
        for row in connection.execute(Q_OBJECT_ACCESS, object_params).mappings():
            key = (row["name"], row["role_name"])
            s.object_access[key] = frozenset(row["privileges"])
            s.object_column_access[key] = frozenset(row["column_privileges"])
        for row in connection.execute(Q_COLUMN_GRANTS, schema).mappings():
            s.column_grants.setdefault(row["name"], {}).setdefault(row["grantee"], set()).add(
                (row["column_name"], row["privilege"])
            )
        for row in connection.execute(Q_POLICIES, schema).mappings():
            s.policies.setdefault(row["name"], []).append(row["policy"])

    def read_routines_and_types():
        for row in connection.execute(Q_ROUTINES, schema).mappings():
            s.routines.append(
                Routine(
                    row["name"],
                    row["signature"],
                    row["owner"],
                    row["security_definer"],
                    row["public_execute"],
                    row["extension_member"],
                    row["kind"],
                )
            )
        params = {**schema, "roles": role_names}
        for row in connection.execute(Q_ROUTINE_ACCESS, params).mappings():
            s.routine_access[(row["signature"], row["role_name"])] = row["can_execute"]
        for row in connection.execute(Q_TYPES, schema).mappings():
            s.types[row["name"]] = row["extension_member"]

    def read_alembic_history():
        rows = connection.execute(Q_VERSION_TABLES, {"name": VERSION_TABLE}).mappings().all()
        s.version_schemas = [row["schema_name"] for row in rows]
        public = next((row for row in rows if row["schema_name"] == SCHEMA), None)
        if public is not None and public["readable"]:
            s.version_rows = list(connection.execute(version_rows_query()).scalars())

    def read_default_privileges():
        for row in connection.execute(Q_DEFAULT_ACL, schema).mappings():
            s.default_grants.append(
                DefaultGrant(
                    row["owner_role"], row["schema_name"], row["object_type"], row["grantee"], row["privilege"]
                )
            )

    def read_ownership():
        owners = {relation.owner for name, relation in s.relations.items() if name in secured_tables}
        owners |= {routine.owner for routine in s.routines if routine.name.startswith(QUEUE_PREFIX)}
        owners.add(roles.connection)
        params = {"roles": list(roles.all()), "owners": sorted(owners)}
        for row in connection.execute(Q_ACTS_AS_OWNER, params).mappings():
            s.acts_as_owner[(row["role_name"], row["owner"])] = row["acts_as_owner"]

    for name, read in (
        ("roles", read_roles),
        ("relations", read_relations),
        ("table details", read_table_details),
        ("privileges", read_privileges),
        ("routines and types", read_routines_and_types),
        ("alembic history", read_alembic_history),
        ("default privileges", read_default_privileges),
        ("ownership", read_ownership),
    ):
        _section(connection, s, name, read)
    return s


# --- evaluation (pure) ----------------------------------------------------------------------


def _skipped(s: Snapshot, *sections: str) -> list[Finding]:
    missing = [name for name in sections if name in s.limited]
    if not missing:
        return []
    return [Finding(LIMITED, ", ".join(missing), "not checked: the catalog query failed (see below)")]


def role_gaps(s: Snapshot, expect: Expectations) -> list[str]:
    """Roles known to exist (the connected role, browser roles seen at connect, roles authenticator
    can assume) that the role read missed."""
    known = {expect.roles.connection, *expect.present_roles, *s.api_roles}
    return sorted(role for role in known if role not in s.roles)


def data_api_roles(s: Snapshot) -> tuple[str, ...]:
    """The browser roles plus every other role authenticator can switch to."""
    return tuple(dict.fromkeys((*BROWSER_ROLES, *s.api_roles)))


def _roles_unknown(s: Snapshot, expect: Expectations, *sections: str) -> list[Finding]:
    """LIMITED when the roles section, or any of `sections`, failed or returned incomplete results."""
    skipped = _skipped(s, "roles", *sections)
    if skipped:
        return skipped
    gaps = role_gaps(s, expect)
    if gaps:
        return [
            Finding(
                LIMITED,
                "roles",
                f"not checked: the role query returned nothing for {', '.join(gaps)}, which exist",
            )
        ]
    return []


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def acts_as_owner(s: Snapshot, role: str, owner: str) -> bool:
    return role == owner or s.acts_as_owner.get((role, owner), False)


def ignores_rls(s: Snapshot, role: str) -> bool:
    info = s.roles.get(role)
    return bool(info and (info.superuser or info.bypassrls))


def current_revision(s: Snapshot) -> str | None:
    rows = s.version_rows or []
    return rows[0] if len(rows) == 1 else None


def security_applied(s: Snapshot, revisions: Revisions) -> bool:
    current = current_revision(s)
    if current not in revisions.ordered or SECURITY_REVISION not in revisions.ordered:
        return False
    return revisions.ordered.index(current) >= revisions.ordered.index(SECURITY_REVISION)


def present_tables(s: Snapshot, names) -> list[str]:
    return [name for name in names if name in s.relations and s.relations[name].kind in TABLE_KINDS]


def _column_privileges(s: Snapshot, table: str, grantee: str) -> dict[str, list[str]]:
    """Direct column grants to `grantee`: privilege -> columns."""
    granted: dict[str, list[str]] = {}
    for column, privilege in sorted(s.column_grants.get(table, {}).get(grantee, ())):
        granted.setdefault(privilege, []).append(column)
    return granted


def _on_columns(privilege: str, columns: list[str] | None) -> str:
    return f"{privilege} on columns {', '.join(columns)}" if columns else f"{privilege} on some columns"


def _exposure(
    s: Snapshot,
    name: str,
    access: Mapping[tuple[str, str], frozenset[str]],
    column_access: Mapping[tuple[str, str], frozenset[str]],
) -> tuple[list[str], list[str], list[str]]:
    public_relation = s.grants.get(name, {}).get("PUBLIC", set())
    public = sorted(public_relation)
    for privilege, columns in _column_privileges(s, name, "PUBLIC").items():
        if privilege not in public_relation:
            public.append(_on_columns(privilege, columns))
    open_to, unknown = [], []
    for role in data_api_roles(s):
        if role not in s.roles:
            continue
        held = access.get((name, role))
        on_any_column = column_access.get((name, role))
        if held is None or on_any_column is None:
            unknown.append(role)
            continue
        granted = _column_privileges(s, name, role)
        parts = sorted(held) + [
            _on_columns(privilege, granted.get(privilege)) for privilege in sorted(on_any_column - held)
        ]
        if parts:
            open_to.append(f"{role}: {', '.join(parts)}")
    return public, open_to, unknown


def browser_access(s: Snapshot, table: str) -> tuple[list[str], list[str], list[str]]:
    """(PUBLIC privileges, Data API role access, Data API roles without a permission record).

    Table and column privileges both count: SELECT on one column is enough to read it."""
    return _exposure(s, table, s.access, s.column_access)


def object_exposure(s: Snapshot, name: str) -> tuple[list[str], list[str], list[str]]:
    """browser_access for any relation in public: views, materialized views, foreign tables and
    sequences included."""
    return _exposure(s, name, s.object_access, s.object_column_access)


def _exposed(public: list[str], open_to: list[str]) -> list[str]:
    return ([f"PUBLIC: {', '.join(public)}"] if public else []) + open_to


def routine_exposure(s: Snapshot, routine: Routine) -> tuple[list[str], list[str]]:
    """(PUBLIC and Data API roles that can EXECUTE it, Data API roles without a record)."""
    callers = ["PUBLIC"] if routine.public_execute else []
    unknown = []
    for role in data_api_roles(s):
        if role not in s.roles:
            continue
        allowed = s.routine_access.get((routine.signature, role))
        if allowed is None:
            unknown.append(role)
        elif allowed:
            callers.append(role)
    return callers, unknown


def security_invoker(relation: Relation) -> bool:
    for option in relation.options:
        key, _, value = option.partition("=")
        if key.strip().lower() == "security_invoker" and value.strip().lower() in TRUE_OPTION_VALUES:
            return True
    return False


def queue_secured(s: Snapshot) -> bool:
    """scripts.secure_queue_schema has run: every queue table exists and has RLS on."""
    tables = present_tables(s, QUEUE_TABLES)
    return len(tables) == len(QUEUE_TABLES) and all(s.relations[name].rls for name in tables)


def queue_sequences(s: Snapshot) -> list[str]:
    return sorted(
        name
        for name, relation in s.relations.items()
        if relation.kind == "S"
        and (name.startswith(QUEUE_PREFIX) or (relation.owned_by or "").startswith(QUEUE_PREFIX))
    )


def routine_kind(routine: Routine) -> str:
    return {"p": "procedure", "a": "aggregate", "w": "window function"}.get(routine.kind, "function")


def evaluate_roles(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _roles_unknown(s, expect, "ownership")
    if skipped:
        return skipped
    roles = expect.roles
    labels: dict[str, list[str]] = {}
    for role, label in (
        (roles.connection, "connection (runs the migrations)"),
        (roles.app, "Core API"),
        (roles.worker, "worker"),
    ):
        labels.setdefault(role, []).append(label)

    out = []
    for role, label_list in labels.items():
        label = " and ".join(label_list)
        info = s.roles.get(role)
        if info is None:
            out.append(Finding(FAIL, role, f"{label} role does not exist"))
            continue
        out.append(
            Finding(
                INFO,
                role,
                f"{label} role: superuser {_yes(info.superuser)}, BYPASSRLS {_yes(info.bypassrls)}, "
                f"can log in {_yes(info.can_login)}",
            )
        )
        if role in BROWSER_ROLES:
            out.append(
                Finding(FAIL, role, "is a Supabase browser role; connect as the role that owns the tables")
            )
        can_use, can_create = s.schema_access.get(role, (False, False))
        if role == roles.connection:
            if can_use and can_create:
                out.append(Finding(PASS, role, "USAGE and CREATE on schema public (needed to create tables)"))
            else:
                out.append(Finding(FAIL, role, "lacks USAGE or CREATE on schema public; migrations can't create tables"))
        elif not can_use:
            out.append(Finding(FAIL, role, "no USAGE on schema public"))

    for role in BROWSER_ROLES:
        info = s.roles.get(role)
        if info is None:
            out.append(Finding(INFO, role, "does not exist"))
        elif role == "service_role":
            note = (
                "; it ignores RLS, so only the revokes keep it out of the tables"
                if info.bypassrls or info.superuser
                else ""
            )
            out.append(
                Finding(INFO, role, f"exists: BYPASSRLS {_yes(info.bypassrls)}, superuser {_yes(info.superuser)}{note}")
            )
        elif info.bypassrls or info.superuser:
            out.append(Finding(FAIL, role, "can bypass RLS (BYPASSRLS or superuser)"))
        else:
            out.append(Finding(PASS, role, "exists without BYPASSRLS or superuser"))

    out += _role_table_access(
        s, roles.app, "Core API", present_tables(s, APP_TABLES), APP_PRIVILEGES, roles.connection
    )
    queue_tables = present_tables(s, QUEUE_TABLES)
    out += _role_table_access(s, roles.worker, "worker", queue_tables, TABLE_PRIVILEGES, roles.connection)
    if queue_tables and roles.worker in s.roles and "routines and types" not in s.limited:
        denied = sorted(
            routine.signature
            for routine in s.routines
            if routine.name.startswith(QUEUE_PREFIX)
            and not s.routine_access.get((routine.signature, roles.worker), False)
        )
        if denied:
            out.append(Finding(FAIL, roles.worker, f"worker role can't execute {', '.join(denied)}"))
    return out


def evaluate_data_api_roles(s: Snapshot, expect: Expectations) -> list[Finding]:
    """Which roles the Data API can switch to; the access checks cover every one of them."""
    if "data api roles" in s.limited:
        return [
            Finding(
                LIMITED,
                AUTHENTICATOR,
                "its role memberships could not be read, so the access checks may miss roles the "
                "Data API can switch to (see below)",
            )
        ]
    if s.authenticator is None:
        if not expect.present_roles:
            return [
                Finding(
                    INFO,
                    AUTHENTICATOR,
                    "does not exist and neither do the browser roles: not a Supabase database, "
                    "so there are no Data API roles to check",
                )
            ]
        return [
            Finding(
                LIMITED,
                AUTHENTICATOR,
                "does not exist, so which roles the Data API logs in as and can switch to is unknown; "
                f"only {', '.join(BROWSER_ROLES)} were checked",
            )
        ]
    skipped = _roles_unknown(s, expect)
    if skipped:
        return skipped

    labels: dict[str, list[str]] = {}
    for role, label in (
        (expect.roles.connection, "migrations"),
        (expect.roles.app, "the Core API"),
        (expect.roles.worker, "the worker"),
    ):
        labels.setdefault(role, []).append(label)
    out = [Finding(INFO, AUTHENTICATOR, f"can switch to {', '.join(s.api_roles) or 'no other role'}")]
    if s.authenticator.superuser:
        out.append(
            Finding(FAIL, AUTHENTICATOR, "is a superuser: the Data API could switch to any role, the table owners included")
        )
    extra = [role for role in s.api_roles if role not in BROWSER_ROLES]
    for role in extra:
        info = s.roles[role]
        if role in labels:
            out.append(
                Finding(
                    FAIL,
                    role,
                    f"the Data API can switch to the role used for {' and '.join(labels[role])}, "
                    "so requests would get its privileges",
                )
            )
        if info.superuser:
            out.append(Finding(FAIL, role, "superuser reachable through the Data API"))
        elif info.bypassrls:
            out.append(
                Finding(WARN, role, "reachable through the Data API with BYPASSRLS: only the revokes keep it out")
            )
    if extra:
        out.append(
            Finding(
                INFO,
                AUTHENTICATOR,
                f"{', '.join(extra)}: checked like the browser roles in every access check below",
            )
        )
    elif not s.authenticator.superuser:
        out.append(Finding(PASS, AUTHENTICATOR, f"can switch to no role besides {', '.join(BROWSER_ROLES)}"))
    return out


def _role_table_access(
    s: Snapshot, role: str, label: str, tables: list[str], needed: Sequence[str], creator: str
) -> list[Finding]:
    if role not in s.roles or _skipped(s, "relations", "privileges"):
        return []
    if not tables:
        if acts_as_owner(s, role, creator):
            return [Finding(PASS, role, f"{label} role will own (or act as owner of) tables {creator} creates")]
        rows = "" if ignores_rls(s, role) else ", and under RLS without policies it would see no rows"
        return [
            Finding(
                WARN,
                role,
                f"{label} role is not {creator}: tables {creator} creates would need grants{rows}",
            )
        ]
    problems = []
    for table in tables:
        if acts_as_owner(s, role, s.relations[table].owner):
            continue
        held = s.access.get((table, role))
        if held is None:
            problems.append(f"{table}: no permission record")
            continue
        missing = [privilege for privilege in needed if privilege not in held]
        if missing:
            problems.append(f"{table}: missing {', '.join(missing)}")
        if not ignores_rls(s, role):
            problems.append(f"{table}: not the owner and no BYPASSRLS, so RLS without policies hides every row")
    if problems:
        return [Finding(FAIL, role, f"{label} role: {problem}") for problem in problems]
    return [Finding(PASS, role, f"{label} role can use all {len(tables)} existing tables")]


_SQL_LITERAL = re.compile(r"'((?:[^']|'')*)'")
# Constraint types that can reject rows the Core API writes.
REJECTING_CONSTRAINTS = frozenset({"c", "f", "u", "x"})


def check_values(definition: str, column: str) -> frozenset[str] | None:
    """The values `CHECK (column IN (...))` allows, from pg_get_constraintdef() of a varchar column.

    Returns None for any other form: such a check can't be compared and must not pass."""
    values = [value.replace("''", "'") for value in _SQL_LITERAL.findall(definition)]
    if not values:
        return None
    array = ", ".join("''::character varying" for _ in values)
    expected = f"CHECK ((({_quote(column)})::text = ANY ((ARRAY[{array}])::text[])))"
    if _SQL_LITERAL.sub("''", definition) != expected:
        return None
    return frozenset(values)


def _names(columns: Sequence[str | None]) -> str:
    return "(" + ", ".join(column or "<expression>" for column in columns) + ")"


def _compare_columns(spec: TableSpec, columns: Mapping[str, ColumnInfo]) -> list[tuple[str, str]]:
    problems = []
    for name, (expected_type, not_null) in spec.columns.items():
        column = columns.get(name)
        if column is None:
            problems.append((FAIL, f"missing column {name}"))
            continue
        if column.type != expected_type:
            problems.append((FAIL, f"column {name} is {column.type}, expected {expected_type}"))
        if column.not_null != not_null:
            expected = "NOT NULL" if not_null else "nullable"
            problems.append((FAIL, f"column {name} should be {expected}"))
        if column.default is not None:
            problems.append((FAIL, f"column {name} has DEFAULT {column.default}; the models define none"))
        if column.identity:
            problems.append((FAIL, f"column {name} is an identity column; the models define none"))
        if column.generated:
            problems.append((FAIL, f"column {name} is a generated column; the models define none"))
    for name in sorted(set(columns) - set(spec.columns)):
        column = columns[name]
        if column.not_null and column.default is None and not (column.identity or column.generated):
            problems.append(
                (FAIL, f"column {name} is not in the models and is NOT NULL without a default; inserts would fail")
            )
        else:
            problems.append((WARN, f"column {name} is not in the models"))
    return problems


def _compare_foreign_key(name: str, expected: ForeignKey, actual: ConstraintInfo) -> list[tuple[str, str]]:
    problems = []
    target = (actual.columns, actual.referred_schema, actual.referred_table, actual.referred_columns)
    if target != (expected.columns, SCHEMA, expected.table, expected.referred):
        found = f"{actual.referred_schema}.{actual.referred_table}{_names(actual.referred_columns)}"
        wanted = f"{SCHEMA}.{expected.table}{_names(expected.referred)}"
        message = f"is {_names(actual.columns)} -> {found}, expected {_names(expected.columns)} -> {wanted}"
        problems.append((FAIL, f"foreign key {name} {message}"))
    for clause, actual_action, expected_action in (
        ("ON DELETE", actual.on_delete, expected.on_delete),
        ("ON UPDATE", actual.on_update, expected.on_update),
    ):
        if actual_action != expected_action:
            found = FK_ACTIONS.get(actual_action, actual_action or "?")
            problems.append(
                (FAIL, f"foreign key {name} has {clause} {found}, expected {FK_ACTIONS[expected_action]}")
            )
    if actual.match_type != FK_MATCH_SIMPLE:
        problems.append((FAIL, f"foreign key {name} is not MATCH SIMPLE"))
    return problems


def _compare_constraints(
    table: str, spec: TableSpec, constraints: Mapping[str, ConstraintInfo]
) -> list[tuple[str, str]]:
    problems = []
    expected_kinds = spec.constraint_kinds(table)
    for name, kind in expected_kinds.items():
        actual = constraints.get(name)
        if actual is None:
            problems.append((FAIL, f"missing constraint {name}"))
            continue
        if actual.kind != kind:
            problems.append((FAIL, f"constraint {name} has type {actual.kind}, expected {kind}"))
            continue
        if actual.deferrable:
            problems.append((FAIL, f"constraint {name} is DEFERRABLE; the models define it as immediate"))
        if not actual.validated:
            problems.append((FAIL, f"constraint {name} is NOT VALID: existing rows were never checked"))
        if kind in ("p", "u"):
            wanted = spec.primary_key if kind == "p" else spec.unique[name]
            if actual.columns != wanted:
                problems.append((FAIL, f"constraint {name} is on {_names(actual.columns)}, expected {_names(wanted)}"))
        elif kind == "f":
            problems += _compare_foreign_key(name, spec.foreign_keys[name], actual)
        else:
            column, allowed = spec.checks[name]
            values = check_values(actual.definition, column)
            if values is None:
                problems.append(
                    (LIMITED, f"constraint {name} could not be compared: unrecognised form {actual.definition}")
                )
            elif values != allowed:
                found, wanted = ", ".join(sorted(values)), ", ".join(sorted(allowed))
                problems.append((FAIL, f"constraint {name} allows {found}; expected {wanted}"))
    for name in sorted(set(constraints) - set(expected_kinds)):
        kind = constraints[name].kind
        if kind in REJECTING_CONSTRAINTS:
            problems.append((FAIL, f"constraint {name} ({kind}) is not in the models and may reject rows"))
        else:
            problems.append((WARN, f"constraint {name} ({kind}) is not in the models"))
    return problems


def _compare_indexes(spec: TableSpec, indexes: Mapping[str, IndexInfo]) -> list[tuple[str, str]]:
    problems = []
    for name, expected in spec.indexes.items():
        actual = indexes.get(name)
        if actual is None:
            problems.append((FAIL, f"missing index {name}"))
            continue
        differences = []
        if actual.columns != expected.columns:
            differences.append(f"is on {_names(actual.columns)}, expected {_names(expected.columns)}")
        if actual.unique != expected.unique:
            differences.append("is UNIQUE" if actual.unique else "is not UNIQUE")
        if actual.method != "btree":
            differences.append(f"uses {actual.method}, expected btree")
        if actual.has_expressions:
            differences.append("indexes an expression")
        if actual.predicate is not None:
            differences.append(f"is partial (WHERE {actual.predicate})")
        if not actual.valid:
            differences.append("is INVALID (an interrupted CREATE INDEX CONCURRENTLY?)")
        problems += [(FAIL, f"index {name} {difference}") for difference in differences]
    for name in sorted(set(indexes) - set(spec.indexes)):
        if indexes[name].unique:
            problems.append((FAIL, f"unique index {name} is not in the models and may reject rows"))
        else:
            problems.append((WARN, f"index {name} is not in the models"))
    return problems


def compare_table(table: str, spec: TableSpec, s: Snapshot) -> list[tuple[str, str]]:
    """(level, message) for every difference from the models; empty when everything matches."""
    return [
        *_compare_columns(spec, s.columns.get(table, {})),
        *_compare_constraints(table, spec, s.constraints.get(table, {})),
        *_compare_indexes(spec, s.indexes.get(table, {})),
    ]


def evaluate_app_tables(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _skipped(s, "relations", "table details", "ownership")
    if skipped:
        return skipped
    existing = [name for name in APP_TABLES if name in s.relations]
    if not existing:
        return [Finding(INFO, "Core API tables", "none of the six tables exist")]
    out = []
    missing = [name for name in APP_TABLES if name not in s.relations]
    if missing:
        out.append(Finding(FAIL, "Core API tables", f"only some exist; missing: {', '.join(missing)}"))
    for table in existing:
        relation = s.relations[table]
        if relation.kind not in TABLE_KINDS:
            out.append(Finding(FAIL, table, f"is a {KIND_NAMES.get(relation.kind, relation.kind)}, not a table"))
            continue
        problems = compare_table(table, APP_TABLES[table], s)
        out += [Finding(level, table, message) for level, message in problems]
        if not problems:
            out.append(Finding(PASS, table, "columns, constraints and indexes match the models"))
        elif not any(level in BLOCKING for level, _ in problems):
            out.append(Finding(PASS, table, "everything the models define matches; review the extras above"))
        if acts_as_owner(s, expect.roles.connection, relation.owner):
            out.append(Finding(PASS, table, f"owned by {relation.owner}; the connection role can alter it"))
        else:
            out.append(
                Finding(
                    FAIL,
                    table,
                    f"owned by {relation.owner}; the connection role can't ALTER it "
                    "(the security migration needs to)",
                )
            )
    return out


def evaluate_alembic(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _skipped(s, "relations", "alembic history")
    if skipped:
        return skipped
    revisions = expect.revisions
    subject = "alembic_version"
    out = [
        Finding(
            INFO,
            "repository",
            f"revisions {' -> '.join(revisions.ordered)}; head {', '.join(revisions.heads)}",
        )
    ]
    tables = [name for name in APP_TABLES if name in s.relations]
    elsewhere = [schema for schema in s.version_schemas if schema != SCHEMA]
    if elsewhere:
        out.append(
            Finding(WARN, subject, f"also exists in schema {', '.join(elsewhere)}; this project uses public")
        )

    if SCHEMA not in s.version_schemas:
        if tables:
            out.append(
                Finding(
                    FAIL,
                    subject,
                    f"missing, but Core API tables exist ({', '.join(tables)}): created outside Alembic "
                    "or by an interrupted run. `alembic upgrade head` would fail on them; compare them "
                    "with the models before deciding anything (don't stamp blindly)",
                )
            )
        else:
            out.append(
                Finding(
                    PASS,
                    subject,
                    "missing, and none of the Core API tables exist: a fresh database, so "
                    "`alembic upgrade head` would apply every revision from the start",
                )
            )
        return out

    if s.version_rows is None:
        out.append(Finding(LIMITED, subject, "exists, but the connection role can't read it"))
        return out
    if not s.version_rows:
        if tables:
            out.append(Finding(FAIL, subject, f"is empty, but Core API tables exist ({', '.join(tables)})"))
        else:
            out.append(
                Finding(
                    WARN,
                    subject,
                    "exists but is empty (usually left by a downgrade to base); "
                    "`alembic upgrade head` would start from the first revision",
                )
            )
        return out
    if len(s.version_rows) > 1:
        out.append(
            Finding(
                FAIL,
                subject,
                f"has {len(s.version_rows)} rows ({', '.join(s.version_rows)}); "
                "this repository has a single head",
            )
        )
        return out

    current = s.version_rows[0]
    if current not in revisions.ordered:
        out.append(
            Finding(
                FAIL,
                subject,
                f"records {current}, which is not in this repository (another branch?); "
                "don't migrate until it is explained",
            )
        )
        return out
    pending = revisions.ordered[revisions.ordered.index(current) + 1 :]
    if pending:
        out.append(Finding(INFO, subject, f"at {current}; pending: {', '.join(pending)}"))
    else:
        out.append(Finding(PASS, subject, f"at head {current}; nothing to upgrade"))
    missing = [name for name in APP_TABLES if name not in s.relations]
    if missing:
        out.append(
            Finding(FAIL, subject, f"records {current}, but these tables are missing: {', '.join(missing)}")
        )
    return out


def evaluate_rls(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _roles_unknown(s, expect, "data api roles", "relations", "privileges", "alembic history")
    if skipped:
        return skipped
    tables = present_tables(s, (*APP_TABLES, VERSION_TABLE))
    if not tables:
        return [
            Finding(
                INFO,
                "RLS",
                "no Core API tables or Alembic version table yet; the security migration enables "
                "RLS and removes the browser roles' access when it runs",
            )
        ]
    secured = security_applied(s, expect.revisions)
    out = []
    for table in tables:
        relation = s.relations[table]
        if relation.forced:
            out.append(Finding(FAIL, table, "FORCE ROW LEVEL SECURITY is set; the owner would lose access too"))
        elif relation.rls:
            out.append(Finding(PASS, table, "RLS on, not forced"))
        elif secured:
            out.append(Finding(FAIL, table, "RLS off, although the security migration is recorded as applied"))
        else:
            out.append(Finding(INFO, table, "RLS off; the security migration will turn it on"))
        if s.policies.get(table):
            out.append(
                Finding(WARN, table, f"policies {', '.join(sorted(s.policies[table]))}; the migrations expect none")
            )
        grants = {
            grantee: privileges for grantee, privileges in s.grants.get(table, {}).items() if grantee != "PUBLIC"
        }
        if grants:
            listed = "; ".join(f"{grantee}: {', '.join(sorted(p))}" for grantee, p in sorted(grants.items()))
            out.append(Finding(INFO, table, f"direct grants: {listed}"))
        column_grantees = sorted(set(s.column_grants.get(table, {})) - {"PUBLIC"})
        if column_grantees:
            listed = "; ".join(
                f"{grantee}: "
                + ", ".join(_on_columns(p, cols) for p, cols in _column_privileges(s, table, grantee).items())
                for grantee in column_grantees
            )
            out.append(Finding(INFO, table, f"direct column grants: {listed}"))
        public, open_to, unknown = browser_access(s, table)
        if unknown:
            out.append(Finding(FAIL, table, f"no permission record for {', '.join(unknown)}"))
        if public:
            out.append(
                Finding(FAIL, table, f"PUBLIC (every role) has {', '.join(public)}; no migration revokes this")
            )
        if open_to:
            hint = "" if secured else "; the security migration revokes this"
            out.append(Finding(FAIL if secured else WARN, table, f"accessible to {'; '.join(open_to)}{hint}"))
        if not (public or open_to or unknown):
            out.append(Finding(PASS, table, "no privileges for PUBLIC or the Supabase browser roles"))
    return out


def evaluate_default_privileges(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _skipped(s, "data api roles", "default privileges")
    if skipped:
        return skipped
    connection_role = expect.roles.connection
    grouped: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for grant in s.default_grants:
        if grant.grantee in ("PUBLIC", *data_api_roles(s)):
            key = (grant.owner_role, grant.schema, grant.object_type)
            grouped.setdefault(key, {}).setdefault(grant.grantee, set()).add(grant.privilege)
    builtin = Finding(
        INFO,
        "defaults",
        "PostgreSQL itself lets PUBLIC execute new functions unless a default privilege revokes it; "
        "the routine checks above show the result for existing functions",
    )
    if not grouped:
        return [
            Finding(
                PASS,
                "defaults",
                "no ALTER DEFAULT PRIVILEGES entry gives PUBLIC or the browser roles access to new objects",
            ),
            builtin,
        ]
    out = [builtin]
    for (owner, schema, object_type), grantees in sorted(grouped.items()):
        objects = DEFAULT_ACL_OBJECTS.get(object_type, object_type)
        scope = f"in schema {schema}" if schema else "in every schema"
        listed = "; ".join(f"{grantee}: {', '.join(sorted(p))}" for grantee, p in sorted(grantees.items()))
        message = f"{objects} that {owner} creates {scope} are granted to {listed}"
        if owner != connection_role:
            out.append(Finding(INFO, "defaults", f"{message} (only affects objects {owner} creates)"))
        elif schema == SCHEMA and object_type in MIGRATION_DEFAULT_ACL_OBJECTS and "PUBLIC" not in grantees:
            out.append(Finding(INFO, "defaults", f"{message}; the security migration removes this"))
        else:
            out.append(
                Finding(
                    WARN,
                    "defaults",
                    f"{message}; the security migration doesn't change this (it removes only the "
                    "browser roles' public-schema defaults for tables, sequences and functions)",
                )
            )
    return out


def evaluate_queue(s: Snapshot, expect: Expectations) -> list[Finding]:
    skipped = _roles_unknown(
        s, expect, "data api roles", "relations", "table details", "privileges", "routines and types", "ownership"
    )
    if skipped:
        return skipped
    spec = expect.queue
    subject = f"procrastinate {spec.version}"
    queue_routines = [routine for routine in s.routines if routine.name.startswith(QUEUE_PREFIX)]
    found = {
        "tables": {name for name in s.relations if name.startswith(QUEUE_PREFIX) and s.relations[name].kind in TABLE_KINDS},
        "functions": {routine.name for routine in queue_routines},
        "types": {name for name in s.types if name.startswith(QUEUE_PREFIX)},
        "triggers": {name for table in QUEUE_TABLES for name in s.triggers.get(table, ())},
        "indexes": {name for table in QUEUE_TABLES for name in s.indexes.get(table, {})},
    }
    expected = {
        "tables": spec.tables,
        "functions": spec.functions,
        "types": spec.types,
        "triggers": spec.triggers,
        "indexes": spec.indexes,
    }
    if not any(found[kind] for kind in ("tables", "functions", "types")):
        return [
            Finding(
                INFO,
                subject,
                "queue schema not installed; after `alembic upgrade head` install it "
                "(python -m scripts.install_queue_schema), then run scripts.secure_queue_schema",
            )
        ]

    out = []
    for kind, names in expected.items():
        missing = sorted(names - found[kind])
        extra = sorted(found[kind] - names)
        if missing:
            out.append(Finding(FAIL, subject, f"incomplete; missing {kind}: {', '.join(missing)}"))
        if extra:
            out.append(
                Finding(WARN, subject, f"{kind} not in this version's schema (another version?): {', '.join(extra)}")
            )
    if not out:
        counts = ", ".join(f"{len(names)} {kind}" for kind, names in expected.items())
        out.append(Finding(PASS, subject, f"complete: {counts}"))

    connection_role = expect.roles.connection
    owners = {s.relations[name].owner for name in found["tables"]} | {r.owner for r in queue_routines}
    for owner in sorted(owners):
        if not acts_as_owner(s, connection_role, owner):
            out.append(
                Finding(WARN, subject, f"objects owned by {owner}; scripts.secure_queue_schema must run as that role")
            )
    # Before scripts.secure_queue_schema runs, the browser roles' access is expected (Procrastinate
    # creates its objects with default privileges); afterwards any access is a regression.
    secured = queue_secured(s)
    exposure_level = FAIL if secured else WARN
    hint = (
        "; the queue was secured, so this was granted afterwards: rerun scripts.secure_queue_schema --apply"
        if secured
        else "; scripts.secure_queue_schema --apply revokes this"
    )
    for table in present_tables(s, QUEUE_TABLES):
        relation = s.relations[table]
        if relation.forced:
            out.append(Finding(FAIL, table, "FORCE ROW LEVEL SECURITY is set; the worker would lose access"))
        elif relation.rls:
            out.append(Finding(PASS, table, "RLS on, not forced"))
        else:
            out.append(Finding(WARN, table, "RLS off; secure it with scripts.secure_queue_schema --check, then --apply"))
        if s.policies.get(table):
            out.append(Finding(WARN, table, f"policies {', '.join(sorted(s.policies[table]))}; none expected"))
        public, open_to, unknown = browser_access(s, table)
        if unknown:
            out.append(Finding(FAIL, table, f"no permission record for {', '.join(unknown)}"))
        exposed = _exposed(public, open_to)
        if exposed:
            out.append(Finding(exposure_level, table, f"accessible to {'; '.join(exposed)}{hint}"))
        elif not unknown:
            out.append(Finding(PASS, table, "no privileges for PUBLIC or the Supabase browser roles"))

    sequences = queue_sequences(s)
    open_sequences = []
    for name in sequences:
        public, open_to, unknown = object_exposure(s, name)
        if unknown:
            out.append(Finding(FAIL, name, f"no permission record for {', '.join(unknown)}"))
        exposed = _exposed(public, open_to)
        if exposed:
            open_sequences.append(name)
            out.append(Finding(exposure_level, name, f"sequence accessible to {'; '.join(exposed)}{hint}"))
    if sequences and not open_sequences:
        out.append(
            Finding(PASS, subject, f"{len(sequences)} queue sequences: no privileges for PUBLIC or the browser roles")
        )

    executable_by: set[str] = set()
    no_record: set[str] = set()
    for routine in queue_routines:
        callers, unknown = routine_exposure(s, routine)
        executable_by.update(callers)
        no_record.update(unknown)
        if routine.security_definer:
            if callers:
                out.append(
                    Finding(
                        FAIL,
                        routine.signature,
                        f"SECURITY DEFINER and executable by {', '.join(callers)}: runs with "
                        f"{routine.owner}'s privileges (Procrastinate {spec.version} defines none)",
                    )
                )
            else:
                out.append(
                    Finding(
                        WARN,
                        routine.signature,
                        f"SECURITY DEFINER (Procrastinate {spec.version} defines none); review it",
                    )
                )
    if no_record:
        out.append(Finding(FAIL, subject, f"no EXECUTE record on queue functions for {', '.join(sorted(no_record))}"))
    if executable_by:
        callers = ", ".join(sorted(executable_by))
        out.append(Finding(exposure_level, subject, f"queue functions executable by {callers}{hint}"))
    elif not no_record:
        out.append(Finding(PASS, subject, "queue functions not executable by PUBLIC or the browser roles"))
    return out


def _relation_exposure_level(relation: Relation) -> tuple[str, str]:
    """(level, why) for PUBLIC or browser-role access to a relation no other section covers."""
    kind = relation.kind
    if relation.extension_member:
        return WARN, "belongs to an extension; confirm the extension means to expose it"
    if kind == "v":
        if security_invoker(relation):
            return WARN, "security_invoker view: the caller's privileges and RLS apply; confirm this is intended"
        return FAIL, f"view runs with {relation.owner}'s privileges, so RLS on the tables it reads doesn't apply"
    if kind == "m":
        return FAIL, "materialized view: RLS doesn't apply to its stored rows"
    if kind == "f":
        return FAIL, "foreign table: RLS doesn't apply to the remote data"
    if kind == "S":
        if relation.owned_by in (*APP_TABLES, VERSION_TABLE):
            return FAIL, f"sequence of {relation.owned_by}"
        return WARN, "sequence: callers can read and advance it"
    if relation.rls:
        return WARN, "RLS on: its policies decide which rows are visible; review them"
    return FAIL, "RLS off: every row is visible to these roles"


def evaluate_object_access(s: Snapshot, expect: Expectations) -> list[Finding]:
    """PUBLIC and browser-role access to everything in public the other sections don't cover."""
    skipped = _roles_unknown(s, expect, "data api roles", "relations", "privileges", "routines and types")
    if skipped:
        return skipped
    # Only real tables and sequences: a view or other object that reuses one of these names is
    # checked here like any other relation.
    covered = {*present_tables(s, (*APP_TABLES, VERSION_TABLE, *QUEUE_TABLES)), *queue_sequences(s)}
    out = []
    for name, relation in sorted(s.relations.items()):
        if name in covered:
            continue
        public, open_to, unknown = object_exposure(s, name)
        label = KIND_NAMES.get(relation.kind, relation.kind)
        if unknown:
            out.append(Finding(FAIL, name, f"{label}: no permission record for {', '.join(unknown)}"))
        exposed = _exposed(public, open_to)
        if exposed:
            level, why = _relation_exposure_level(relation)
            out.append(Finding(level, name, f"{label} accessible to {'; '.join(exposed)}: {why}"))

    for routine in s.routines:
        if routine.name.startswith(QUEUE_PREFIX):
            continue
        callers, unknown = routine_exposure(s, routine)
        label = routine_kind(routine)
        if unknown:
            out.append(Finding(FAIL, routine.signature, f"{label}: no EXECUTE record for {', '.join(unknown)}"))
        if routine.security_definer and callers:
            level = WARN if routine.extension_member else FAIL
            note = "; it belongs to an extension, review it" if routine.extension_member else ""
            out.append(
                Finding(
                    level,
                    routine.signature,
                    f"SECURITY DEFINER {label} executable by {', '.join(callers)}: runs with "
                    f"{routine.owner}'s privileges and the Data API can call it{note}",
                )
            )
        elif routine.security_definer and not routine.extension_member:
            out.append(
                Finding(
                    WARN,
                    routine.signature,
                    f"SECURITY DEFINER {label}, not executable by PUBLIC or the browser roles; review it",
                )
            )
        elif callers and not routine.extension_member:
            out.append(
                Finding(
                    WARN,
                    routine.signature,
                    f"{label} executable by {', '.join(callers)} with the caller's privileges; the Data "
                    "API exposes it as an RPC, so confirm that is intended",
                )
            )
    if not out:
        out.append(
            Finding(
                PASS,
                "public",
                "no other relation, sequence or routine is accessible to PUBLIC or the browser roles, "
                "and none is SECURITY DEFINER",
            )
        )
    return out


def evaluate_unexpected(s: Snapshot) -> list[Finding]:
    skipped = _skipped(s, "relations", "routines and types")
    if skipped:
        return skipped
    queue_names = [name for name in s.relations if name.startswith(QUEUE_PREFIX)]
    known = {*present_tables(s, (*APP_TABLES, VERSION_TABLE, *queue_names)), *queue_sequences(s)}
    relations = [
        f"{name} ({KIND_NAMES.get(relation.kind, relation.kind)})"
        for name, relation in s.relations.items()
        if name not in known and not relation.extension_member
    ]
    routines = [
        routine.signature
        for routine in s.routines
        if not routine.name.startswith(QUEUE_PREFIX) and not routine.extension_member
    ]
    types = [name for name, extension in s.types.items() if not name.startswith(QUEUE_PREFIX) and not extension]
    extension_objects = (
        sum(relation.extension_member for relation in s.relations.values())
        + sum(routine.extension_member for routine in s.routines)
        + sum(s.types.values())
    )
    out = []
    for label, names in (("relations", relations), ("functions", routines), ("types", types)):
        if names:
            out.append(
                Finding(
                    WARN,
                    "public",
                    f"{label} not created by this project: {', '.join(sorted(names))}; "
                    "the migrations don't touch them, but review them before migrating",
                )
            )
    if extension_objects:
        out.append(Finding(INFO, "public", f"{extension_objects} objects belong to extensions (not reviewed)"))
    if not (relations or routines or types):
        out.append(Finding(PASS, "public", "nothing besides the Core API, Alembic and Procrastinate objects"))
    return out


def evaluate(s: Snapshot, expect: Expectations) -> list[tuple[str, list[Finding]]]:
    sections = [
        ("Roles for migrations, the Core API and the worker", evaluate_roles(s, expect)),
        ("Roles the Data API can switch to", evaluate_data_api_roles(s, expect)),
        ("Core API tables", evaluate_app_tables(s, expect)),
        ("Alembic history", evaluate_alembic(s, expect)),
        ("RLS, grants and policies: Core API tables and alembic_version", evaluate_rls(s, expect)),
        ("Default privileges", evaluate_default_privileges(s, expect)),
        ("Procrastinate queue", evaluate_queue(s, expect)),
        ("Privileges on other objects in public", evaluate_object_access(s, expect)),
        ("Other objects in the public schema", evaluate_unexpected(s)),
    ]
    if s.limited:
        sections.append(
            (
                "Checks that could not run",
                [Finding(LIMITED, name, reason) for name, reason in s.limited.items()],
            )
        )
    return sections


def print_report(sections: list[tuple[str, list[Finding]]]) -> int:
    counts: Counter[str] = Counter()
    for title, findings in sections:
        print(f"\n== {title} ==")
        for finding in findings:
            counts[finding.level] += 1
            print(f"{finding.level:<7} | {finding.subject} | {finding.message}")
    print("\nSummary: " + ", ".join(f"{counts[level]} {level}" for level in LEVELS))
    if any(counts[level] for level in BLOCKING):
        print("NOT READY: resolve every FAIL and LIMITED finding before migrating. Nothing was changed.")
        return 1
    print("No blocking findings. Review every WARN before migrating. Nothing was changed.")
    return 0


def connection_failure_hint(message: str) -> str:
    """A fixed description of a connection failure; the message itself is never returned."""
    lowered = message.lower()
    for pattern, hint in CONNECTION_FAILURE_HINTS:
        if pattern in lowered:
            return hint
    return "no SQLSTATE: the connection failed or was lost; details hidden"


def safe_error_summary(error: DBAPIError) -> str:
    """Exception class and SQLSTATE only: server messages can name the user, host or project.

    psycopg gives no SQLSTATE for failures while connecting, so those get a fixed hint instead."""
    sqlstate = getattr(error.orig, "sqlstate", None)
    if sqlstate:
        hint = SQLSTATE_HINTS.get(sqlstate, "details hidden")
    else:
        hint = connection_failure_hint(str(error.orig))
    return f"database error {type(error.orig).__name__} (SQLSTATE {sqlstate or 'unknown'}: {hint})"


def unexpected_error_summary(error: BaseException) -> str:
    """Exception class and where it was raised, never its message: messages can contain the URL."""
    frames = traceback.extract_tb(error.__traceback__)
    where = ""
    if frames:
        frame = frames[-1]
        where = f" at {Path(frame.filename).name}:{frame.lineno} in {frame.name}"
    return f"unexpected {type(error).__name__}{where} (details hidden)"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.supabase_preflight",
        description="Read-only check of the database before running migrations on Supabase.",
    )
    parser.add_argument(
        "--local-test",
        action="store_true",
        help="target a local *_test database instead of Supabase (for testing this script)",
    )
    parser.add_argument(
        "--expect-database",
        help="database name to expect (default: postgres; with --local-test, the URL's database)",
    )
    parser.add_argument("--app-role", help="role the Core API connects as (default: the connected role)")
    parser.add_argument("--worker-role", help="role the worker connects as (default: the connected role)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="don't ask for confirmation after the identity checks (the checks still run)",
    )
    parser.add_argument(
        "--allow-unverified-tls",
        action="store_true",
        help=(
            "accept sslmode=require (no certificate check) or verify-ca (no host name check), "
            "reported as a WARN; never needed with verify-full"
        ),
    )
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as error:  # noqa: BLE001 - any message could contain the URL; report the class only
        print(f"ERROR: {unexpected_error_summary(error)}. Nothing was changed.", file=sys.stderr)
        return 1


def run(args: argparse.Namespace) -> int:
    try:
        revisions = load_revisions()
        queue = load_queue_spec()
        raw, source = read_secret(os.environ, URL_ENV, "Database URL (input hidden): ")
        url = target_url(raw)
        check_connection_overrides(url, os.environ)
        if args.local_test:
            target_findings = check_local_test_target(url)
            expected_database = args.expect_database or url.database
        else:
            expected_ref, _ = read_secret(
                os.environ, PROJECT_REF_ENV, "Expected Supabase project reference (input hidden): "
            )
            target_findings = check_supabase_target(url, expected_ref, args.allow_unverified_tls)
            expected_database = args.expect_database or SUPABASE_DATABASE
    except (PreflightRefused, safety.UnsafeDatabaseTarget) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(f"Target: {redacted_target(url)} (URL from {source})")
    # Takes precedence over a connect_timeout in the URL.
    engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS})
    stage = "while connecting"
    try:
        with engine.connect() as connection:
            stage = "after connecting"
            begin_read_only(connection)
            identity = read_identity(connection)
            connection.rollback()
            print_identity(identity)
            problems = identity_problems(identity, expected_database, supabase=not args.local_test)
            if problems:
                raise PreflightRefused("; ".join(problems))
            if not confirmed(args.yes):
                raise PreflightRefused("not confirmed; nothing else was read")

            begin_read_only(connection)
            if read_identity(connection) != identity:
                raise PreflightRefused("the connection's identity changed between transactions")
            roles = Roles(identity.role, args.app_role or identity.role, args.worker_role or identity.role)
            snapshot = inspect_database(connection, roles)
            connection.rollback()
    except PreflightRefused as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except DBAPIError as error:
        print(f"ERROR: {safe_error_summary(error)} {stage}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    expectations = Expectations(roles, revisions, queue, identity.supabase_roles)
    sections = [("Connection identity", identity_findings(identity, target_findings))]
    sections += evaluate(snapshot, expectations)
    return print_report(sections)


if __name__ == "__main__":
    sys.exit(main())
