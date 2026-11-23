# TB-Science task: `medium-baseline-rtk`

This repo contains one Terminal-Bench-Science task in Harbor format, along with its QC evidence and agent trajectories. It is laid out like the upstream repo: `tasks/<domain>/<field>/<task>`.

| | |
|---|---|
| Task | [`tasks/earth-sciences/geosciences/medium-baseline-rtk`](tasks/earth-sciences/geosciences/medium-baseline-rtk) |
| Deliverable | `/root/results/solver.py`, a self-contained dual-frequency GPS kinematic RTK solver, run offline on 4 hidden RINEX sessions |
| Oracle / nop (Harbor, docker) | **1.0 / 0.0** |
| Similarity check (TB-Science pipeline, 96 public tasks) | max **56%** (threshold 80%), against the intended variant parent only |

## 1. Domains chosen

1. **Earth sciences: geodesy** (GNSS positioning, reference frames, atmospheric delays)
2. **Engineering sciences: electrical engineering** (navigation signals, receiver clocks, Doppler and carrier tracking)
3. **Mathematical sciences: estimation** (Kalman filtering, integer least squares, LAMBDA decorrelation)

The task sits where all three meet. Carrier-phase RTK is a geodetic measurement problem, built on receiver and signal engineering, and solved by mixed integer and real estimation.

## 2. Variant design: what it is a variant of, and why pipelines don't flag it

**Parent:** `engineering-sciences/electrical-engineering/navigation-sensor-calibration`, the only public task touching GNSS. Its agent writes a reusable `solver.py` that the verifier runs on hidden navigation sessions; it fuses already-computed GNSS positions with IMU and LiDAR, and solves for calibration and trajectory.

**This task keeps the shell and changes the science.** The shell is the same: a reusable solver, run on hidden sessions, graded on trajectory accuracy. But the inputs here are raw dual-frequency code and carrier phase in RINEX, not positions. The core problem is integer ambiguity resolution: double differencing, LAMBDA, wide-lane to narrow-lane, ionosphere-weighted estimation, cycle-slip detection and repair, and handling receiver clock resets. None of this appears in the parent, which never sees a carrier phase.

| check | result |
|---|---|
| `ci_checks/check-similarity.py` (TF-IDF 1-2-gram cosine, the upstream pipeline) vs all public `tasks/` + `lite/` | **56%** with the parent; threshold 80% |
| next most similar public task | 17.6% (`eeg-erp-recovery`) |
| grep of all public instructions for gnss, rinex, carrier phase, ambiguity | only the parent (GNSS positions only) and one false hit |

Output in [`qc/similarity.txt`](qc/similarity.txt).

## 3. QC: static checks (upstream `ci_checks/`)

All structural, format and security checks pass ([`qc/static_checks.txt`](qc/static_checks.txt)):
canary, task-structure, task-fields, task-slug, task-path, task-readme (section caps: 362/600, 156/300, 454/700 words), task-timeout (28800), instruction-suffix, absolute-path, dockerfile-sanity/platform/references, pip-pinning, pytest-version, separate-verifier, verifier-resources, verifier-tooling-baked, binary-reward (static and from real trials), test-sh-sanity, nproc, allow-internet, compose-host-binds, gpu-types, trial-network-fetch, test-file-references, verifier-output (oracle and nop trials).

Not runnable locally:
- `check-ai-detection` needs a GPTZero key (see the note at the end).
- `check-task-proposal-link` needs a PR body that links an approved proposal.

## 4. QC: implementation rubric (40 criteria), self-review

| criterion | status | evidence |
|---|---|---|
| verifiable / deterministic_reproducible | ✅ | fixed data bytes (sha256 at build), deterministic oracle; in-container metrics match local runs to 4 decimals |
| well_specified / structured_data_schema | ✅ | exact CSV schema, epoch and time convention (reception instant), status semantics, execution contract (offline, pinned libs, 600 s, write only in OUTPUT_DIR), every gating metric |
| test_instruction_alignment | ✅ | 4 metrics + format in the instruction ↔ 5 tests × 4 sessions |
| solvable / solution_quality | ✅ | oracle 1.0 via Harbor; the full EKF+LAMBDA solver computes everything from RINEX |
| difficult / essential_difficulty | ✅ | medium-baseline AR with ionosphere, unflagged slips, clock resets; RTKLIB 2.4.3 fails 2 of 4 sessions even when tuned |
| novel | ⚠️ reviewer judgement | RTK is a known problem, but the offline self-contained constraint, medium-baseline physics and data defects defeat off-the-shelf configs |
| scientifically_grounded / scope | ✅ | geodetic post-processing; filed under geosciences/geodesy |
| outcome_verified / functional_verification | ✅ | runs the submitted solver and grades positions against truth, no source inspection |
| anti_cheat_robustness / verifier_execution_isolation | ✅ | setpriv uid 65534 with no-new-privs; `/tests` and `/logs/verifier` root-only (700); output via temp files; every uid process killed per session; poisoned-artifact test scores 0 |
| ground_truth_provenance | ✅ | truth is the generator's trajectory, independent of the oracle |
| graded_instances_discriminate | ✅ | trivial nulls fail every session individually |
| threshold calibration | ✅ | two structurally different correct solvers pass; 8 defective approaches fail (table in task README) |
| separate_verifier_configured / artifact_efficiency | ✅ | single artifact (`solver.py`); hidden data baked into the verifier image |
| environment_hygiene | ✅ | no tests or solution in the agent image; pinned pip; slim base |
| ctrf_reporting | ✅ | `--ctrf /logs/verifier/ctrf.json`, 20 parametrized cases |
| task_authoring_dir / no_extraneous_files | ✅ | generator, comparators, ablations and poison test live under `authoring/` |
| resource_configuration | ✅ | 2 CPU / 4 GB; verifier 3000 s = 4 × 600 s; oracle ~90 s per session |
| task_toml_schema / category_and_tags / task_name | ✅ | template fields only |
| difficulty/solution/verification explanations, task_readme | ✅ | under the caps; calibration table |
| author fields | ❗ **you must fill in** | `author_name`, `author_email`, `author_profile`, `relevant_experience` are placeholders |

## 5. Trajectories

See [`trajectories/`](trajectories/) and §6. Run them with `scripts/run_gemini_trials.sh` (terminus-2 + Gemini, `max_turns` cap for the free tier).

## 6. Trajectory results

Agent: Harbor `terminus-2`, `max_turns=60`, one trial at a time. **The free Gemini key allows 20 requests per model per day** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quota 20), so every run was cut off at about 20 steps. Pro and 4.x models have quota 0 on a free key.

| model | trial | steps | reward | what happened | failure valid? |
|---|---|---|---|---|---|
| gemini-2.5-flash | Bx7EFHD | 21 | 0 | still debugging its own RINEX header and epoch parser (column slicing); `main()` wrote a placeholder header-only CSV; then 429 | graded correctly (0 rows); run truncated, so not difficulty evidence |
| gemini-2.5-flash | kixxmbc | 2 | 0 | 429 after 2 steps, no solver | quota; not a task signal |
| gemini-3.5-flash | WAaptuF | 24 | 0 | stuck writing files through shell quoting, no solver; then 429 | quota and agent tooling; not a task signal |
| gemini-3.5-flash | Sxg5YkP | 1 | 0 | 429 on its first call, then waited until the agent timeout | quota; not a task signal |
| gemini-3-flash-preview | gsmxuic | 13 | 0 | wrote a 212-line **L1-only float** solver (no ionosphere, no ambiguity resolution); positions diverge to 1e24 m, fix rate 0 on all sessions | **valid scientific failure** (re-verified in the verifier image: 149 s, 7 format passed / 13 metric failed, `reverify_standalone_verifier.txt`) |
| gemini-3-flash-preview | zfnQXnY | 0 | none | no solver produced, Harbor artifact copy error | quota; not a task signal |

The one completed attempt (gsmxuic) failed in exactly the way the task is designed to catch: a single-frequency, ionosphere-free float approach cannot fix ambiguities at medium baselines. Its Harbor verifier phase reported a timeout because it ran while other trial jobs shared the Docker host. The same artifact in the same verifier image with 2 CPUs and 4 GB completes in 149 s with reward 0.

**To get full trajectories:** rerun after the daily quota resets, with a paid Gemini key, or with a frontier agent (`claude-code` / `codex`). TB-Science calibrates on frontier models, not Flash.

## Reproduce

```bash
uv tool install harbor
harbor run -p tasks/earth-sciences/geosciences/medium-baseline-rtk -a oracle   # 1.0
harbor run -p tasks/earth-sciences/geosciences/medium-baseline-rtk -a nop      # 0.0
GEMINI_API_KEY=... bash scripts/run_gemini_trials.sh
```
