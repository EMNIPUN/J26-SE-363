import os
import sys
import asyncio
import procrastinate
from dotenv import load_dotenv

# psycopg async on Windows requires WindowsSelectorEventLoopPolicy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv(dotenv_path="backend/.env", override=False)
load_dotenv(dotenv_path=".env", override=False)
# backend/.env when running from backend/server or backend/agentic_framework
load_dotenv(dotenv_path="../.env", override=False)

def get_dsn() -> str:
    """Return a psycopg-compatible DSN (strips SQLAlchemy dialect prefix).
    
    Prefers SERVER_DIRECT_URL (port 5432) which supports direct session connections.
    """
    url = (
        os.getenv("SERVER_DIRECT_URL")
        or os.getenv("SERVER_DATABASE_URL")
        or ""
    )
    return url.replace("postgresql+psycopg://", "postgresql://")

# Global Procrastinate App instance initialized with the Supabase connection info
app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(conninfo=get_dsn())
)
