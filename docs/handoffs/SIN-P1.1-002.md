# SIN-P1.1-002 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code), assigned by Avinash
- Branch/worktree: `feat/SIN-P1.1-002-taskmanifest-requirement` at `../worktrees/SIN-P1.1-002`
- HEAD commit: the PR #6 review-fix commit (child of `2a503ba`, whose CI run 37149318551 passed)
- Base commit: `2a11582` (`main`, PR #5 merge)
- Dirty files, if any: none after commit

## Completed
- `TaskManifest` and `Requirement` (schema v1) as closed, immutable, float-free records with strict scalars, implementing D1–D8 and C1–C6 from the packet.
- Shared `Record`/`StrictModel` base (`src/sindri/schemas/_base.py`): unknown-field rejection, frozen, recursive float rejection, exact `schema_version`, `content_id()`, version-chain check.
- Additive ID types: `FamilyId`, `LineageId`, `VariantId`, `ContractId`.
- Contract tests and adapted master-example fixtures; component contract `components/schemas.yaml`.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 13 files |
| `uv run pytest -q` | 264 passed, 8 skipped | 170 contract tests (after PR #6 review fixes) |
| Planted bug: `split` default | 1 failure | reverted |
| Planted bug: `extra="allow"` | 9 failures | reverted |
| Planted bug: `training_allowed=True` default | 1 failure | reverted |
| Planted bug: rights/split rule removed | 6 failures | reverted (review fix) |
| Spot-check of rejection reasons | each rejection fails for its intended reason | see packet |

## Changed
`src/sindri/core/ids.py` (insertions only), `src/sindri/schemas/` (new), `tests/contract/` (new), `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
No new ADR. Task-level implementation choices, recorded in the packet:
- `schema_version` is a `StrictInt` pinned to 1, because Pydantic's `Literal[1]` accepts `True`/`1.0`. Verified by probe.
- Rights live at manifest level.
- Commits must be full object IDs.
- `ParameterScope` is a tuple of named value lists (not a dict), so records are fully immutable.

## Review fixes (coordinator review on PR #6)
1. Rights/split compatibility enforced: `train` needs `training_allowed`; `dev`/`final` need `evaluation_allowed`. The earlier positive test that combined `train` with training disallowed was wrong and now uses a `final` split.
2. Packet corrected to match the code: `schema_version` is a StrictInt pinned to 1 (not `Literal[1]`); `licence` is declared text, with SPDX/policy validation deferred to P2.1.
3. `implementation/task_board.yaml` added to the packet's allowed paths as status-only governance state.

## Deviations
None open. Going `ready → review` in one session was accepted by the coordinator. Touching the task board is now an allowed path (review fix 3).

## Follow-ups (not in this task)
- Task-template convention: `docs/tasks/TASK_TEMPLATE.md` should list `implementation/task_board.yaml` as an implicit status-only allowed path for every task. This is for the coordinator's next governance change.

## Open questions
- `repo` is not URL-validated. Add rules when a consumer (the P2.2 repo miner) defines them.

## Coordinator verification
- PR #6 merged to `main` as `4377df5` after coordinator re-review.
- Merged-main CI run `37154049449` passed.
- Task status: `verified` on 2026-10-04.

## Blocked on
- None. This task is verified. No later task is authorized until its packet is separately reviewed and marked READY.

## Next eligible for packet drafting
Per the P1.1 order, now that this task is verified (the coordinator opens them; the agent does not):
- SIN-P1.1-003 EvaluationPolicy: owns the requirement → obligation mapping and introduces `ObligationId` (ADR-0004).
- SIN-P1.1-004 CandidateManifest.

003 and 004 may run in parallel.

## Do not start
- 003/004 until the coordinator writes and readies their packets.
- 005–009, P1.1-G, P1.2+ and any P2+ work.

## Risks / things not to change casually
- Later records must subclass `Record`/`StrictModel`. Declaring their own `Literal` version or using plain `int`/`bool` would reintroduce silent coercion.
- Changing an ID pattern or the canonical JSON encoding changes the identities of stored records (schema-semantic change: ADR + migration).
- Do not move `obligation_ids` back onto `Requirement` (ADR-0004).
