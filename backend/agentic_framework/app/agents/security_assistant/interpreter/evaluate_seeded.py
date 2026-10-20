"""Run the Semantic Interpreter on the seeded set and print status versus the human label.

    uv run python -m app.agents.security_assistant.interpreter.evaluate_seeded            # offline, mock oracle
    uv run python -m app.agents.security_assistant.interpreter.evaluate_seeded --live     # real Groq call (needs the key and model in .env)

The offline mode answers with the human label, so it only checks the plumbing. It says nothing about the
model: only --live produces numbers for the RQ1 comparison (scanner only: every seeded finding counts as
reported, so its precision is the share of real ones).
"""

import argparse
import asyncio
import json
import sys

from app.agents.security_assistant.interpreter.interpreter import SemanticInterpreter
from app.agents.security_assistant.interpreter.llm import LLMError, get_default_client
from app.agents.security_assistant.interpreter.seeded import SeededCase, load_cases


class OracleClient:
    """Mock model that returns the human label. NOT a model result."""

    model = "mock-oracle"

    def __init__(self, cases: list[SeededCase]):
        self.current: SeededCase | None = None

    async def complete(self, system: str, user: str) -> str:
        c = self.current
        return json.dumps({"status": c.ground_truth, "rationale": "oracle answer from the seeded label",
                           "evidence_ids": ["E1", "E2"], "confidence": 1.0})


async def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="call the real LLM (needs SECURITY_ASSISTANT_LLM_API_KEY and SECURITY_ASSISTANT_LLM_MODEL)")
    args = ap.parse_args(argv)

    cases = load_cases()
    if args.live:
        try:
            client = get_default_client()
        except LLMError as exc:
            print(f"cannot run live: {exc}")
            return 2
    else:
        client = OracleClient(cases)
    interpreter = SemanticInterpreter(client)

    print(f"model: {client.model}{'  (mock: answers with the human label)' if not args.live else ''}")
    correct = errors = 0
    for case in cases:
        if not args.live:
            client.current = case
        result = await interpreter.interpret(case.finding, case.bundle)
        ok = result.status == case.ground_truth
        correct += ok
        errors += bool(result.error or result.output_rejected)
        flags = " ".join(f for f, on in (("downgraded", result.downgraded), ("rejected", result.output_rejected),
                                         ("llm-error", bool(result.error))) if on)
        print(f"{case.finding.category.value} {case.id:<38} truth={case.ground_truth:<9} got={result.status:<9} "
              f"conf={result.confidence:.2f} {'ok ' if ok else 'MISS'} {flags}")
        if result.error or result.output_rejected:
            print(f"     reason: {(result.error or result.rationale)[:200]}")
    print(f"agreement with the labels: {correct}/{len(cases)}; calls that failed or were rejected: {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
