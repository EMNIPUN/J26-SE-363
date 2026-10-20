# Recorded RQ1 comparison (verification run, 2026-10-20)

Produced by `python -m app.agents.security_assistant.rq1` from the verification phase:

- **Scanner-only** columns: full scans with CodeQL (Docker image) of the four synthetic demo repositories (`vuln_py_repo`, `vuln_js_repo`,
  `vuln_java_repo`, `vuln_java_gradle_repo`), ground truth `tools/tests/fixtures/PLANTED_BUGS.md`.
- **+LLM** columns for Python and JS: `assess` runs (`openai/gpt-oss-120b`, prompt `interpreter-v3`, temperature 0) over those scans.
  Java and Gradle have **no LLM columns**: their `assess` run hit Groq's daily token limit (200,000 tokens per day) after 11 of 36 calls, so
  most findings came back "uncertain" because of the quota, not because of the model. That run is not a measurement and is not used.
- **Deliberate false positives** (`interpreter/seeded/cases.json`): a live run of `interpreter.evaluate_seeded --live` with `gpt-oss-120b`, 10 of 10 cases.

How to read it (strict, and honest about what the ground truth cannot judge):

- "fp" means "not in PLANTED_BUGS.md". The one JS false positive is CodeQL's `js/missing-rate-limiting` on the route that runs a command: a
  real but unplanted weakness.
- Dependency advisories match a planted bug on the file only, so the ground truth cannot say whether dismissing one advisory of a planted
  vulnerable package was right. `llm_dismissed_file_only` counts those separately: 15 of 15 for Python and 12 of 13 for JS.
- The JS row's lost recall (8 of 10 planted bugs found after the LLM) is two bugs: all 12 lodash/express advisories were dismissed (the model
  saw that `server.js` never imports lodash) and the hard-coded JWT signing key `'key'` was dismissed as "a generic placeholder".
- On the seeded false positives the LLM removed all 5 look-alikes and kept all 5 real problems (precision 0.5 -> 1.0). On the demo repos
  the scanners have almost no false positives to remove, so the LLM cannot raise precision there; it can only lose recall.
