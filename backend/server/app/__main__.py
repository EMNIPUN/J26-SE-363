"""Run the Core API with PORT from backend/server/.env (default 8020).

    uv run python -m app
    # or, if uv trampoline fails on Windows:
    .\\.venv\\Scripts\\python.exe -m app
"""

import uvicorn

from app.core.config import settings


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
