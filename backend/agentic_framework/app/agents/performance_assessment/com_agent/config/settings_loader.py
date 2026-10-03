"""Pydantic configuration loader and environment resolver for com_agent.

Strictly aligned with:
- PLAN.md Section 12.2 (Quiz Timeout Settings)
- PLAN.md Section 12.5 (AHP Factor Weights Config & Sum Validation)
- PLAN.md Section 12.7 (GitHub API Rate Limiting)
- PLAN.md Section 12.8 (Environment Resolution & Mock Mode Flag)
"""

import os
import math
import pathlib
from typing import Dict, Optional, Any
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


REQUIRED_FACTORS = {
    "effort",
    "consistency",
    "requirement_fulfillment",
    "collaboration",
    "task_complexity",
    "code_ownership",
}


class QuizTimeoutSettings(BaseModel):
    """Configuration for Code Ownership active verification quiz timeouts."""
    model_config = ConfigDict(extra="ignore")

    time_window_hours: int = Field(default=48, gt=0, description="Initial answer window in hours")
    extra_time_hours: int = Field(default=48, gt=0, description="Extension window in hours upon first timeout")
    capped_score_ceiling: float = Field(
        default=0.50, gt=0.0, le=1.0, description="Max KO score allowed after extension"
    )


class GitHubAPISettings(BaseModel):
    """Configuration for GitHub API rate limiting and sandbox fallback."""
    model_config = ConfigDict(extra="ignore")

    max_calls_per_student: int = Field(
        default=30, gt=0, description="Max GitHub MCP/REST calls per student before sandbox fallback"
    )


class FactorWeightsConfig(BaseModel):
    """Configuration for deterministic fusion AHP factor weights."""
    model_config = ConfigDict(extra="ignore")

    version: str = Field(default="1.0.0", description="Weights schema version")
    last_updated_by: Optional[str] = Field(default=None, description="Author or team who set these weights")
    last_updated_at: Optional[str] = Field(default=None, description="Date weights were set")
    factor_weights: Dict[str, float] = Field(
        ..., description="Weights for all 6 additive factors summing to 1.0"
    )

    @field_validator("factor_weights")
    @classmethod
    def validate_weights(cls, weights: Dict[str, float]) -> Dict[str, float]:
        missing_factors = REQUIRED_FACTORS - set(weights.keys())
        if missing_factors:
            raise ValueError(f"Missing required factor weights: {sorted(missing_factors)}")

        for factor, weight in weights.items():
            if weight <= 0.0 or weight > 1.0:
                raise ValueError(f"Factor '{factor}' weight {weight} must be in (0.0, 1.0]")

        total = sum(weights.values())
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ValueError(f"Factor weights must sum to 1.0, got {total:.6f}")

        return weights


class AppSettings(BaseModel):
    """Unified application settings container for com_agent."""
    model_config = ConfigDict(extra="ignore")

    env: str = Field(default="development", description="Execution environment ('development' | 'production')")
    is_dev_mode: bool = Field(default=True, description="True when running with mocked adapters")
    weights_config: FactorWeightsConfig = Field(..., description="Validated AHP factor weights")
    quiz_timeout: QuizTimeoutSettings = Field(..., description="Code ownership quiz timeout settings")
    github_api: GitHubAPISettings = Field(..., description="GitHub API rate limiting settings")


def load_settings(config_dir: Optional[pathlib.Path] = None) -> AppSettings:
    """Loads and validates all YAML configurations and environment variables."""
    if config_dir is None:
        config_dir = pathlib.Path(__file__).resolve().parent

    weights_file = config_dir / "weights_config.yaml"
    quiz_file = config_dir / "quiz_timeout_settings.yaml"

    if not weights_file.exists():
        raise FileNotFoundError(f"weights_config.yaml not found at {weights_file}")
    if not quiz_file.exists():
        raise FileNotFoundError(f"quiz_timeout_settings.yaml not found at {quiz_file}")

    with open(weights_file, "r", encoding="utf-8") as f:
        weights_raw = yaml.safe_load(f) or {}

    with open(quiz_file, "r", encoding="utf-8") as f:
        quiz_raw = yaml.safe_load(f) or {}

    weights_config = FactorWeightsConfig(**weights_raw)
    quiz_timeout = QuizTimeoutSettings(**(quiz_raw.get("code_ownership_quiz", {})))
    github_api = GitHubAPISettings(**(quiz_raw.get("github_api", {})))

    env_val = os.getenv("COM_AGENT_ENV", "development").lower()
    is_dev = env_val != "production"

    return AppSettings(
        env=env_val,
        is_dev_mode=is_dev,
        weights_config=weights_config,
        quiz_timeout=quiz_timeout,
        github_api=github_api,
    )


# Module-level singleton instance
settings: AppSettings = load_settings()
IS_DEV_MODE: bool = settings.is_dev_mode
