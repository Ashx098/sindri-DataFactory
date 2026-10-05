# SIN-P1.1-007 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-05
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-007-episode-state` at `../worktrees/SIN-P1.1-007`
- HEAD commit: the PR #19 review-fix commit (after merging `main` `b46be56` into this branch)
- Base commit: `e70d4e4` (`main`, PR #17: 007 READY on `main`)
- Dirty files, if any: none after commit

## Completed
- `EpisodeBudget` v1: additive `limits` (zeros allowed) and `wall_clock_limit_ms > 0`; identity is its `content_id()`; `remaining(state)` is derived.
- `EpisodeState` v1, an immutable hash-chained snapshot:
  - ADR-0006 states with WAITING/`resume_state`, `abort_reason`;
  - exact candidate bindings;
  - pending jobs with `request_hash`, a required-but-nullable `candidate` (no `action`), and reservations;
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
| `uv run pytest -q` | 694 passed, 8 skipped | 89 EpisodeState tests (after PR #19 fixes) |
| Planted: WAITING with zero pending jobs | 1 failure | restored |
| Planted: reserved-sum check skipped | 3 failures | restored |
| Planted: `request_hash` optional | 1 failure | restored |
| Planted: candidate required in IMPLEMENT | 1 failure | restored |
| Planted: zero additive limits rejected | 1 failure | restored |
| Planted: non-null job candidate required | 1 failure | restored |
| Planted: `action` field reintroduced | 2 failures | restored |

## Changed
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_episode_state.py`, two fixtures, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, task packet, this handoff. Coordinator verification is recorded after the integrated merge.

## Decisions
None new. PR #19 review fixes applied:
1. `PendingJob.candidate: CandidateBinding | None`, with the key required.
2. `PendingJob.action` removed; `request_hash` is the request identity (ADR-0005: jobs are broader than Observations).
3. Tests for candidate-less WAITING → PLAN, the required candidate key, and the absent `action`, with two new planted bugs.

The four implementation choices listed in the packet were approved as-is on PR #19.

## Deviations
- **Governance (coordinator correction, PR #20):** readiness for this task was recorded by the agent on PR #17 (`1f50e904`) from a chat instruction, without re-reading the PR. A later coordinator comment (`5981249383`) had required one more packet amendment and said not to mark READY. The task is therefore `blocked`; this PR applies the omitted rules and stays review-only until the coordinator clears it. **Lesson recorded:** before recording any readiness, re-read the PR's latest coordinator comments.
- `main` `b46be56` was merged into this branch; conflicts in the packet and board were resolved toward `main` (authoritative).

## Open questions
None. (Whether a pending job must match the active candidate is settled: P1.5 decides per request/state.)

## Coordinator verification
- PR #19 merged to `main` as `b6ced72`.
- Merged-main CI run `37256889064` passed on the integrated 006+007 state.
- Task status: `verified` on 2026-10-05.

## Blocked on
- None. This task is verified.

## Integration with SIN-P1.1-006 (done, per the coordinator's merge order)
`main` at `0d19b0f` (PR #18 merged) was merged into this branch. Three files were resolved **by hand**, not "accept both", in P1.1 order (006 before 007):
- `src/sindri/schemas/__init__.py`: rebuilt as seven valid import blocks. The 74 exports were verified to equal exactly the union of `main`'s (62) and this branch's (59) `__all__`.
- `components/schemas.yaml`: outputs in P1.1 order; INV-FD-* then INV-EP7-*; `related_adrs` includes ADR-0006; `related_docs` lists 002–007.
- `docs/REPO_MAP.md`: one schemas line naming every record; the "remaining records" row removed, because 006 + 007 complete the P1.1 record set.

`implementation/task_board.yaml` merged automatically; both tasks remain `blocked`.

**Combined gate:** ruff and mypy clean (18 files); **799 passed**, 8 skipped (= 707 on `main` + 694 here − 602 shared); 683 contract tests; Finding + EpisodeState tests 194; 29 unique invariants; all 74 exports resolve.

## Next eligible for packet drafting
- SIN-P1.1-008 serialization/versioning. Implementation remains unauthorized until its own packet is reviewed, merged and marked READY.

## Do not start
- 008 implementation, 009, P1.1-G, P1.2+; 008 is packet-drafting only until separately authorized. No controller, job runner, failure-signature constructor or solver-config record.

## Risks / things not to change casually
- Do not put wall-clock back into `BudgetVector` (concurrency makes it non-additive, ED7), and never store `remaining` (ED8).
- The ADR-0006 table changes only through an explicit controller/ADR review.
- `failure_signature_v1` belongs to P1.5; do not add a generic JSON hash here (ED11).
