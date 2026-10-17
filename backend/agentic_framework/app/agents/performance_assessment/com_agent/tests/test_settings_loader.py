"""Unit tests for settings_loader.py (T0.3.1 - T0.3.4)."""

import os
import pytest
from pydantic import ValidationError
from app.agents.performance_assessment.com_agent.config.settings_loader import (
    settings,
    IS_DEV_MODE,
    AppSettings,
    FactorWeightsConfig,
    QuizTimeoutSettings,
    GitHubAPISettings,
    load_settings,
)

def test_singleton_settings_loaded():
    assert isinstance(settings, AppSettings)
    assert isinstance(settings.weights_config, FactorWeightsConfig)
    assert isinstance(settings.quiz_timeout, QuizTimeoutSettings)
    assert isinstance(settings.github_api, GitHubAPISettings)
    assert settings.quiz_timeout.time_window_hours == 48
    assert settings.quiz_timeout.extra_time_hours == 48
    assert settings.quiz_timeout.capped_score_ceiling == 0.50
    assert settings.github_api.max_calls_per_student == 30
    assert IS_DEV_MODE is True or IS_DEV_MODE is False

def test_factor_weights_validation_success():
    valid = {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.15,
    }
    cfg = FactorWeightsConfig(factor_weights=valid)
    assert cfg.factor_weights["effort"] == 0.20

def test_factor_weights_missing_factor_fails():
    invalid = {
        "effort": 0.35,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        # code_ownership missing
    }
    with pytest.raises(ValidationError) as exc:
        FactorWeightsConfig(factor_weights=invalid)
    assert "Missing required factor weights" in str(exc.value)

def test_factor_weights_sum_not_one_fails():
    invalid = {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.14,  # sums to 0.99
    }
    with pytest.raises(ValidationError) as exc:
        FactorWeightsConfig(factor_weights=invalid)
    assert "must sum to 1.0" in str(exc.value)

def test_factor_weights_out_of_bounds_fails():
    invalid = {
        "effort": -0.10,
        "consistency": 0.45,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.15,
    }
    with pytest.raises(ValidationError) as exc:
        FactorWeightsConfig(factor_weights=invalid)
    assert "must be in (0.0, 1.0]" in str(exc.value)

def test_quiz_timeout_validation():
    with pytest.raises(ValidationError):
        QuizTimeoutSettings(time_window_hours=-1)

    with pytest.raises(ValidationError):
        QuizTimeoutSettings(capped_score_ceiling=1.5)

def test_github_api_validation():
    with pytest.raises(ValidationError):
        GitHubAPISettings(max_calls_per_student=0)

def test_env_resolution(monkeypatch):
    monkeypatch.setenv("COM_AGENT_ENV", "production")
    s_prod = load_settings()
    assert s_prod.env == "production"
    assert s_prod.is_dev_mode is False

    monkeypatch.setenv("COM_AGENT_ENV", "development")
    s_dev = load_settings()
    assert s_dev.env == "development"
    assert s_dev.is_dev_mode is True
