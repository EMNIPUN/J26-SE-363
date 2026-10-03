"""Unit tests for dependency and environment setup (T0.5)."""

import pathlib
import pytest

COM_AGENT_DIR = pathlib.Path(__file__).resolve().parent.parent
BACKEND_DIR = next((p for p in COM_AGENT_DIR.parents if p.name == "backend"), COM_AGENT_DIR.parent.parent.parent.parent.parent)

def test_requirements_file_content():
    req_file = BACKEND_DIR / "requirements.txt"
    assert req_file.exists(), f"requirements.txt not found at {req_file}"
    content = req_file.read_text(encoding="utf-8")

    expected_pkgs = [
        "langgraph",
        "langchain",
        "langchain-core",
        "langsmith",
        "pydantic",
        "pyyaml",
        "python-dotenv",
        "pytest",
        "pytest-asyncio",
    ]
    for pkg in expected_pkgs:
        assert pkg in content, f"Expected {pkg} in requirements.txt"

def test_env_example_content():
    env_file = COM_AGENT_DIR / ".env.example"
    assert env_file.exists(), f".env.example not found at {env_file}"
    content = env_file.read_text(encoding="utf-8")

    expected_vars = [
        "COM_AGENT_ENV",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
    ]
    for var in expected_vars:
        assert var in content, f"Expected {var} in .env.example"
