# SIN-P1.1-001 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code), assigned by Avinash
- Branch/worktree: `feat/SIN-P1.1-001-base-ids-hashing` at `../worktrees/SIN-P1.1-001`
- HEAD commit: implementation `1632ea7` (CI push run 37146101929 success); this handoff in the next commit
- Base commit: `0cb29dd` (B0.G approval commit on PR #1, not yet on `main`)
- Dirty files, if any: none after commit

## Completed
- `sindri.core.ids`:
  - typed, validating ID types: `TaskId`, `CandidateId`, `ObservationId`, `EpisodeId`, `RequirementId`, `PolicyId`, `FindingId`, `ContentId`;
  - `content_id(bytes)`, `canonical_json_bytes(obj)`, `canonical_json_id(obj)`;
  - Pydantic integration so later records can use the ID types directly.
- `sindri.core.status`: ADR-0002 TIMEOUT wording; `@unique` on every enum. Members unchanged.
- Tests: `tests/unit/test_ids.py` (new); `tests/unit/test_status.py` extended.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | |
| `uv run pytest -q` | 82 passed, 9 skipped | skips = packages not yet created |
| GitHub Actions on `1632ea7` | success, run 37146101929 | |
| Planted bug: hash ignores the last byte | suite fails (2 tests) | reverted |
| Planted bug: canonical JSON accepts int keys | suite fails (1 test) | reverted |

## Changed
`src/sindri/core/ids.py`, `src/sindri/core/status.py`, `tests/unit/test_ids.py`, `tests/unit/test_status.py`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff.

## Decisions
None at ADR level. Task-level choices, recorded in the packet:
- ID formats follow the master §20 examples.
- `ContentId` is `sha256:<64 lowercase hex>`.
- Canonical JSON rejects any value the json module would silently convert.

## Deviations
- Branch was based on PR #1's approval commit `0cb29dd` rather than `main`; merging PR #2 with a merge commit brought both into `main`, so no rebase was needed.
- The first commit (`1632ea7`) carried a blank handoff template because of an agent tooling error; fixed in the following commit.

## Open questions
- Should identity-bearing record fields forbid floats outright? Decide in SIN-P1.1-002…007 (packet "Known limitations").

## Blocked on
- Nothing. Merged via PR #2 (`7cf0fd8`); B0-E004 closed. Awaiting coordinator verification (`merged` → `verified`).

## Next ready after approval
Newly unblocked once this task is merged and verified (the coordinator opens them; the agent does not):
- SIN-P1.1-002 … 007 (records), which can run in parallel now that the primitives are frozen.

## Do not start
- Any other P1.1 task until the coordinator opens it.
- P1.2 / P1.3 / P1.4 / P1.5 / P1.6 and any P2+ work.

## Risks / things not to change casually
- Changing an ID pattern or the canonical JSON encoding changes identities of stored artifacts. Treat it as a schema-semantic change (ADR + migration).
- Do not add enum members or aliases without an ADR-0002 update; `@unique` and the taxonomy test enforce this.
