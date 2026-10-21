"""Report which detection tools are installed.  Run: python -m app.agents.security_assistant.tools.check"""

import asyncio
import sys

from app.agents.security_assistant.tools.runner import default_tools


async def main() -> int:
    missing = 0
    for tool in default_tools():
        ok, version = await tool.check_available()
        missing += not ok
        print(f"{tool.name:<12} {'ok     ' if ok else 'MISSING'} {version or ''}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
