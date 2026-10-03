"""Unit tests for weights_config.yaml verification (T0.2.1)."""

import pathlib
import yaml
import pytest
import math

CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "weights_config.yaml"

def test_weights_config_exists_and_parses():
    assert CONFIG_PATH.exists(), f"weights_config.yaml not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "YAML root must be a mapping"
    assert "version" in data, "Missing 'version' field"
    assert "last_updated_by" in data, "Missing 'last_updated_by' field"
    assert "last_updated_at" in data, "Missing 'last_updated_at' field"
    assert "factor_weights" in data, "Missing 'factor_weights' field"

def test_weights_config_exact_factors():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    weights = data["factor_weights"]
    expected_factors = {
        "effort": 0.20,
        "consistency": 0.15,
        "requirement_fulfillment": 0.25,
        "collaboration": 0.15,
        "task_complexity": 0.10,
        "code_ownership": 0.15,
    }
    assert set(weights.keys()) == set(expected_factors.keys()), "Factor keys do not match expected 6 factors"
    for factor, expected_val in expected_factors.items():
        assert math.isclose(weights[factor], expected_val, rel_tol=1e-5), f"Weight mismatch for {factor}: {weights[factor]} != {expected_val}"

def test_weights_config_sum_to_one():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    weights = data["factor_weights"]
    total = sum(weights.values())
    assert math.isclose(total, 1.0, rel_tol=1e-6), f"Sum of weights must be 1.0, got {total}"
    for factor, val in weights.items():
        assert 0.0 < val <= 1.0, f"Factor {factor} weight {val} out of bounds (0, 1]"

def test_weights_bridge_load_weights():
    from app.agents.performance_assessment.com_agent.fusion_engine.weights_config import (
        load_weights,
        get_weights_as_dict,
    )
    from app.agents.performance_assessment.com_agent.config.settings_loader import FactorWeightsConfig

    cfg = load_weights()
    assert isinstance(cfg, FactorWeightsConfig)
    assert cfg.version == "1.0.0"

    w_dict = get_weights_as_dict()
    assert isinstance(w_dict, dict)
    assert len(w_dict) == 6
    assert sum(w_dict.values()) == pytest.approx(1.0, rel=1e-6)
    assert "effort" in w_dict
    assert "code_ownership" in w_dict

