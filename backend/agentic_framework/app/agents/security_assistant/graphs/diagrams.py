"""Export the Mermaid diagram of every graph, generated from the compiled LangGraph graphs so they cannot drift from the code.

    python -m app.agents.security_assistant.graphs.diagrams            # write docs/*.mmd and refresh the diagram in WORKFLOW.md
    python -m app.agents.security_assistant.graphs.diagrams --check    # change nothing; exit 1 if a committed diagram is out of date

Files (in the `docs/` folder next to this package): workflow.mmd (the whole flow), orchestrator.mmd, question.mmd, governance.mmd. WORKFLOW.md
holds the workflow diagram between the markers `<!-- diagram:workflow -->` and `<!-- /diagram -->`; the command rewrites what is between them.
Rendering needs no network: the text is produced by LangGraph itself.
"""

import argparse
import sys
from pathlib import Path

from app.agents.security_assistant.graphs import assess_graph, governance_graph, orchestrator_graph, question_graph

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WORKFLOW_MD = ROOT / "WORKFLOW.md"
BEGIN, END = "<!-- diagram:workflow -->", "<!-- /diagram -->"
NOTES = {
    "workflow": "%% scan nests the orchestrator graph (orchestrator.mmd), questions nests the question graph (question.mmd), and every LLM call\n"
                "%% (interpret, trace) passes the governance gate (governance.mmd). Stage statuses live in the graph state.\n",
}
GRAPHS = {
    "workflow": assess_graph.diagram_graph,
    "orchestrator": orchestrator_graph.diagram_graph,
    "question": question_graph.diagram_graph,
    "governance": governance_graph.diagram_graph,
}


def render_all() -> dict[str, str]:
    """{name: mermaid text} for every graph."""
    return {name: build().get_graph().draw_mermaid() + NOTES.get(name, "") for name, build in GRAPHS.items()}


def workflow_block(text: str) -> str:
    return f"{BEGIN}\n```mermaid\n{text.rstrip()}\n```\n{END}"


def refreshed_workflow_md(current: str, diagram: str) -> str:
    start, end = current.index(BEGIN), current.index(END) + len(END)
    return current[:start] + workflow_block(diagram) + current[end:]


def export(docs: Path = DOCS, workflow_md: Path = WORKFLOW_MD) -> list[Path]:
    docs.mkdir(parents=True, exist_ok=True)
    texts, written = render_all(), []
    for name, text in texts.items():
        path = docs / f"{name}.mmd"
        path.write_text(text, encoding="utf-8")
        written.append(path)
    if workflow_md.exists() and BEGIN in workflow_md.read_text(encoding="utf-8"):
        workflow_md.write_text(refreshed_workflow_md(workflow_md.read_text(encoding="utf-8"), texts["workflow"]), encoding="utf-8")
        written.append(workflow_md)
    return written


def stale(docs: Path = DOCS, workflow_md: Path = WORKFLOW_MD) -> list[str]:
    """The files whose content differs from what the graphs produce now."""
    out, texts = [], render_all()
    for name, text in texts.items():
        path = docs / f"{name}.mmd"
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            out.append(str(path.name))
    if workflow_md.exists() and BEGIN in workflow_md.read_text(encoding="utf-8"):
        current = workflow_md.read_text(encoding="utf-8")
        if refreshed_workflow_md(current, texts["workflow"]) != current:
            out.append(workflow_md.name)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if a diagram is out of date")
    ap.add_argument("--out", type=Path, default=DOCS)
    ap.add_argument("--workflow-md", type=Path, default=WORKFLOW_MD)
    args = ap.parse_args(argv)
    if args.check:
        old = stale(args.out, args.workflow_md)
        print("diagrams are up to date" if not old else "out of date: " + ", ".join(old) + " (run the command without --check)")
        return 1 if old else 0
    for path in export(args.out, args.workflow_md):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
