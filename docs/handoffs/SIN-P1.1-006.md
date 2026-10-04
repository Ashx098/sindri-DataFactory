# SIN-P1.1-006 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-006-finding` at `../worktrees/SIN-P1.1-006`
- HEAD commit: the commit that adds this file
- Base commit: `e70d4e4` (`main`, PR #17: 006 READY on `main`)
- Dirty files, if any: none after commit

## Completed
- `Finding` v1: an immutable claim with an exact candidate binding, one requirement, initial `Uncertainty`, a closed producer union (model, component or human), Observation citations and supporting artifacts. It has no status.
- `FindingTransition` v1: the edge table, `ProposedCheck` only on the transition into `check_proposed` (`ExistingPolicyCheck | DevelopmentProbeRequest`), deciding citations only on confirm/refute, typed drop reasons with `superseded_by`, and the chain head.
- Contract tests and adapted §20.6 fixtures; component invariants INV-FD-001…003.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 17 files |
| `uv run pytest -q` | 690 passed, 8 skipped | 88 Finding tests |
| Planted: `hypothesis → confirmed` allowed | 2 failures | restored |
| Planted: confirm with empty citations | 2 failures | restored |
| Planted: `proposed_check` optional on `check_proposed` | 1 failure | restored |
| Planted: `training_allowed=True` default | 1 failure | restored |

## Changed
`src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_finding.py`, three fixtures, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
None new. Five implementation interpretations are listed in the packet's completion evidence. The most notable: a first transition must start from `hypothesis` (in-record), and probes cannot name `inspect_waveform` (the action is `ObservationAction`).

## Deviations
None. Started from `main` after READY was authoritative there.

## Open questions
- Interpretation 4: should development probes eventually request diagnostic queries (`inspect_waveform`/`coverage`)? That needs the ADR-0005 diagnostic result type.

## Blocked on
- Coordinator review. **Integration with SIN-P1.1-007:** both edit `schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md` and `implementation/task_board.yaml`. Whichever PR merges second needs a deliberate manual resolution, never "accept both", followed by the full gate on the combined state.

## Next ready after approval
After 006 and 007 are merged and verified: SIN-P1.1-008 serialization/versioning (the coordinator opens its packet).

## Do not start
- 008, 009, P1.1-G, P1.2+; no blackboard store, controller logic or probe promotion.

## Risks / things not to change casually
- Never put `status`, `proposed_check` or `rank` back on Finding (FD1, FD7). Never add an `actor`/`direction` field (FD2, FD9).
- Supporting artifacts and probes must never be able to decide a Finding (FD5, FD8, ADR-0005).
