# SIN-P1.1-002 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code), assigned by Avinash
- Branch/worktree: `feat/SIN-P1.1-002-taskmanifest-requirement` at `../worktrees/SIN-P1.1-002`
- HEAD commit: the commit that adds this file
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
| `uv run pytest -q` | 252 passed, 8 skipped | 158 contract tests |
| Planted bug: `split` default | 1 failure | reverted |
| Planted bug: `extra="allow"` | 9 failures | reverted |
| Planted bug: `training_allowed=True` default | 1 failure | reverted |
| Spot-check of rejection reasons | each rejection fails for its intended reason | see packet |

## Changed
`src/sindri/core/ids.py` (insertions only), `src/sindri/schemas/` (new), `tests/contract/` (new), `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
No new ADR. Task-level implementation choices, recorded in the packet:
- `schema_version` is a `StrictInt` pinned to 1, because Pydantic's `Literal[1]` accepts `True`/`1.0`. Verified by probe.
- Rights live at manifest level.
- Commits must be full object IDs.
- `ParameterScope` is a tuple of named value lists (not a dict), so records are fully immutable.

## Deviations
- The board went from `ready` to `review` in one step; the intermediate `active` state was not committed separately. The work happened in a single session on this branch.

## Open questions
- `repo` is not URL-validated. Add rules when a consumer (the P2.2 repo miner) defines them.

## Blocked on
- Coordinator review and merge of this task's PR.

## Next ready after approval
Per the P1.1 order, once this task is merged and verified (the coordinator opens them; the agent does not):
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
