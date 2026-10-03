# SIN-P1.1-001 — Base IDs, content hashing, enums and status taxonomy

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
The shared primitives every P1.1 record depends on are frozen: typed IDs, canonical content hashing,
and the status/tier/evidence/authority enums. Records (SIN-P1.1-002 onward) can then be built in
parallel without redefining primitives.

## Why / architecture references
- Master architecture section(s): §4 principle 9 (results bind to exact artifacts); §8 F1 status normaliser; §8.7 authority records; §14 J2 status taxonomy; §12 G2/G3 tiers and evidence levels.
- Phase/subphase: P1.1 (`docs/implementation/phases/P1_FOUNDATION_AND_JUDGE_V0.md`); P1.1 breakdown in `docs/implementation/CURRENT_PHASE.md`.
- ADRs/RFCs: ADR-0001, ADR-0002 (accepted 2026-10-04, with the TIMEOUT amendment).

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned by Avinash 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: the B0.G approval commit on PR #1 (rebase onto `main` once PR #1 merges)
- Worktree: `../worktrees/SIN-P1.1-001`

## Dependencies
- Required completed tasks: `B0.G`
- Required schemas/contracts: existing `sindri.core.status`

## Scope
- In scope:
  - `src/sindri/core/ids.py`: typed ID types for task, candidate, observation, episode, requirement, policy, finding; `content_id(bytes)` and `canonical_json_id(obj)` (SHA-256 over canonical JSON: sorted keys, no insignificant whitespace, UTF-8).
  - `src/sindri/core/status.py`: review and finalize against master §14 J2 and Appendix A; add nothing that is not in the master. Align the `ToolStatus.is_label` docstring with accepted ADR-0002: raw TIMEOUT stays TIMEOUT, and only a downstream EvaluationPolicy-driven outcome may be negative.
  - Unit and property tests for both.
- Allowed paths: `src/sindri/core/`, `tests/unit/`, `docs/REPO_MAP.md`, `THIRD_PARTY.md`, this packet, `docs/handoffs/SIN-P1.1-001.md`.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created.
- Other forbidden paths: `src/sindri/schemas/` (SIN-P1.1-002+), every other `src/sindri/` package.

## Non-goals
- No Pydantic record models (TaskManifest, Observation, ...): later P1.1 tasks.
- No storage, hashing of files on disk, sandbox or tool code (P1.2–P1.4).
- No ID generation policy beyond content IDs and typed wrappers (no UUID service, no database).

## Interfaces touched
- Schemas: none. Tool APIs: none. DB/migrations: none.
- External dependencies: none beyond the standard library and pydantic.

## Acceptance criteria
- [x] Same input → same content ID; any single changed byte → different ID (Hypothesis property test).
- [x] Canonical JSON ID is independent of key order and whitespace; differs for any value change.
- [x] Typed IDs reject malformed values (wrong prefix/format) and are not interchangeable in type checks.
- [x] Only `PASS`/`FAIL` are labels; `TOOL_ERROR`, `TIMEOUT`, `INCONCLUSIVE`, `UNSUPPORTED` cannot be coerced to `PASS`/`FAIL` (negative tests).
- [x] Unknown status strings are rejected when parsed.
- [x] `ruff`, `mypy --strict`, full `pytest` green; no import-boundary violations.
- [x] Handoff written; report ends with "Awaiting coordinator assignment."
- [ ] Merge condition (B0-E004): `main` branch protection confirmed enabled before this task's PR merges.

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
```

## Plan of record
`src/sindri/core/ids.py`, `src/sindri/core/status.py` (review only), `tests/unit/test_ids.py`, `tests/unit/test_status.py`. If this changes materially, stop and ask the coordinator.

## Status
`review` (authoritative status: `implementation/task_board.yaml`)

## Completion evidence
- Files changed: `src/sindri/core/ids.py` (new), `src/sindri/core/status.py` (ADR-0002 docstring, `@unique` on all enums; no members added or removed), `tests/unit/test_ids.py` (new), `tests/unit/test_status.py`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff.
- Tests run/results: `uv run ruff check .` clean; `uv run mypy` clean (strict); `uv run pytest -q`: 82 passed, 9 skipped (packages not yet created).
- Acceptance evidence:
  - Hashing: Hypothesis properties for determinism, single-byte change, appended bytes; the SHA-256 empty-input known vector.
  - Canonical JSON: Hypothesis key-order and formatting invariance; any value change alters the ID. `1`, `1.0`, `True`, `"1"`, `[1]`, `{"1":1}` give 6 distinct IDs. Int keys, tuples, sets, bytes, NaN, inf and arbitrary objects are rejected rather than silently converted.
  - Typed IDs: master §20 examples accepted; 17 malformed values rejected; a mypy `--strict` run proves `CandidateId` and bare `str` are rejected where `TaskId` is required; Pydantic fields validate strictly and serialize as plain str.
  - Statuses: TIMEOUT/TOOL_ERROR/INCONCLUSIVE/UNSUPPORTED never equal PASS/FAIL and round-trip unchanged; no enum aliases; unknown and miscased strings rejected; the taxonomy matches master J2, Appendix A, G2, G3 and §4.
  - Planted bugs in `ids.py` (hash ignoring the last byte; accepting int keys) each made the suite fail; both reverted.
- Known limitations: domain ID formats follow the master §20 examples; patterns are permissive enough that, e.g., `ob_1` is also a syntactically valid `TaskId` (records type their fields, so this is not ambiguous in use). Floats hash by Python's shortest repr; records should avoid floats in identity-bearing fields.
- Handoff/next action: `docs/handoffs/SIN-P1.1-001.md`. Merge blocked on PR #1 merging and on B0-E004 (branch protection).
