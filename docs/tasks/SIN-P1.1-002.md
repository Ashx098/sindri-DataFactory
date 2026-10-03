# SIN-P1.1-002 — TaskManifest + Requirement

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`TaskManifest` and `Requirement` exist as strict, versioned, immutable Pydantic records that make a
task's meaning and provenance explicit: authority mode, family/lineage/task/variant identity, split,
structured source rights, edit scope, and requirements that keep the original wording separate from
the normalized semantics. Nothing about authority, split, lineage or rights can be defaulted
silently. Later records (EvaluationPolicy, CandidateManifest, Observation) can then reference tasks
and requirements without inventing their shape.

## Why / architecture references
- Master architecture: §4 principles 8–9 and the authority rule; §8.7 authority records; §9 T1–T5 (sources, task types, lineage, split before generation); §9.1 authority modes; §11.6 traceability; §20.1 and §20.9 examples (as amended by the decisions below).
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md` (001 → **002** → {003, 004} → …).
- ADRs/RFCs: ADR-0001 (stack), ADR-0002 (`AuthorityMode`, statuses), **ADR-0004** (Requirement does not own obligations).

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned by Avinash 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash; RTL/DV reviewer for requirement semantics once assigned (role currently unassigned)

## Base
- Base branch: `main`
- Base commit: `main` at the time the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-002`

## Dependencies
- Required completed tasks: SIN-P1.1-001 (verified)
- Required schemas/contracts: `sindri.core.ids`, `sindri.core.status`

## Coordinator decisions (PR #4 and final packet review, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| D1 | **(b)** TaskManifest is immutable and versioned, and limited to identity, authority, provenance, rights, split, contract and allowed edit scope. Tier, difficulty, evidence level and status history are lifecycle state for the registry/event log (P1.2). |
| D2 | **(a)** Add `FamilyId`, `LineageId`, `VariantId`, `ContractId` additively; frozen 001 patterns unchanged. IDs without a real consumer are deferred. |
| D3 | **(a)** A requirement is identified by (`task_id`, `requirement_id`). No `RequirementRef` abstraction until a downstream consumer needs one. |
| D4 | Disposition enum `proposed / approved / ambiguous / not_applicable / unsupported / rejected`; `ambiguous` blocks qualification. **`obligation_ids` removed from Requirement**: obligations belong to EvaluationPolicy / VerificationPlan (ADR-0004). |
| D5 | Both records reject binary floats **recursively**. Exact fractions, when needed later, use an exact representation (canonical decimal string, scaled integer or rational schema). `canonical_json_id()` is not changed in this task. |
| D6 | **(b)** Budgets are episode/experiment-scoped. Task identity does not change when the same task runs under a different budget. EpisodeState (007) records spent/remaining against a later immutable budget configuration. |
| C1 | `Requirement` is versioned: `requirement_version ≥ 1`, `supersedes: ContentId \| None`, with the same first-version invariant as TaskManifest. The logical `RequirementId` stays stable; any change to meaning or disposition is a new immutable version. |
| C2 | Rights are structured and explicit (see Scope). Missing rights are invalid; rights never default to training-allowed. |
| C3 | Edit scope depends on task type: mutating types require a non-empty set of safe relative paths; read-only types require an empty set. |
| C4 | No `dict[str, Any]` (or `Any`) in authoritative fields; parameter values use exact JSON-native, non-float types. |
| C5 | P1.1-009 gets an invariant: task/family/lineage/split identity cannot change across manifest versions (recorded in `CURRENT_PHASE.md`). |

| D8 | **ObligationId deferral to SIN-P1.1-003: approved** (no consumer in 002 after ADR-0004). |
| D7 | **Approved.** `TaskType` = §20.1 values + `comprehension` (master §9 T1 lists Comprehension as a task type). Read-only (empty edit scope): `comprehension`, `spec_task`. Mutating (non-empty safe edit scope): `spec_to_rtl`, `completion`, `modification`, `debug`, `testbench`, `assertion`. |
| C6 | Implementation note for C4: exact scalars use Pydantic strict types, `ExactScalar = StrictInt \| StrictStr \| StrictBool`, so that `True`/`1`/`"1"` are never coerced into one another in identity-bearing data. |

## Scope
- In scope:
  - `src/sindri/schemas/__init__.py`, `src/sindri/schemas/_base.py`: a shared base model with `extra="forbid"`, `frozen=True`, strict types, and a required `schema_version: Literal[1]`. The base also contains a recursive validator that rejects binary floats anywhere in the record (D5).
  - `src/sindri/schemas/task.py`, `TaskManifest`:
    - Identity: `task_id: TaskId`, `family_id: FamilyId`, `lineage_id: LineageId`, `variant_id: VariantId`.
    - Versioning: `manifest_version: int ≥ 1`, `supersedes: ContentId | None`. `None` if and only if `manifest_version == 1`.
    - `authority_mode: AuthorityMode`: required, no default.
    - `split: Split` (`train` | `dev` | `final`): required, no default.
    - `task_type: TaskType` (D7: §20.1 values + `comprehension`).
    - `source`: a discriminated union on `kind`, with kind-specific required fields:
      - `repo_cut`, `commit_feature`, `commit_fix`: `repo`, `commit`;
      - `mutation`: parent `task_id`, operator;
      - `generator`: generator ID and version;
      - `use_case`: intake reference.
    - `rights: SourceRights` (C2), required for every source kind. All fields are required with no defaults:
      - `licence` (SPDX identifier, or `null` only with a `written_agreement_ref`);
      - `written_agreement_ref`;
      - `training_allowed: bool`, `evaluation_allowed: bool`, `redistribution_allowed: bool`, `customer_restricted: bool`.
    - `golden_hash: ContentId | None`: required for `reference_behavior`.
    - `contract_id: ContractId`, `approved_contract_hash: ContentId`.
    - `allowed_edit_paths: tuple[str, ...]` (C3):
      - each entry is a relative POSIX path with no `..`, no absolute paths and no empty segments;
      - entries are unique;
      - non-empty for mutating types, empty for read-only types.
    - `requirement_ids: tuple[RequirementId, ...]`: non-empty, unique.
  - `src/sindri/schemas/requirement.py`, `Requirement`:
    - Identity: `task_id: TaskId`, `requirement_id: RequirementId`.
    - Versioning: `requirement_version: int ≥ 1`, `supersedes: ContentId | None` (C1).
    - `source_ref: str` (non-empty).
    - `original_text: str` (verbatim, non-empty) and `normalized_semantics: str` (non-empty). These are distinct fields, and neither is derived from the other.
    - `legal_environment: tuple[EnvironmentRule, ...]`, where each rule has `text` and `source_ref`.
    - `assumptions: tuple[Assumption, ...]`, where each has `text` and a required `source_ref`.
    - `applicability`: either `AllSupportedConfigs` or `ParameterScope`. `ParameterScope` maps a parameter name (`[A-Z][A-Z0-9_]*`) to a non-empty tuple of `ExactScalar` values (C4/C6: `StrictInt | StrictStr | StrictBool`; no float, no `Any`, no coercion).
    - `mandatory: bool`: required, no default.
    - `disposition: RequirementDisposition` (D4).
    - No `obligation_ids` (ADR-0004).
  - `src/sindri/core/ids.py`: add `FamilyId`, `LineageId`, `VariantId` (pattern `[a-z0-9]+(?:[-_][a-z0-9]+)*`, which allows the §20.1 hyphens) and `ContractId` (`ct_…`). Additive only.
  - Tests under `tests/contract/` and `tests/unit/`.
- Allowed paths: `src/sindri/schemas/`, `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/`, `docs/REPO_MAP.md`, `components/schemas.yaml`, this packet, `docs/handoffs/SIN-P1.1-002.md`.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created. Fixtures must not use real final-eval family names.
- Other forbidden paths: every `src/sindri/` package other than `schemas` and `core/ids.py`; existing ID patterns in `core/ids.py`; `core/status.py`; `canonical_json_id()` behaviour.

## Non-goals
- No `Observation`, `EvaluationPolicy`, `CandidateManifest`, `Finding`, `EpisodeState`, `Contract` or `VerificationPlan` models; no `ObligationId`.
- No storage, registry, lifecycle state, lineage service or split-assignment logic (P1.2, P2.6). The manifest *carries* a split; it does not *decide* it.
- No cross-record checks that need two or more records (cross-version identity, family-level split consistency, requirement-ID resolution). Those are SIN-P1.1-009 / P2.6.
- No JSON Schema export (P1.1-G). No budgets (D6).
- No defaults that invent authority, split, lineage, rights, edit scope or mandatory status.

## Interfaces touched
- Schemas: new `TaskManifest` v1, `Requirement` v1.
- Tool APIs: none. DB/migrations: none.
- External dependencies: none new.

## Acceptance criteria
Positive:
- [ ] The §20.1 and §20.9 examples, adapted to D1–D7 and C1–C4, validate and round-trip (model → JSON → model) identically.
- [ ] Every source kind validates with its required fields.
- [ ] A rights combination with training disallowed, evaluation allowed, redistribution disallowed and customer-restricted validates.
- [ ] A read-only task with empty edit scope validates; a mutating task with safe paths validates.
- [ ] A record's canonical content ID is stable across key order and changes when any field changes.

Negative (each a separate test):
- [ ] Missing `authority_mode`, `split`, `family_id`, `lineage_id`, `variant_id`, `rights` (or any rights field), or `mandatory` → rejected. No silent defaults.
- [ ] Unknown field at any nesting level → rejected, including `obligation_ids` on Requirement (ADR-0004).
- [ ] Wrong `schema_version` → rejected.
- [ ] `reference_behavior` without `golden_hash` → rejected.
- [ ] Source kind missing its required fields → rejected.
- [ ] Versioning: version > 1 without `supersedes`, or version 1 with it → rejected (both records).
- [ ] Edit scope:
  - mutating type with empty scope → rejected;
  - read-only type with non-empty scope → rejected;
  - absolute path, `..`, empty segment or duplicate entry → rejected.
- [ ] Duplicate `requirement_ids` → rejected.
- [ ] `original_text` or `normalized_semantics` empty → rejected.
- [ ] Assumption or environment rule without `source_ref` → rejected.
- [ ] Unknown disposition, split, task type or source kind → rejected.
- [ ] A binary float anywhere, at any depth (including inside `ParameterScope` values), → rejected.
- [ ] `ParameterScope` values are not coerced: `"8"` stays a str, `True` stays a bool and never matches `1` (C6).
- [ ] Non-JSON-native or `Any`-typed authoritative values (e.g. a nested dict where a typed model is expected) → rejected.
- [ ] Records are immutable: attribute assignment raises.

Planted-bug checks (run, record in the handoff, then revert):
- [ ] Giving `split` a default makes the suite fail.
- [ ] Allowing extra fields makes the suite fail.
- [ ] Defaulting `training_allowed=True` makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; the import-boundary test covers `schemas`.
- [ ] `docs/REPO_MAP.md` and `components/schemas.yaml` (from the component template) updated.
- [ ] Handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/{__init__,_base,task,requirement}.py`, `tests/contract/__init__.py`, `tests/contract/test_task_manifest.py`, `tests/contract/test_requirement.py`, `tests/contract/examples/{task_manifest,requirement}.json`, `tests/unit/test_ids.py` (new ID types), `components/schemas.yaml`, `docs/REPO_MAP.md`. If this changes materially, stop and ask the coordinator.

## Status
`ready` (coordinator, 2026-10-04). All decisions D1–D8 and C1–C6 are final (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
