"""Factor weights configuration bridge.

Strictly aligned with:
- BOARD.md T3.2 (T3.2.1, T3.2.2)
- PLAN.md Section 12.5
"""

from typing import Dict
from app.agents.performance_assessment.com_agent.config.settings_loader import (
    settings,
    FactorWeightsConfig,
)


def load_weights() -> FactorWeightsConfig:
    """Thin wrapper around settings.weights_config."""
    return settings.weights_config


def get_weights_as_dict() -> Dict[str, float]:
    """Flat dict of factor weights for calculator and fusion engine."""
    return dict(settings.weights_config.factor_weights)
