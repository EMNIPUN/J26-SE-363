"""Seeded findings with human labels (one real finding and one deliberate false positive per category)
for the later comparison of scanner-only versus scanner + LLM interpretation (RQ1)."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.agents.security_assistant.interpreter.evidence import finding_item
from app.agents.security_assistant.interpreter.models import EvidenceBundle, EvidenceItem
from app.agents.security_assistant.schemas import Finding

CASES_FILE = Path(__file__).parent / "cases.json"
# Built from pieces so no secret-looking string is stored in the repository (see cases.json).
FAKE_VALUES = {
    "{{FAKE_AWS_KEY}}": "AKIA" + "QYLPMN5HHHFPZAM2",
    "{{FAKE_AWS_SECRET}}": "Zk9xQ2v7Lm4Rt8Yp1Nc6Wd3Hs5Jb0Ga2Ue" + "+Ff7Xi",
}


@dataclass
class SeededCase:
    id: str
    ground_truth: str  # "confirmed" (real finding) or "dismissed" (deliberate false positive)
    why: str
    finding: Finding
    bundle: EvidenceBundle
    planted_secrets: tuple[str, ...]  # fake secret values present in the unredacted evidence


def load_cases() -> list[SeededCase]:
    text = CASES_FILE.read_text(encoding="utf-8")
    planted = tuple(v for k, v in FAKE_VALUES.items() if k in text)
    for placeholder, value in FAKE_VALUES.items():
        text = text.replace(placeholder, value)
    cases = []
    for raw in json.loads(text)["cases"]:
        finding = Finding.model_validate(raw["finding"])
        items = [finding_item(finding)] + [
            EvidenceItem(id=f"E{n}", kind=e["kind"], label=e["label"], content=e["content"])
            for n, e in enumerate(raw["evidence"], start=2)
        ]
        cases.append(SeededCase(raw["id"], raw["ground_truth"], raw["why"], finding, EvidenceBundle(items=items),
                                planted if "AKIA" in "".join(e["content"] for e in raw["evidence"]) else ()))
    return cases
