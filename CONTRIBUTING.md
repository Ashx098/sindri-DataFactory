# Contributing to Sindri Factory

## Change classes
- **Local implementation**: behavior already defined by accepted contracts/ADRs.
- **Cross-component interface**: changes schemas or dependencies; requires design review.
- **Architecture/security/authority change**: requires ADR before implementation.
- **Experiment**: may live behind a feature flag or `experiments/` adapter; cannot silently become production default.

## Standard workflow
1. Create or claim a task packet.
2. Create branch/worktree from the recorded base commit.
3. Read root and local agent instructions.
4. Implement the smallest coherent change.
5. Add tests before integration.
6. Update docs according to the documentation matrix.
7. Run local quality gates.
8. Open a PR with evidence and explicit non-goals.
9. Resolve review findings; do not hide failures.
10. Merge only after required owners and CI pass.

## Branch names
Use `type/TASK-ID-short-description`, e.g. `feat/SIN-P1.4-003-verilator-lint-adapter`. Task IDs follow `SIN-P<phase>.<subphase>-<nnn>` (bootstrap work uses `SIN-B0.<n>-<nnn>`); create packets with `scripts/new_task.py`.

## Commit style
Prefer small conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `build:`, `chore:`. Include the task ID when practical.

## Pull-request size
Prefer reviewable units. Cross-cutting migrations may be large but should be split into preparatory, migration, and cleanup PRs where possible.

## Review standard
Reviewers check behavior, architecture boundaries, tests, evidence/replay impact, security/data boundaries, docs, and migration compatibility — not only code style.
