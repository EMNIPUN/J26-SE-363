"""Shared machinery of the three bounded agent loops (orchestrator, question agent, governance).

An agent here is: it SELECTS the next action from a list, keeps STATE between steps, and LOOPS until a goal is met or a budget is spent.
The constraints that keep it safe are in code, not in a prompt:

- The actions are a fixed vocabulary per component. In every step the component computes the list of actions that are valid in the
  current state (`options`); a policy may only choose from that list. A choice outside it is REJECTED, recorded, and replaced by the
  deterministic rule policy. There is no free-form command, no shell, and no action that is not in the list.
- Steps and retries are capped by configuration (`LoopConfig`, environment variables); when the budget is spent the loop stops and says so.
- A policy is swappable: anything with `choose(state, options) -> (Action, reason)`. The default policies are deterministic rules; an LLM
  policy would receive the same state summary and the same options and could only return one of them.
- Every decision goes to the audit log (`agent_decision` events) and to a decision trail that is rendered into the report.
"""

import os
from dataclasses import dataclass, field
from typing import Protocol


class DisallowedAction(ValueError):
    """A policy chose an action that is not in the list of valid options."""


@dataclass(frozen=True)
class Action:
    """One action from a component's fixed vocabulary. `why` is the reason the component offers it (computed in code)."""

    name: str
    target: str | None = None
    why: str = ""

    @property
    def key(self) -> str:
        return f"{self.name}:{self.target}" if self.target else self.name


class Policy(Protocol):
    name: str

    def choose(self, state: dict, options: list[Action]) -> tuple[Action, str]:
        """Pick one of `options` and say why. `state` is a small JSON-serialisable summary."""
        ...


class RulePolicy:
    """The default: the options are listed in priority order by the component, so the rule is 'take the first'."""

    name = "rules"

    def choose(self, state: dict, options: list[Action]) -> tuple[Action, str]:
        return options[0], options[0].why


@dataclass
class LoopConfig:
    """Budgets of one loop. `max_steps` counts decisions (the final stop included); `max_retries` is per tool or per finding."""

    max_steps: int
    max_retries: int

    @classmethod
    def from_env(cls, prefix: str, max_steps: int, max_retries: int) -> "LoopConfig":
        def number(name: str, default: int) -> int:
            for key in (f"SECURITY_ASSISTANT_{prefix}_{name}", f"SECURITY_ASSISTANT_AGENT_{name}"):
                try:
                    if os.environ.get(key):
                        return max(0 if name == "MAX_RETRIES" else 1, int(os.environ[key]))
                except ValueError:
                    pass
            return default

        return cls(max_steps=number("MAX_STEPS", max_steps), max_retries=number("MAX_RETRIES", max_retries))


def select(policy: Policy, fallback: Policy, state: dict, options: list[Action]) -> tuple[Action, str, dict | None]:
    """Let `policy` choose, validated in code. Returns (action, reason, rejected) where `rejected` describes a choice that was refused
    (outside the options, or the policy failed) and replaced by `fallback`. `options` must not be empty."""
    if not options:
        raise ValueError("a loop needs at least one valid option (a stop action is always valid)")
    valid = {a.key: a for a in options}
    try:
        chosen, reason = policy.choose(state, list(options))
    except Exception as exc:  # a broken policy must not stop the loop or free it
        action, why = fallback.choose(state, list(options))
        return action, why, {"policy": policy.name, "error": type(exc).__name__}
    if not isinstance(chosen, Action) or chosen.key not in valid:
        action, why = fallback.choose(state, list(options))
        return action, why, {"policy": policy.name, "proposed": getattr(chosen, "key", str(chosen))[:80],
                             "problem": "not one of the valid options"}
    return valid[chosen.key], reason or valid[chosen.key].why, None


@dataclass
class DecisionTrail:
    """The ordered decisions of one loop. Written to the audit log as they happen and rendered into the report."""

    component: str
    audit: object | None = None  # an AuditLog (governance.AuditLog) or None
    entries: list[dict] = field(default_factory=list)

    def record(self, step: int, policy: str, state: dict, options: list[Action], chosen: Action, reason: str,
               rejected: dict | None = None, subject: str | None = None) -> dict:
        entry = {"component": self.component, "step": step, "subject": subject, "policy": policy, "state": state,
                 "options": [a.key for a in options], "chosen": chosen.key, "reason": reason, "rejected": rejected, "outcome": None}
        self.entries.append(entry)
        return entry

    def outcome(self, entry: dict, text: str) -> None:
        """Attach what the action did, then write the whole decision to the audit log (one line per decision)."""
        entry["outcome"] = text
        if self.audit is not None:
            self.audit.record("agent_decision", **{k: v for k, v in entry.items()})


def render_trail(trails: dict[str, list[dict]]) -> str:
    """The 'Decision trail' section of a report: one table per loop that made decisions."""
    M = ["## Decision trail", "",
         "> Each agent loop chooses its next action from a fixed list that the code validates, keeps state between steps, and stops at its goal "
         "or when its budget is spent. Every decision below is also a line in `audit.jsonl`. The default policy is a set of deterministic rules; "
         "a choice outside the valid options is rejected and shown here.", ""]
    shown = False
    for component, entries in trails.items():
        if not entries:
            continue
        shown = True
        M += [f"### {component}", "", "| step | subject | policy | chosen | why | result |", "|---|---|---|---|---|---|"]
        for e in entries:
            chosen = e["chosen"] + (f" (rejected {e['rejected'].get('proposed', e['rejected'].get('error', '?'))}, rules used)" if e.get("rejected") else "")
            cells = [str(e["step"]), e.get("subject") or "-", e["policy"], f"`{chosen}`", e["reason"], e.get("outcome") or "-"]
            M.append("| " + " | ".join(" ".join(str(c).split()).replace("|", "\\|") for c in cells) + " |")
        M.append("")
    if not shown:
        M.append("No agent loop made a decision in this run.")
    return "\n".join(M) + "\n"
