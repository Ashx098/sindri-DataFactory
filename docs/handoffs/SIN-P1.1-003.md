# SIN-P1.1-003 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-003-evaluation-policy` at `../worktrees/SIN-P1.1-003`
- HEAD commit: the commit that adds this file
- Base commit: `62a7834` (ready-marking commit on `chore/SIN-P1.1-003-004-ready`; not yet on `main`)
- Dirty files, if any: none after commit

## Completed
- `EvaluationPolicy` v1 with `Configuration`/`ParameterAssignment`, `Check` (`CheckKind`, `Visibility`, `FormalMode`), `EnvironmentAssumption`, `Obligation`, `PolicyException`/`ExcludedPair`.
- Additive IDs: `ObligationId`, `CheckId`, `ConfigurationId`, `ToolProfileId`, `ExceptionId`.
- Contract tests and the adapted §20.10 fixture; component-contract invariants INV-EP-001…004, including the judge-side protection rule (E2).

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 14 files; caught a real mixed-ID variable bug during implementation |
| `uv run pytest -q` | 359 passed, 8 skipped | 83 policy tests, 12 new ID tests (after PR #10 fixes) |
| E5a fix: original `min_length=1` restored | 1 failure | confirms the new test catches it |
| Planted bug: `mandatory` default `True` | 1 failure | reverted |
| Planted bug: obligation→check resolution removed | 1 failure | reverted |
| Planted bug: `cover` allowed as a formal mode | 1 failure | reverted |

## Changed
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/policy.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_evaluation_policy.py`, `tests/contract/examples/evaluation_policy.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
E1–E7 (coordinator, PR #8) and E8–E9 (agent decisions under coordinator delegation, recorded in the packet and effective on merge of the ready-marking PR). No new decisions in implementation.

## Review fixes (PR #10)
- E5a: zero-parameter designs use one explicit default configuration with empty assignments; duplicate empty sets are rejected.
- E7a: no wall-clock expiry on policy exceptions (semantic not-applicability); temporary waivers are release-layer.
- 009: the strengthened mandatory-requirement enforcement rule is recorded for SIN-P1.1-009.
- E8/E9 approved by the coordinator.

## Deviations
- **Process deviation (not precedent):** implementation began from the **unmerged** readiness commit `62a7834`, under coordinator delegation. The coordinator accepted the work for review, but READY was not yet authoritative on `main`. Future implementation waits until readiness is merged.
- The branch includes the updated readiness branch (merged in at `fdf66da`), so after PR #9 merges this PR's diff is only 003's own changes.

## Open questions
None.

## Blocked on
- Merge of the ready-marking PR (`chore/SIN-P1.1-003-004-ready`), then coordinator review of this task's PR.
- Integration with SIN-P1.1-004: both append to `schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md` and `implementation/task_board.yaml`. Whichever PR merges second needs a **deliberate manual resolution**. "Accept both" is unsafe: a trial merge showed it breaks the `__init__.py` import block and duplicates repo-map lines. Re-run the full gate on the combined state.

## Next ready after approval
After 003 and 004 are both merged and verified: SIN-P1.1-005 Observation (the coordinator opens its packet). Observation can now reference `CheckId` and `ConfigurationId` from this record.

## Do not start
- 005–009, P1.1-G, any P1.2+ or P2+ work. No solver projection of the policy (P1.5/P5).

## Risks / things not to change casually
- Do not add `mutation_qualification`, `clean_replay` or `cover` to this record. They belong to evaluator qualification and release (E3/E4).
- Exceptions must stay not-applicable exclusions (E7/E9). Using them to waive failures or remove mandatory checks defeats the policy versioning route.
