# SIN-P1.1-007 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-007-episode-state` at `../worktrees/SIN-P1.1-007`
- HEAD commit: the commit that adds this file
- Base commit: `e70d4e4` (`main`, PR #17: 007 READY on `main`)
- Dirty files, if any: none after commit

## Completed
- `EpisodeBudget` v1: additive `limits` (zeros allowed) and `wall_clock_limit_ms > 0`; identity is its `content_id()`; `remaining(state)` is derived.
- `EpisodeState` v1, an immutable hash-chained snapshot:
  - ADR-0006 states with WAITING/`resume_state`, `abort_reason`;
  - exact candidate bindings;
  - pending jobs with `request_hash` and reservations;
  - spent/reserved plus wall-clock elapsed;
  - failure signature with its repeat count;
  - nullable checkpoint;
  - policy/budget/solver-config hashes.
- `ALLOWED_EPISODE_TRANSITIONS`, `ACTIVE_EPISODE_STATES`, `CANDIDATE_REQUIRED_STATES` as data for P1.5/009. Additive `JobId`.
- Contract tests and adapted §20.11 fixtures; component invariants INV-EP7-001…003.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 17 files |
| `uv run pytest -q` | 691 passed, 8 skipped | 86 EpisodeState tests |
| Planted: WAITING with zero pending jobs | 1 failure | restored |
| Planted: reserved-sum check skipped | 3 failures | restored |
| Planted: `request_hash` optional | 1 failure | restored |
| Planted: candidate required in IMPLEMENT | 1 failure | restored |
| Planted: zero additive limits rejected | 1 failure | restored |

## Changed
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_episode_state.py`, two fixtures, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
None new. Five implementation interpretations are listed in the packet's completion evidence. The most notable: pending jobs need not bind the active candidate (a P1.5 rule if needed), and `BudgetRemaining` may go negative to represent an overrun.

## Deviations
None. Started from `main` after READY was authoritative there.

## Open questions
- Interpretation 5: should pending jobs be restricted to the active candidate in some states? That is a controller rule for P1.5.

## Blocked on
- Coordinator review. **Integration with SIN-P1.1-006:** both edit `schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md` and `implementation/task_board.yaml`. Whichever PR merges second needs a deliberate manual resolution, never "accept both", followed by the full gate on the combined state.

## Next ready after approval
After 006 and 007 are merged and verified: SIN-P1.1-008 serialization/versioning (the coordinator opens its packet).

## Do not start
- 008, 009, P1.1-G, P1.2+; no controller, job runner, failure-signature constructor or solver-config record.

## Risks / things not to change casually
- Do not put wall-clock back into `BudgetVector` (concurrency makes it non-additive, ED7), and never store `remaining` (ED8).
- The ADR-0006 table changes only through an explicit controller/ADR review.
- `failure_signature_v1` belongs to P1.5; do not add a generic JSON hash here (ED11).
