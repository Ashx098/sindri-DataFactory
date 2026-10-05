# SIN-P1.1-008 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-05
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `test/SIN-P1.1-008-serialization` at `../worktrees/SIN-P1.1-008`
- HEAD commit: the commit that adds this file
- Base commit: `ffe2ad2` (`main`, PR #23: 008 READY on `main`; PR #22 final review re-read before starting)
- Dirty files, if any: none after commit

## Completed
- Serialization/identity/versioning contract tests over a 39-entry catalog (10 fixtures + 29 generated variants) covering all nine P1.1 records and every union branch.
- Four test modules: round trip, identity encoding, schema versioning, strict deserialization.
- Component invariants INV-SER-001…004. **Tests and docs only; no `src/` change.**

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 18 files |
| `uv run pytest -q` | 1572 passed, 8 skipped | 773 new 008 tests |
| `uv run pytest -q tests/contract` | 1456 passed | |
| Planted: `exclude_none=True` in round-trip helper | 137 failures | restored |
| Planted: `content_id` hashes `model_dump_json()` | 41 failures | caught by canonical-identity contract + byte vector; restored |
| Planted: `schema_version` 2 accepted | 21 failures | restored |
| Planted: float walker removed | 167 failures | restored |
| Planted: canonical encoding sorts arrays | 10 failures | incl. all three S11 tests; restored |
| `git status src/` after planting | clean | product files byte-identical |

## Changed
Five new files under `tests/contract/`; `components/schemas.yaml` (invariants, related doc); `docs/REPO_MAP.md`; `implementation/task_board.yaml` (→ `review`); task packet; this handoff.

## Decisions
None new; S1–S17 implemented as decided on PR #22.

## Deviations
None. Implementation started from `main` after READY was authoritative there, and after re-reading PR #22's latest coordinator comments.

## Open questions
None.

## Follow-ups owned by P1.2 (hard requirements from S15/S16)
- **Authoritative ingest boundary:** reject duplicate JSON object member names, NaN/Infinity and malformed bytes **before** model validation, with its own tests. Probe evidence: Pydantic's `model_validate_json` accepts duplicate keys (last wins) and admits NaN/Infinity tokens. The records reject the latter, but duplicates must be stopped at ingest.
- **Integer storage/interop:** preserve integers exactly, or reject out-of-range values explicitly at the storage boundary (records accept integers beyond 2⁶³; PostgreSQL `bigint` and JS consumers do not). Never narrow silently.

## Blocked on
- Coordinator review and merge of this task's PR.

## Next ready after approval
After 008 is merged and verified: SIN-P1.1-009, cross-record invariants (all the deferred rules listed in packets 002–007). The coordinator opens its packet.

## Do not start
- 009, P1.1-G, P1.2+; no schema change, version gate, canonical-order validator, migration framework or strict loader.

## Risks / things not to change casually
- Never make the canonical encoding order-insensitive for arrays: array order is exact-record identity (S11). Use a specialized semantic hash where a rule needs set semantics.
- `model_validate_json` in these tests covers known-good repository serialization only. It is **not** an ingest boundary for untrusted evidence-store bytes.
- The S9 walkers assert rejection, not the per-leaf reason (see the packet's known limitations).
