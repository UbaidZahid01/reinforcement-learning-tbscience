# Task 02: `linked-file-regression`

TB-Science task in Harbor format, `mathematical-sciences/statistics`: estimate a regression with valid 95% intervals when covariates and outcome are in two files joined only by error-prone identifiers.

| item | result |
|---|---|
| Task | [`tasks/mathematical-sciences/statistics/linked-file-regression`](tasks/mathematical-sciences/statistics/linked-file-regression) |
| Harbor oracle / no-op | see `validation/` and below |
| Independent correct solver | passes all groups (calibration data) |
| Defective methods | 8 of 8 fail overall |
| Isolation test | 13 attacks denied, reward 0 ([`qc/poisoned_artifact.txt`](qc/poisoned_artifact.txt)) |
| Similarity, 186 upstream instructions | max 31% (limit 80%) |
| Static checks | [`qc/static_checks.txt`](qc/static_checks.txt) |
| Checklists and known limits | [`qc/contributor_checklist.md`](qc/contributor_checklist.md) |

## Do not publish

`tests/datasets/` (with the truth) is git-ignored and exists only on the author's machine, so a clone cannot build the verifier. The parent GitHub repository is public and agents have internet access: keep this branch, which also holds the solver and generator, off public remotes.

## Outstanding

- Author identity and relevant experience in `task.toml` (placeholders); approved TB-Science proposal.
- Instruction and solution were AI-drafted: rewrite or disclose.
- Frontier-model trials, exploit agent, debug tool, human review.

## Reproduce (from the repository root)

```bash
harbor run -p task02/tasks/mathematical-sciences/statistics/linked-file-regression -a oracle
harbor run -p task02/tasks/mathematical-sciences/statistics/linked-file-regression -a nop
```
