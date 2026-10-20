"""SELVIA AI Backend. Internal service: only the Core API calls it.

Starting this server also starts the job worker (the part that really runs the assessment agent), so one command starts everything:

    uv run --active --no-sync uvicorn app.main:app --port 8003

Set AGENT_RUN_WORKER=0 to start the HTTP server alone, and `uv run python -m worker` to run the worker on its own (for example on a second machine).
"""

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

# uvicorn only configures its own loggers; without this the worker's job logs (and these messages) would not show in the terminal.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

RETRY_SECONDS = 10


def worker_wanted() -> bool:
    return os.environ.get("AGENT_RUN_WORKER", "1").strip().lower() not in ("0", "false", "no", "off")


async def run_worker() -> None:
    """Keep a queue worker running. A failure to reach the queue is logged and retried, never silent and never fatal for the HTTP server."""
    import app.tasks  # noqa: F401  registers the @task jobs

    from shared.queue import app as queue, get_dsn

    if not get_dsn():
        logger.error("No queue database URL (SERVER_DIRECT_URL in backend/agentic_framework/.env): the job worker was NOT started.")
        return
    while True:
        try:
            logger.info("Job worker: connecting to the queue ...")
            async with queue.open_async():
                logger.info("Job worker: connected, waiting for jobs (queues: all).")
                await queue.run_worker_async(install_signal_handlers=False)  # the server owns the signals
            logger.warning("Job worker stopped; starting it again.")
        except asyncio.CancelledError:
            logger.info("Job worker: stopping with the server.")
            raise
        except Exception:
            logger.exception("Job worker failed (for example the database is unreachable or out of connections); trying again in %s s.", RETRY_SECONDS)
        await asyncio.sleep(RETRY_SECONDS)


class WorkerThread:
    """The worker on a thread of its own, with its own event loop.

    Two reasons: the database driver's async mode cannot run on the loop uvicorn uses on Windows (it needs the selector loop), and an assessment does heavy work that must not slow the HTTP server.
    """

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.task: asyncio.Task | None = None
        self.thread = threading.Thread(target=self._run, name="procrastinate-worker", daemon=True)

    def _run(self) -> None:
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        self.loop = loop
        self.task = loop.create_task(run_worker())
        try:
            loop.run_until_complete(self.task)
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        if self.loop is not None and self.task is not None and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.task.cancel)
        self.thread.join(timeout=15)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    worker = WorkerThread() if worker_wanted() else None
    if worker is None:
        logger.info("Job worker not started (AGENT_RUN_WORKER=0).")
    else:
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()


app = FastAPI(
    title=settings.APP_NAME,
    description="Main Orchestrator and specialized agents for SELVIA",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str | bool]:
    return {"status": "UP", "service": settings.APP_NAME, "environment": settings.APP_ENV, "worker": worker_wanted()}
