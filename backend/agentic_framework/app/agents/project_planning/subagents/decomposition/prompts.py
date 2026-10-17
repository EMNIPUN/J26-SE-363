"""Prompts for the Decomposition sub-agent.

Only coverage.py and invest.py make LLM calls (one each, regardless of story
count) — the gate decision, 0-4 score, and student feedback are all computed
in code from their structured output (see gate.py / scorer.py). This file is
intentionally near-empty: there is no scorer or reflect prompt anymore (see
scorer.py's module docstring for why they were removed).
"""

from __future__ import annotations
