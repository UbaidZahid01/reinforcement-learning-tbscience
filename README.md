# TB-Science task: `medium-baseline-rtk`

This repo contains one Terminal-Bench-Science task in Harbor format, along with its QC evidence and agent trajectories. It is laid out like the upstream repo: `tasks/<domain>/<field>/<task>`.

| | |
|---|---|
| Task | [`tasks/earth-sciences/geosciences/medium-baseline-rtk`](tasks/earth-sciences/geosciences/medium-baseline-rtk) |
| Deliverable | `/root/results/solver.py`, a self-contained dual-frequency GPS kinematic RTK solver, run offline on 4 hidden RINEX sessions |
| Oracle / nop (Harbor, docker) | **1.0 / 0.0** on the current package ([`validation/oracle/2026-11-24__21-13-36`](validation/oracle/2026-11-24__21-13-36), [`validation/nop/2026-11-24__21-12-11`](validation/nop/2026-11-24__21-12-11)); the older runs in `validation/` belong to earlier versions of the package |
| Similarity check (TB-Science pipeline, 97 public tasks) | max **53%** (threshold 80%), against the intended variant parent only |

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
| `ci_checks/check-similarity.py` (TF-IDF 1-2-gram cosine, the upstream pipeline) vs all public `tasks/` + `lite/` | **53%** with the parent; threshold 80% |
| next most similar public task | 15.9% (`eeg-erp-recovery`) |
| grep of all public instructions for gnss, rinex, carrier phase, ambiguity | only the parent (GNSS positions only) and one false hit |

Output in [`qc/similarity.txt`](qc/similarity.txt).

## 3. QC: static checks (upstream `ci_checks/`)

All structural, format and security checks pass ([`qc/static_checks.txt`](qc/static_checks.txt)):
canary, task-structure, task-fields, task-slug, task-path, task-readme (words of prose against the section caps: 390/600, 156/300, 563/700), task-timeout (28800), instruction-suffix, absolute-path, dockerfile-sanity/platform/references, pip-pinning, pytest-version, separate-verifier, verifier-resources, verifier-tooling-baked, binary-reward (static and from real trials), test-sh-sanity, nproc, allow-internet, compose-host-binds, gpu-types, trial-network-fetch, test-file-references, verifier-output (oracle and nop trials).

Not runnable locally:
- `check-ai-detection` needs a GPTZero key.
- `check-task-proposal-link` needs a PR body that links an approved proposal.

## 4. QC: implementation rubric (40 criteria), self-review

| criterion | status | evidence |
|---|---|---|
| verifiable / deterministic_reproducible | ✅ | fixed data bytes (sha256 at build), deterministic oracle; in-container metrics match local runs to 4 decimals |
| well_specified / structured_data_schema | ✅ | exact CSV schema, epoch and time convention (reception instant), status semantics, execution contract (offline, pinned libs, 600 s, write only in OUTPUT_DIR), every gating metric |
| test_instruction_alignment | ✅ | 4 metrics + format + writes only in `OUTPUT_DIR` in the instruction ↔ 6 tests × 4 sessions |
| solvable / solution_quality | ✅ | oracle 1.0 via Harbor; the full EKF+LAMBDA solver computes everything from RINEX |
| difficult / essential_difficulty | ✅ / unproven | medium-baseline AR with ionosphere, unflagged 9/7 and 77/60 slips, clock resets; classical MW/geometry-free slip detection fails all 4 sessions. No valid strong-model run exists yet, so difficulty for models is not demonstrated |
| novel | reviewer judgement | RTK is a known problem with public engines; the single-file offline contract and the injected data defects raise the bar, and no claim is made that off-the-shelf tools fail |
| scientifically_grounded / scope | ✅ | geodetic post-processing; filed under geosciences/geodesy |
| outcome_verified / functional_verification | ✅ | runs the submitted solver and grades positions against truth, no source inspection |
| anti_cheat_robustness / verifier_execution_isolation | ✅ | setpriv to an unprivileged uid with no-new-privs; output directory is the only writable place, and writes elsewhere are searched for after each run; `/tests` and `/logs/verifier` root-only (700); output via temp files; every uid process killed per session; poisoned-artifact test scores 0 |
| ground_truth_provenance | ✅ | truth is the generator's trajectory, independent of the oracle |
| graded_instances_discriminate | ✅ | every defective approach in the calibration table fails every session individually |
| threshold calibration | ✅ | two structurally different correct solvers pass; 8 defective approaches fail every session (table in task README; one further row, clock resets ignored in the Doppler slip test only, passes) |
| separate_verifier_configured / artifact_efficiency | ✅ | single artifact (`solver.py`); hidden data baked into the verifier image |
| environment_hygiene | ✅ | no tests or solution in the agent image; pinned pip; slim base |
| ctrf_reporting | ✅ | `--ctrf /logs/verifier/ctrf.json`, 24 separate entries (6 checks × 4 sessions) |
| task_authoring_dir / no_extraneous_files | ✅ | generator, comparators, ablations and poison test live under `authoring/` |
| resource_configuration | ✅ | 2 CPU / 4 GB; verifier 3000 s covers 4 × 600 s plus grading; oracle 130 s for all four sessions in the verifier |
| task_toml_schema / category_and_tags / task_name | ✅ | template fields only |
| difficulty/solution/verification explanations, task_readme | ✅ | under the caps; calibration table |
| author fields | ✅ | filled in by the author; no professional GNSS background is claimed |

## 5. Trajectories

See [`trajectories/`](trajectories/) and §6. Run them with `scripts/run_gemini_trials.sh` (terminus-2 + Gemini, `max_turns` cap for the free tier).

## 6. Trajectory results

Agent: Harbor `terminus-2`, `max_turns=60`, one trial at a time, seven trials in total. **All seven ran on an earlier version of the package** (20 tests, other session data, old instruction), so they are not evidence about the current one. **The free Gemini key allows 20 requests per model per day** (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quota 20); Pro and 4.x models have quota 0 on a free key.

| model | trial | agent steps | official reward | what happened | what it shows |
|---|---|---|---|---|---|
| gemini-2.5-flash | Bx7EFHD | 20 | 0 | still debugging its own RINEX parser; wrote a header-only CSV; then 429 | truncated by quota |
| gemini-2.5-flash | kixxmbc | 1 | 0 | 429, no solver | truncated by quota |
| gemini-2.5-flash | VbSMoEy | 0 | none | 429 on the first call, no solver | truncated by quota |
| gemini-3.5-flash (recorded as served by gemini-3.6-flash) | WAaptuF | 23 | 0 | stuck writing files through shell quoting, no solver; then 429 | quota and agent tooling |
| gemini-3.5-flash | Sxg5YkP | 0 | 0 | one API call that lasted 3.0 h, then the agent timeout; the 8 h agent phase took 12.7 h of wall time, so the host was probably suspended | infrastructure |
| gemini-3-flash-preview | gsmxuic | 12 | none (verifier timeout) | wrote a 212-line L1-only float solver whose positions diverge to 1e24 m | a numerically broken solver |
| gemini-3-flash-preview | zfnQXnY | 0 | none | "Failed to start tmux session"; no model call was made | infrastructure |

For `gsmxuic` the verifier phase ran from 22:50 to 01:52 against a 3000 s limit; the cause was not established. A later ad hoc run of the same artifact in the verifier image of that time took 149 s and scored 0, with 13 of 20 tests failed (`reverify_standalone_verifier.txt`). The 7 passes are the 4 format tests and 3 wrong-fix tests that pass because no epoch is labelled fixed. The positions diverge numerically, so the run does not show that ambiguity resolution was the obstacle.

**None of these runs is evidence of scientific difficulty.** To get it, rerun on the current package after the daily quota resets, with a paid Gemini key, or with a frontier agent (`claude-code` / `codex`). TB-Science calibrates on frontier models, not Flash.

## 7. Internet access

The verifier, which runs the submitted solver, has no network (`network_mode = "no-network"` in `[verifier.environment]`). The agent phase is `public` because the upstream check `check-allow-internet.sh` rejects anything else. Disabling it for the agent would fail that check. The author asked for internet to be disabled; this is as far as the benchmark allows.

Because the agent can reach the internet, the hidden truth, the generator seeds and the reference solver must not be publicly reachable: keep this repository private. Data published with an earlier version of this task must be treated as exposed; the current sessions use other trajectories, noise and events.

## Reproduce

```bash
uv tool install harbor
harbor run -p tasks/earth-sciences/geosciences/medium-baseline-rtk -a oracle   # 1.0
harbor run -p tasks/earth-sciences/geosciences/medium-baseline-rtk -a nop      # 0.0
GEMINI_API_KEY=... bash scripts/run_gemini_trials.sh
```
