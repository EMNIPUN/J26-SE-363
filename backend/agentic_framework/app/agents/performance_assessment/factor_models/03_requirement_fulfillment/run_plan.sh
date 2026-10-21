#!/bin/bash
# Resumable run of the Requirement Fulfillment experiments (EXPERIMENTS.md). Safe to run again and again: finished items are skipped, and a run
# pauses by itself when the Groq account's daily token limit is reached (about 1,000,000 tokens a day for gpt-oss-120b across five keys).
#
#   RF_ENV_FILE=<dotenv file holding ASSESSMENT_GROQ_API_KEYS / ASSESSMENT_GROQ_MODEL / ASSESSMENT_GROQ_FALLBACK_MODEL> RF_PY=<python with langgraph> bash run_plan.sh [exp1 exp2 exp3 repeat]
#
# Each experiment runs from its own branch in a git worktree (default: $TMPDIR/rf_wt), so the checked-out branch of the main folder is never touched.
# Results go to <branch>/runs/<name>/ ; commit them on that branch when a stage is complete (the script does not commit).
set -u
ROOT=$(git rev-parse --show-toplevel)
SUB=backend/agentic_framework/app/agents/performance_assessment/factor_models/03_requirement_fulfillment
WT=${RF_WT:-${TMPDIR:-/tmp}/rf_wt}
PY=${RF_PY:?set RF_PY to a python with langgraph}
: "${RF_ENV_FILE:?set RF_ENV_FILE}"
export RF_ENV_FILE
export RF_WAIT=${RF_WAIT:-1}   # at the daily token limit, wait for the refill instead of stopping (the limit refills continuously)
STAGES=${*:-exp1 exp2 exp3}
PB=${RF_PER_BUCKET:-4}   # held-out tasks per size bucket; the items are nested, so raising it later only adds items (8 is the full plan)
tree() {  # tree <name> <branch>  -> path (inside a worktree) of that branch; an existing checkout of the branch is used as it is
  local have
  have=$(git -C "$ROOT" worktree list --porcelain | awk -v b="refs/heads/$2" '/^worktree /{w=substr($0,10)} /^branch /{if ($2==b) print w}' | head -1)
  if [ -n "$have" ]; then echo "$have/$SUB"; return 0; fi
  local dir="$WT/$1"
  [ -d "$dir" ] || git -C "$ROOT" worktree add -q "$dir" "$2" || { echo "cannot make a worktree for $2" >&2; return 1; }
  echo "$dir/$SUB"
}
run() {  # run <dir> <experiment> <split> <per-bucket> <out> [runs]
  (cd "$1" && "$PY" -m rf_bench.runner run --exp "$2" --split "$3" --per-bucket "$4" --out "$5" --runs "${6:-1}" --workers 5 && "$PY" -m rf_bench.runner report --out "$5" > /dev/null)
}
for s in $STAGES; do
  case $s in
    exp1) d=$(tree exp1 feature/requirement-fulfillment-single-prompt-sadeesha) || continue
          run "$d" experiments.single_prompt:SinglePromptAsProposed dev 2 runs/exp1_as_proposed_dev_smoke
          run "$d" experiments.single_prompt:SinglePromptAsProposed held_out "$PB" runs/exp1_as_proposed_heldout
          run "$d" experiments.single_prompt:SinglePromptCut held_out "$PB" runs/exp1_cut_heldout ;;
    exp2) d=$(tree exp2 feature/requirement-fulfillment-agent-experiment-sadeesha) || continue
          run "$d" experiments.agent:Agent held_out "$PB" runs/exp2_agent_heldout ;;
    exp3) d=$(tree exp3 feature/requirement-fulfillment-agent-critic-sadeesha) || continue
          run "$d" experiments.agent_critic:AgentCritic held_out "$PB" runs/exp3_critic_heldout ;;
    repeat) d=$(tree exp2 feature/requirement-fulfillment-agent-experiment-sadeesha) || continue
          run "$d" experiments.agent:Agent held_out 2 runs/exp2_agent_repeat 3 ;;
  esac
  for f in "$WT"/*/"$SUB"/runs/*/status.json; do [ -f "$f" ] && echo "$(dirname "$f" | sed "s#.*/runs/##"): $(tr -d '\n ' < "$f")"; done
done
