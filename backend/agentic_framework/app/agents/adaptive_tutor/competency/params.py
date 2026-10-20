"""Baseline BKT parameter configuration.

These defaults are fixed research baselines, not trained or optimized values.
"""

from app.agents.adaptive_tutor.schemas import BktParameters

DEFAULT_BKT_PARAMETERS = BktParameters(
    p_l0=0.2,
    p_t=0.1,
    p_g=0.2,
    p_s=0.1,
)

DEFAULT_CORRECT_THRESHOLD = 0.5
