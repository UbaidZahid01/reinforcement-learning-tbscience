# Contributor checklist (Terminal-Bench paper, app. B.1)

- [x] Checks run and passing (`static_checks.txt`); exceptions listed there.
- [x] All behaviour checked in the tests is described in the instruction (table below).
- [x] All behaviour described in the instruction is checked, except as noted below.
- [x] Tests have informative docstrings.
- [x] It is hard to cheat: separate offline verifier, unprivileged runs, hidden data (`poisoned_artifact.txt`, `agent_image_audit.txt`). An independent exploit-agent run has NOT been done.
- [ ] Instruction written by a human. **No: drafted with an AI assistant; needs the author's rewrite or disclosure.**
- [ ] Solution written by a human with minimal LLM help. **No: drafted with an AI assistant.**
- [x] Structured output schema is in the instruction.
- [x] Python dependencies pinned.
- [ ] Run with terminus-2 and a powerful model, failures analysed. **Not done.**

| instruction | test |
|---|---|
| schema, four ordered terms, finite, low <= estimate <= high | `test_outputs_valid` |
| every run succeeds, 180 s, offline, only listed libraries, writes only in OUTPUT_DIR | `test_outputs_valid` (enforced by the sandbox) |
| RMSE <= 1.7x reference, per group | `test_accuracy[0-3]` |
| coverage >= 86%, per group | `test_coverage[0-3]` |
| median width <= 1.6x reference, per group | `test_width[0-3]` |

Note: the output must be under 20 kB and a run may start at most 64 processes; neither limit is in the instruction, as no reasonable solver meets them.

# B.2 LLM-check criteria, self-reviewed (not an independent run)

| criterion | result | evidence |
|---|---|---|
| behaviour in description / in tests | pass | table above |
| docstrings | pass | `tests/test_state.py` |
| anti-cheating | pass | audit and poisoned-artifact outputs |
| schema / files named | pass | instruction |
| pinned dependencies | pass | both Dockerfiles |
| typos | pass | read through |
| tests, solution or test deps in agent image | pass | `agent_image_audit.txt` |
| hardcoded solution | pass | `solution/solver.py` computes from the files |

# Known limits

- Runs that overlap in time could still talk over loopback, abstract sockets or live SysV IPC; files are blocked. The container does not grant the rights to unshare these. Datasets are independent, so the gain would be pooling group-level corruption parameters.
- Coverage gates are estimates from 120 intervals: standard error about 0.02-0.03. A correct solver near 0.90 true coverage in group 2 can miss 0.86 by chance (roughly 5-10% per fresh dataset draw); on the fixed hidden data the outcome of a deterministic solver does not vary.
- Group 0 does not separate simplified joint models from the full one.
- Human expert review and the paper's two auditors are outstanding.
