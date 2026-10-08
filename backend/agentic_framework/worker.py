"""
Agentic Framework Worker Entrypoint.

Starts the Procrastinate worker that consumes jobs from the PostgreSQL queue.

Run:
    cd backend/agentic_framework
    uv run python -m worker

Or, to run specific queues only:
    uv run python -m worker --queues performance planning
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


def main(queues: list[str] | None = None) -> None:
    # Import all task modules first — this registers @app.task decorators
    import app.tasks  # noqa: F401

    from shared.queue import app, get_dsn

    dsn = get_dsn()
    if not dsn:
        logger.error("No database DSN found. Set SERVER_DIRECT_URL or SERVER_DATABASE_URL in .env")
        sys.exit(1)

    logger.info(f"Starting Procrastinate worker (queues: {queues or 'all'})")

    async def run() -> None:
        async with app.open_async():
            worker = app.run_worker_async(
                queues=queues,
                install_signal_handlers=True,
            )
            await worker

    asyncio.run(run())


if __name__ == "__main__":
    # Optional: accept --queues flag from CLI
    import argparse

    parser = argparse.ArgumentParser(description="SELVIA Agentic Framework Worker")
    parser.add_argument(
        "--queues",
        nargs="*",
        default=None,
        help="Queue names to consume (default: all queues)",
    )
    args = parser.parse_args()
    main(queues=args.queues)
