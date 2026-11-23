#!/usr/bin/env bash
# Run step-capped Gemini trajectories on the task with Harbor's terminus-2 agent.
# Needs GEMINI_API_KEY in the environment (free key: https://aistudio.google.com/apikey).
# Free-tier rate limits are low, so trials run one at a time with a turn cap.
#   MODEL=gemini/gemini-2.5-flash N=3 TURNS=60 bash task02/scripts/run_gemini_trials.sh
set -euo pipefail
: "${GEMINI_API_KEY:?set GEMINI_API_KEY first}"
MODEL="${MODEL:-gemini/gemini-2.5-flash}"
N="${N:-5}"
TURNS="${TURNS:-60}"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
harbor run \
  -p task02/tasks/mathematical-sciences/statistics/linked-file-regression \
  -a terminus-2 -m "$MODEL" \
  --ak max_turns="$TURNS" \
  -k "$N" -n 1 \
  -o "task02/trajectories/$(echo "$MODEL" | tr '/' '_')_turns${TURNS}"
