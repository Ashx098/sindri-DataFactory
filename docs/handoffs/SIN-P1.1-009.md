# SIN-P1.1-009 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-05
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.1-009-cross-record` at `../worktrees/SIN-P1.1-009`
- HEAD commit: the commit that adds this file
- Base commit: `a882aa2` (`main`, PR #27: 009 READY; PR #26 coordinator comments re-read before starting)
- Dirty files, if any: none after commit

## Completed
- `src/sindri/schemas/cross_record.py`: pure `check_records(Iterable[Record]) -> tuple[Violation, ...]`.
  - 54 runtime `InvariantCode`s, one registered rule function each (`RULES`), plus `run_rules` for the harness.
  - Aggregate output with no cascades; deterministic sort.
  - `TypeError` for a non-`Record` or unsupported `Record` type.
  - Imports concrete schema modules only.
- A coherent 46-record FIFO bundle built from a typed spec (`tests/contract/cross_record/_bundle.py`); the §20 examples are untouched.
- Tests:
  - 83 isolated negative cases, each asserting the exact code set and cardinality;
  - the rule-removal harness over all 54 codes;
  - CT-1 (37 `ContentId` fields classified), CT-2 (one set head), CT-3 (no-cascade ownership) and CT-4 (T1 implied by B1 + B2);
  - hypothesis order-independence and idempotence properties;
  - variant positives.
- Docs: `components/schemas.yaml` (INV-XR-001…006, FM-XR-001/002, public API) and `docs/REPO_MAP.md`.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 19 files |
| `uv run pytest -q` | 1802 passed, 8 skipped | |
| `uv run pytest -q tests/contract` | 1686 passed | |
| `uv run pytest -q tests/contract/cross_record` | 176 passed | |
| Forbidden-path diff (existing schemas, `sindri.core`, examples) | empty | |
| `grep "from sindri.schemas import" cross_record.py` | empty | |
| 13 manual planted bugs (packet list) | all caught | counts in packet; sha256 restore verified |

## Changed
- **Product:** `cross_record.py` (new) and `schemas/__init__.py` (exports).
- **Tests:** `tests/contract/cross_record/` (new).
- **Docs:** `components/schemas.yaml`, `docs/REPO_MAP.md`, the task board (→ `review`), the packet, and this handoff.

## Decisions
None new. X1–X13, OQ1–OQ4, N3 and N4 are implemented as decided on PR #26.

## Deviations (for coordinator review)
- **XR-T1 → CT-4.** "All transitions of one `finding_id` carry the same `finding_hash`" is implied by B1 + B2, so it can never fire alone. This is the same reasoning as the coordinator's C2 ruling. It is a contract test, not a runtime code. If the coordinator prefers a runtime T1, it would need B1 to stop owning conflicting Finding ids, which changes X3.

## Implementation interpretations (for review; recorded in the packet)
- **Chain heads:** a cross-key supersedes link makes both chain keys head-less.
- **K3:** skips read-only head tasks (K2 owns them).
- **E3:** judges only ADR-0006-legal pairs (E2 owns illegal edges).
- **F3/F5:** skip a cited Observation whose own binding is broken (B2 owns it).
- **P8:** skips a policy whose task is absent (P1 owns it).

## Open questions
None.

## Blocked on
- Coordinator review and merge of this task's PR.

## Next ready after approval
After 009 is merged and verified, the next step is **P1.1-G**, the subphase integration gate. The coordinator opens it.

## Do not start
- P1.1-G, P1.2+.
- No schema field for L1–L3.
- No Contract, ToolProfile, evaluator-bundle, dependency-bundle, job-request or solver-config records.

## Risks / things not to change casually
- **Adding a rule:** add an `InvariantCode`, a `RULES` entry, an isolated negative `Case`, and its dependency-ordering skips. The harness fails until every code has a case that only that rule catches.
- **Adding a `ContentId` field to any schema:** classify it in `test_hash_inventory.py` (H1/H2/H3); CT-1 fails until you do.
- **Positive-bundle edits:** keep `positive_spec()` clean. Every negative case is "positive + one mutation".
- **Not an ingest boundary:** `check_records` validates a *closed* bundle. It is not an authorization boundary and not a partial-store query (X4, D1).
