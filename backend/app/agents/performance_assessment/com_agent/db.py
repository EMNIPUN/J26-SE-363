"""Decoupled PostgreSQL connection and persistence layer for Performance Assessment Agent.

Strictly isolated:
- Dedicated to the performance assessment database (assessment_db).
- Manages LangGraph PostgresSaver checkpointer and result tables.
- Graceful offline fallback to in-memory checkpointer when PostgreSQL is unavailable or in dev mode.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def get_db_url() -> str:
    """Resolve PostgreSQL connection URL from environment variables."""
    custom_url = os.getenv("DATABASE_URL")
    if custom_url:
        return custom_url

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5434")
    db = os.getenv("POSTGRES_DB", "assessment_db")
    user = os.getenv("POSTGRES_USER", "assessment_user")
    password = os.getenv("POSTGRES_PASSWORD", "assessment_pass")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# SQL Table Definitions
INIT_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS assessment_results (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    sprint_id VARCHAR(64) NOT NULL,
    team_id VARCHAR(64) NOT NULL,
    final_score DOUBLE PRECISION NOT NULL,
    behavioral_persona VARCHAR(64),
    lecturer_override_applied BOOLEAN DEFAULT FALSE,
    data JSONB NOT NULL,
    assessed_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_student_sprint UNIQUE (student_id, sprint_id)
);

CREATE TABLE IF NOT EXISTS student_feedback (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(64) NOT NULL,
    sprint_id VARCHAR(64) NOT NULL,
    final_score DOUBLE PRECISION NOT NULL,
    behavioral_persona VARCHAR(64),
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_student_feedback UNIQUE (student_id, sprint_id)
);

CREATE TABLE IF NOT EXISTS cohort_baselines (
    id SERIAL PRIMARY KEY,
    team_id VARCHAR(64) NOT NULL,
    sprint_id VARCHAR(64) NOT NULL,
    baseline_metrics JSONB NOT NULL,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_team_sprint_baseline UNIQUE (team_id, sprint_id)
);

CREATE INDEX IF NOT EXISTS idx_assessment_student_sprint ON assessment_results (student_id, sprint_id);
CREATE INDEX IF NOT EXISTS idx_feedback_student_sprint ON student_feedback (student_id, sprint_id);
"""


def init_assessment_db(db_url: Optional[str] = None) -> bool:
    """Initialize PostgreSQL tables. Returns True on success, False if DB is unreachable."""
    url = db_url or get_db_url()
    try:
        import psycopg

        with psycopg.connect(url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(INIT_TABLES_SQL)
        logger.info("Assessment database tables initialized successfully.")
        return True
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL ({url}): {e}. Using fallback.")
        return False


def get_checkpointer(db_url: Optional[str] = None) -> Any:
    """Returns PostgresSaver if available and online, otherwise returns MemorySaver fallback."""
    from app.agents.performance_assessment.com_agent.config.settings_loader import IS_DEV_MODE

    # If explicitly in dev mode or DB is not reachable, use MemorySaver
    if IS_DEV_MODE:
        from app.agents.performance_assessment.com_agent.graph import MemorySaver
        return MemorySaver()

    url = db_url or get_db_url()

    # Try LangGraph PostgresSaver
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg

        # Quick connectivity test
        with psycopg.connect(url) as conn:
            pass

        checkpointer = PostgresSaver.from_conn_string(url)
        # Ensure LangGraph checkpoint migrations are set up
        if hasattr(checkpointer, "setup"):
            checkpointer.setup()
        logger.info("Successfully connected to PostgresSaver checkpointer.")
        return checkpointer
    except Exception as e:
        logger.warning(f"PostgresSaver unavailable ({e}). Falling back to MemorySaver.")
        from app.agents.performance_assessment.com_agent.graph import MemorySaver
        return MemorySaver()


def save_assessment_result_db(result_data: Dict[str, Any], db_url: Optional[str] = None) -> bool:
    """Persist finalized AssessmentResultSchema into assessment_results table."""
    url = db_url or get_db_url()
    try:
        import psycopg

        student_id = result_data.get("student_id")
        sprint_id = result_data.get("sprint_id")
        team_id = result_data.get("team_id", "")
        final_score = float(result_data.get("final_score", 0.0))
        persona = result_data.get("behavioral_persona", "")
        override = bool(result_data.get("lecturer_override_applied", False))

        sql = """
        INSERT INTO assessment_results (student_id, sprint_id, team_id, final_score, behavioral_persona, lecturer_override_applied, data)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (student_id, sprint_id)
        DO UPDATE SET
            final_score = EXCLUDED.final_score,
            behavioral_persona = EXCLUDED.behavioral_persona,
            lecturer_override_applied = EXCLUDED.lecturer_override_applied,
            data = EXCLUDED.data,
            assessed_at = NOW();
        """
        with psycopg.connect(url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (student_id, sprint_id, team_id, final_score, persona, override, json.dumps(result_data)))
        return True
    except Exception as e:
        logger.warning(f"Failed to persist assessment result to PostgreSQL: {e}")
        return False


def save_student_feedback_db(feedback_data: Dict[str, Any], db_url: Optional[str] = None) -> bool:
    """Persist StudentFeedbackSchema into student_feedback table."""
    url = db_url or get_db_url()
    try:
        import psycopg

        student_id = feedback_data.get("student_id")
        sprint_id = feedback_data.get("sprint_id")
        final_score = float(feedback_data.get("final_score", 0.0))
        persona = feedback_data.get("behavioral_persona", "")

        sql = """
        INSERT INTO student_feedback (student_id, sprint_id, final_score, behavioral_persona, data)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (student_id, sprint_id)
        DO UPDATE SET
            final_score = EXCLUDED.final_score,
            behavioral_persona = EXCLUDED.behavioral_persona,
            data = EXCLUDED.data,
            created_at = NOW();
        """
        with psycopg.connect(url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (student_id, sprint_id, final_score, persona, json.dumps(feedback_data)))
        return True
    except Exception as e:
        logger.warning(f"Failed to persist student feedback to PostgreSQL: {e}")
        return False


def get_assessment_result_db(student_id: str, sprint_id: str, db_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve an assessment result from PostgreSQL."""
    url = db_url or get_db_url()
    try:
        import psycopg

        sql = "SELECT data FROM assessment_results WHERE student_id = %s AND sprint_id = %s;"
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (student_id, sprint_id))
                row = cur.fetchone()
                if row:
                    return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None
    except Exception as e:
        logger.warning(f"Failed to query assessment result from PostgreSQL: {e}")
        return None
