"""Single place where a governance check can be attached later. It does nothing today."""

from typing import Any


def governance_hook(event: str, data: dict[str, Any]) -> None:
    """Called by the interpreter with event "pre_llm" (prompt about to be sent) and "post_llm" (result ready).

    A later governance check can inspect or veto here (raise to block). Currently a no-op on purpose.
    """
    return None
