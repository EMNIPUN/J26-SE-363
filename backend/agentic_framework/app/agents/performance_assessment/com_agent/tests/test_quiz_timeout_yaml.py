"""Unit tests for quiz_timeout_settings.yaml verification (T0.2.2)."""

import pathlib
import yaml
import pytest
import math

CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "quiz_timeout_settings.yaml"

def test_quiz_timeout_settings_exists_and_parses():
    assert CONFIG_PATH.exists(), f"quiz_timeout_settings.yaml not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "YAML root must be a mapping"
    assert "version" in data, "Missing 'version' field"
    assert "code_ownership_quiz" in data, "Missing 'code_ownership_quiz' section"
    assert "github_api" in data, "Missing 'github_api' section"

def test_code_ownership_quiz_settings():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    quiz_cfg = data["code_ownership_quiz"]
    assert quiz_cfg["time_window_hours"] == 48, f"time_window_hours must be 48, got {quiz_cfg.get('time_window_hours')}"
    assert quiz_cfg["extra_time_hours"] == 48, f"extra_time_hours must be 48, got {quiz_cfg.get('extra_time_hours')}"
    assert math.isclose(quiz_cfg["capped_score_ceiling"], 0.50, rel_tol=1e-5), f"capped_score_ceiling must be 0.50, got {quiz_cfg.get('capped_score_ceiling')}"
    assert isinstance(quiz_cfg["time_window_hours"], int)
    assert isinstance(quiz_cfg["extra_time_hours"], int)
    assert 0.0 < quiz_cfg["capped_score_ceiling"] <= 1.0

def test_github_api_settings():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    gh_cfg = data["github_api"]
    assert gh_cfg["max_calls_per_student"] == 30, f"max_calls_per_student must be 30, got {gh_cfg.get('max_calls_per_student')}"
    assert isinstance(gh_cfg["max_calls_per_student"], int)
    assert gh_cfg["max_calls_per_student"] > 0
