# SIN-P1.1-004 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-004-candidate-manifest` at `../worktrees/SIN-P1.1-004`
- HEAD commit: the commit that adds this file
- Base commit: `62a7834` (ready-marking commit on `chore/SIN-P1.1-003-004-ready`; not yet on `main`)
- Dirty files, if any: none after commit

## Completed
- `CandidateManifest` v1 with `CandidateFile`, `ModelAuthor`, `ProducerRole`.
- `candidate_source_hash()`: the single implementation of the F3 `candidate_file_set_v1` construction.
- Contract tests and the adapted §20.3 fixture; component-contract invariants INV-CM-001…005.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 14 files |
| `uv run pytest -q` | 328 passed, 8 skipped | 64 CandidateManifest tests (after PR #11 fixes) |
| F6 fix: old over-strict episode rule restored | 1 failure | confirms the new test catches it |
| Planted bug: domain tag dropped | 15 failures | reverted |
| Planted bug: source_hash recomputation skipped | 4 failures | reverted |
| Planted bug: `training_allowed=True` default | 1 failure | reverted |

## Changed
`src/sindri/schemas/candidate.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_candidate_manifest.py`, `tests/contract/examples/candidate_manifest.json`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
None beyond F1–F8. `seed` has no range constraint (none specified).

## Review fixes (PR #11)
- F6 corrected: solver requires `episode_id`, reconstructor forbids it, and architecture_explorer has it optional (oracle-side `None`, solver-side episode recorded). Both explorer modes are tested.

## Deviations
- **Process deviation (not precedent):** implementation began from the **unmerged** readiness commit `62a7834`, under coordinator delegation. The coordinator accepted the work for review, but READY was not yet authoritative on `main`. Future implementation waits until readiness is merged.
- The branch includes the updated readiness branch (PR #9). After PRs #9 and #10 merge, `main` must be merged into this branch and the shared files resolved by hand before this PR merges.

## Open questions
None.

## Blocked on
- Merge of the ready-marking PR (`chore/SIN-P1.1-003-004-ready`), then coordinator review of this task's PR.
- Integration with SIN-P1.1-003: both edit `schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md` and `implementation/task_board.yaml` (append-only). This PR merges second and needs a **deliberate manual resolution**. "Accept both" is unsafe: a trial merge showed it breaks the `__init__.py` import block and duplicates repo-map lines. Re-run the full gate on the combined state.

## Next ready after approval
After 003 and 004 are both merged and verified: SIN-P1.1-005 Observation (the coordinator opens its packet).

## Do not start
- 005–009, P1.1-G, any P1.2+ or P2+ work.

## Risks / things not to change casually
- The F3 construction is identity: changing the tag, sort order or field names changes every candidate ID. A new construction needs a new `kind` tag, not an edit.
- `dependency_hash=None` has exactly one meaning (no bundle); never use it as "not computed".
