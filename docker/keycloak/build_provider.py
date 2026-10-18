#!/usr/bin/env python3
"""Builds the Keycloak plugin in docker/keycloak/providers-src/link-by-email-code and puts the jar
in docker/keycloak/providers/, which docker-compose mounts into Keycloak.

It needs only Docker (Maven and Java run in a container), so it works the same on a laptop and on
the server. The unit tests run as part of the build. Restart Keycloak afterwards.

    python docker/keycloak/build_provider.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "providers-src" / "link-by-email-code"
TARGET = HERE / "providers"
JAR = "selvia-link-by-email-code.jar"
IMAGE = "maven:3.9-eclipse-temurin-17"


def main() -> int:
    command = [
        "docker", "run", "--rm",
        "-v", f"{SOURCE}:/src",
        "-v", "selvia-maven-cache:/root/.m2",  # keeps the downloaded Keycloak libraries between builds
        "-w", "/src",
        IMAGE,
        "mvn", "-q", "-B", "package",
    ]
    print("Building the plugin (and running its tests)...")
    if subprocess.run(command).returncode != 0:
        print("error: the build failed", file=sys.stderr)
        return 1
    TARGET.mkdir(exist_ok=True)
    shutil.copyfile(SOURCE / "target" / JAR, TARGET / JAR)
    print(f"Done: {TARGET / JAR}. Restart Keycloak to load it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
