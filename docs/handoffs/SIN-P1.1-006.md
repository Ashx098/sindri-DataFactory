# SIN-P1.1-006 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-05
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-006-finding` at `../worktrees/SIN-P1.1-006`
- HEAD commit: the PR #18 review-fix commit (after merging `main` `b46be56` into this branch)
- Base commit: `e70d4e4` (`main`, PR #17: 006 READY on `main`)
- Dirty files, if any: none after commit

## Completed
- `Finding` v1: an immutable claim with an exact candidate binding, one requirement, initial `Uncertainty`, a closed producer union (model, component or human), Observation citations and supporting artifacts. It has no status.
- `FindingTransition` v1: the edge table, `ProposedCheck` only on the transition into `check_proposed` (`ExistingPolicyCheck | DevelopmentProbeRequest`), deciding citations only on confirm/refute, typed drop reasons with `superseded_by`, and the chain head.
- Contract tests and adapted §20.6 fixtures; component invariants INV-FD-001…004.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 17 files |
| `uv run pytest -q` | 707 passed, 8 skipped | 105 Finding tests (after PR #18 fixes) |
| Planted: `hypothesis → confirmed` allowed | 2 failures | restored |
| Planted: confirm with empty citations | 2 failures | restored |
| Planted: `proposed_check` optional on `check_proposed` | 1 failure | restored |
| Planted: `training_allowed=True` default | 1 failure | restored |
| Planted: `confirming_status` defaulted | 1 failure | restored |
| Planted: `confirming_status` accepts any status | 2 failures | restored |
| Planted: any probe action allowed | 3 failures | restored |
| Planted: mixed probe payload allowed | 1 failure | restored |

## Changed
`src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_finding.py`, three fixtures, `components/schemas.yaml`, `docs/REPO_MAP.md`, task packet, this handoff. Coordinator verification is recorded after merge.

## Decisions
None new. PR #18 review fixes applied:
1. `ExistingPolicyCheck.confirming_status` (PASS|FAIL) with a `refuting_status` helper.
2. `DevelopmentProbeRequest.policy_hash`, and strict `run_sim`/`run_formal` payloads (all other actions rejected).
3. The probe→terminal prohibition is recorded for 009/P1.5. No promotion relation is invented here.
4. Tests and planted bugs for all of the above.

## Deviations
- **Governance (coordinator correction, PR #20):** readiness for this task was recorded by the agent on PR #17 (`1f50e904`) from a chat instruction, without re-reading the PR. A later coordinator comment (`5981249383`) had required one more packet amendment and said not to mark READY. The task is therefore `blocked`; this PR applies the omitted rules and stays review-only until the coordinator clears it. **Lesson recorded:** before recording any readiness, re-read the PR's latest coordinator comments.
- `main` `b46be56` was merged into this branch; conflicts in the packet and board were resolved toward `main` (authoritative).

## Open questions
None. (The earlier `inspect_waveform` probe question is settled: v1 probes are `run_sim`/`run_formal` only.)

## Coordinator verification
- PR #18 merged to `main` as `0d19b0f`; merged-main CI `37244343777` passed.
- PR #19 later integrated EpisodeState deliberately with this Finding state and merged as `b6ced72`; merged-main CI `37256889064` passed.
- Task status: `verified` on 2026-10-05.

## Blocked on
- None. This task is verified.

## Next eligible for packet drafting
- SIN-P1.1-008 serialization/versioning. Implementation remains unauthorized until its own packet is reviewed, merged and marked READY.

## Do not start
- 008 implementation, 009, P1.1-G, P1.2+; 008 is packet-drafting only until separately authorized. No blackboard store, controller logic or probe promotion.

## Risks / things not to change casually
- Never put `status`, `proposed_check` or `rank` back on Finding (FD1, FD7). Never add an `actor`/`direction` field (FD2, FD9).
- Supporting artifacts and probes must never be able to decide a Finding (FD5, FD8, ADR-0005).
