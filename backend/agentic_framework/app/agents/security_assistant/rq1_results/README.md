# Recorded RQ1 comparison (vuln_py_repo only)

Produced by `python -m app.agents.security_assistant.rq1 --repo vuln_py_repo=<findings.json>,<interpreted.json>` from one saved live run
on the synthetic Python demo repository: scan without CodeQL (`vuln_py_repo_fast`, 33 findings), interpreted by
`openai/gpt-oss-120b` with prompt `interpreter-v3` at temperature 0 (16 confirmed, 15 dismissed, 2 uncertain).

- Only this repository has a saved scan and LLM run. The JS and Java repositories need CodeQL and a Docker image to scan and
  have not been run: their rows are empty on purpose.
- The "deliberate false positives" suite has scanner-only numbers; it has no LLM numbers because no live run of
  `interpreter.evaluate_seeded --live --save` has been made (run it, then pass `--seeded-results`).
- Reading the Python row: every scanner finding matches a planted bug (precision 1.0 both ways), so the LLM cannot raise precision
  here. It dismissed 15 dependency advisories; they match a planted bug only by file, so this ground truth cannot say whether the
  dismissals were right. Treat this row as a recorded measurement, not as evidence that the LLM helps or hurts.
