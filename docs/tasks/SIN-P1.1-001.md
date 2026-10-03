# SIN-P1.1-001 — Core domain schemas, content IDs and status taxonomy

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
The P1.1 boundary records exist as strict, versioned Pydantic models with content-hash identity, so
P1.2 (evidence store), P1.3 (sandbox), P1.5 (controller) and P1.6 (FIFO package) can build against
frozen interfaces.

## Why / architecture references
- Master architecture section(s): §8.7 authority records; §20.1, 20.3, 20.4, 20.6, 20.9, 20.10, 20.11 schemas; §14 J2 status taxonomy; §4 authority rule.
- Phase/subphase: P1.1 (`docs/implementation/phases/P1_FOUNDATION_AND_JUDGE_V0.md`)
- ADRs/RFCs: ADR-0001 (layout/stack), ADR-0002 (authority modes, status taxonomy), ADR-0003.

## Owner / coordinator
- Owner: TBD
- Integrator: platform lead
- Reviewers: platform lead; DV/formal engineer for `Requirement` and `EvaluationPolicy` semantics

## Base
- Base branch: `main`
- Base commit: commit that closes B0.G
- Worktree: `../worktrees/SIN-P1.1-001`

## Dependencies
- Required completed tasks: `B0.G`
- Required schemas/contracts: `sindri.core.status` (exists)

## Scope
- In scope:
  - `src/sindri/core/ids.py`: typed ID newtypes and SHA-256 content hashing of canonical bytes/JSON.
  - `src/sindri/schemas/`: `TaskManifest`, `Requirement`, `EvaluationPolicy`, `CandidateManifest`, `Observation`, `Finding`, `EpisodeState`.
  - Every record: `schema_version`, `extra="forbid"`, frozen where the record is immutable, enums from `sindri.core.status` only.
  - `Observation` binds to candidate hash, tool image digest, profile and configuration; claims of pass/fail reference observation IDs (master §8.7 repository invariant).
  - Serialized example per record under `tests/contract/examples/` adapted from master §20.
  - JSON Schema export per record to `docs/schemas/` via a script (generated, never hand-edited).
- Allowed paths: `src/sindri/core/`, `src/sindri/schemas/`, `tests/unit/`, `tests/contract/`, `docs/schemas/`, `scripts/export_schemas.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `THIRD_PARTY.md`, this packet, its handoff.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created.
- Other forbidden paths: `src/sindri/{evidence,tools,controller,judge,solver}/` (later subphases).

## Non-goals
- No evidence store, database, sandbox or tool adapter (P1.2–P1.4).
- No controller state machine logic beyond the `EpisodeState` record shape (P1.5).
- No FIFO contract or fixtures (P1.6); no tool version pinning (P1.4).
- No Contract, SpecCertificate, EvaluatorCertificate, ReleaseManifest or DatasetRecord schemas (later phases).
- No LLM calls.

## Interfaces touched
- Schemas: new, `schema_version = 1`.
- Tool APIs: none.
- DB/migrations: none.
- External dependencies: none beyond pydantic (record any addition in `THIRD_PARTY.md`).

## Acceptance criteria
- [ ] Each record round-trips its serialized example (model → JSON → model is identical).
- [ ] Unknown fields, wrong enum values and missing required fields are rejected (negative tests per record).
- [ ] Status fields cannot hold a value outside `sindri.core.status`; `TOOL_ERROR`/`TIMEOUT`/`INCONCLUSIVE` cannot collapse into `FAIL` or `PASS`.
- [ ] Content ID is stable for identical input and changes for any changed byte (Hypothesis property test).
- [ ] An `Observation` whose inputs lack candidate hash or tool image digest is invalid.
- [ ] `TaskManifest` requires `authority_mode`, family/lineage IDs and `split`.
- [ ] JSON Schemas exported; `components/schemas.yaml` written from the component template.
- [ ] `docs/REPO_MAP.md` updated; no import-boundary violations.

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest tests/unit tests/contract tests/architecture -q
python scripts/export_schemas.py --check   # exported schemas match models
```

## Plan of record
`src/sindri/core/ids.py`, `src/sindri/schemas/{__init__,task,requirement,policy,candidate,observation,finding,episode}.py`, `tests/unit/test_ids.py`, `tests/contract/test_schemas.py`, `tests/contract/examples/*.json`, `scripts/export_schemas.py`, `docs/schemas/*.json`, `components/schemas.yaml`. If this changes materially, stop and ask the coordinator.

## Status
`planned` (authoritative status: `implementation/task_board.yaml`)

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
