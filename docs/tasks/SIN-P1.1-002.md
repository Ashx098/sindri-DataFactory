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
source rights, and requirements that keep the original wording separate from the normalized
semantics. Nothing about authority, split or lineage can be defaulted silently. Later records
(EvaluationPolicy, CandidateManifest, Observation) can then reference tasks and requirements without
inventing their shape.

## Why / architecture references
- Master architecture: §4 principles 8–9 and the authority rule; §8.7 authority records ("TaskManifest: task/version, authority mode, family/lineage, source rights, split, approved contract hash, allowed edits and budgets"; "Requirement: original wording, normalized semantics, legal environment, assumptions, applicability and disposition"); §9 T1–T5 (sources, lineage, split before generation); §9.1 authority modes; §11.6 requirement → obligation traceability; §20.1 and §20.9 examples.
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md` (001 → **002** → {003, 004} → …).
- ADRs/RFCs: ADR-0001 (stack), ADR-0002 (`AuthorityMode`, statuses).

## Owner / coordinator
- Owner: assigned by coordinator on approval
- Integrator: Avinash
- Reviewers: Avinash; RTL/DV reviewer for requirement semantics once assigned (role currently unassigned)

## Base
- Base branch: `main`
- Base commit: `main` at the time the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-002`

## Dependencies
- Required completed tasks: SIN-P1.1-001 (verified)
- Required schemas/contracts: `sindri.core.ids`, `sindri.core.status`

## Decisions needed before READY
The master architecture underdetermines or contradicts itself on these points. The agent recommends
an option for each; **the coordinator decides**. Approved choices are copied into Scope before the
packet is marked ready.

| ID | Question | Options | Agent recommendation |
|---|---|---|---|
| D1 | §20.1 puts `tier`, `evidence_level`, `difficulty` and `status_history` in TaskManifest; §8.7 lists only identity/authority/rights/split/contract/allowed edits/budgets. These fields change over a task's life (silver → quarantine, difficulty re-profiled every round). | (a) Follow §20.1 and put lifecycle fields in the manifest. (b) Manifest holds immutable identity and authority only (§8.7); lifecycle state lives in the task registry/event log (P1.2). | **(b).** An immutable record that holds mutable state invites in-place edits. A correction would be a new manifest version that supersedes the old one, so tier changes would create noise versions. |
| D2 | §20.1 IDs use hyphens (`family_id: stream-framing`, `variant_id: maxlen4-64_datasheet`), which the 001 `TaskId` pattern does not allow. There are no ID types yet for family, lineage, variant, contract, spec, suite or certificate. | (a) Add new typed IDs in `core/ids.py` (additive only; no existing pattern changes) that allow hyphens where §20.1 does. (b) Normalize §20.1 examples to underscores. | **(a), additive.** Existing 001 types and patterns stay frozen; new types: `FamilyId`, `LineageId`, `VariantId`, `ContractId` (`ct_…`), `ObligationId` (e.g. `sim_stall_01`). Spec/suite/certificate IDs are deferred to the tasks that create those records. |
| D3 | `RequirementId` is `R17`, unique only within one task. Other records must not confuse `R17` of two tasks. | (a) Requirements are referenced as the pair (`task_id`, `requirement_id`). (b) Make requirement IDs globally unique. | **(a).** It matches the master examples. `Requirement` carries `task_id`, and 009 cross-record tests enforce pair references. |
| D4 | Requirement `disposition` values: the master shows only `approved`; verification-forge rules require explicit `not_applicable`/`unsupported`; ambiguity can also be open. | Proposed enum: `proposed`, `approved`, `ambiguous`, `not_applicable`, `unsupported`, `rejected`. | Adopt it. Only `approved` requirements are eligible for obligations; `ambiguous` blocks qualification (master §10, §11.6). |
| D5 | Floats in identity-bearing fields (SIN-P1.1-001 follow-up). §20.1 `difficulty.pass_rate: 0.25` is a float. | (a) Forbid floats in TaskManifest and Requirement. (b) Allow them, accepting shortest-repr hashing. | **(a)** for these two records. This follows if D1(b) moves `difficulty` out. Record the rule for later records at P1.1-G. |
| D6 | Budgets (§8.7 lists them in TaskManifest; §8 F3 says budgets are fixed per experiment). | (a) Budgets in TaskManifest. (b) Budgets belong to the episode/experiment configuration (SIN-P1.1-007 EpisodeState). | **(b).** The same task must be run under different matched budgets (the A–E arms). TaskManifest keeps `allowed_edit_paths` only. |

## Scope (pending D1–D6; written for the recommended options)
- In scope:
  - `src/sindri/schemas/__init__.py`, `src/sindri/schemas/_base.py`: a shared frozen base model with `extra="forbid"`, `frozen=True`, strict types and a required `schema_version: Literal[1]`.
  - `src/sindri/schemas/task.py`, `TaskManifest`:
    - Identity: `task_id`, `family_id`, `lineage_id`, `variant_id`, `manifest_version` (int ≥ 1), `supersedes` (previous manifest's `ContentId` or `None` only when `manifest_version == 1`).
    - `authority_mode: AuthorityMode`, required, no default.
    - `split: Split` (`train` | `dev` | `final`), required, no default.
    - `task_type: TaskType` (master §20.1 values).
    - `source`: discriminated union on `kind` (`repo_cut`, `commit_feature`, `commit_fix`, `mutation`, `generator`, `use_case`), each with the fields its kind needs. Repo kinds require `repo`, `commit`, `licence`; `mutation` requires the parent task; `generator` requires generator ID and version; `use_case` requires an intake reference. Every kind requires a `rights` statement (training/evaluation use allowed).
    - `golden_hash: ContentId | None`, which must be present for `reference_behavior` tasks.
    - `contract_id: ContractId`, `approved_contract_hash: ContentId`.
    - `allowed_edit_paths: tuple[str, ...]`: relative POSIX paths, no `..`, non-empty.
    - `requirement_ids: tuple[RequirementId, ...]`: non-empty, unique.
  - `src/sindri/schemas/requirement.py`, `Requirement`:
    - `task_id`, `requirement_id`, `source_ref`.
    - `original_text` (verbatim, non-empty) and `normalized_semantics` (non-empty), kept as distinct fields.
    - `legal_environment`, `assumptions` (each with a source reference; no source-less assumption).
    - `applicability`: either `all_supported_configs` or an explicit parameter scope `{param: [values]}`.
    - `mandatory: bool` (required, no default).
    - `disposition: RequirementDisposition`.
    - `obligation_ids: tuple[ObligationId, ...]`: required non-empty when `approved` and `mandatory`; empty otherwise allowed.
  - `src/sindri/core/ids.py`: additive ID types per D2. No change to existing types or patterns.
  - Tests under `tests/contract/` and `tests/unit/`.
- Allowed paths: `src/sindri/schemas/`, `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/`, `docs/REPO_MAP.md`, `components/schemas.yaml`, this packet, `docs/handoffs/SIN-P1.1-002.md`.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created. Fixtures must not use real final-eval family names.
- Other forbidden paths: every `src/sindri/` package other than `schemas` and `core/ids.py`; existing ID patterns in `core/ids.py`; `core/status.py`.

## Non-goals
- No `Observation`, `EvaluationPolicy`, `CandidateManifest`, `Finding`, `EpisodeState` or `Contract` models.
- No storage, registry, lineage service or split-assignment logic (P1.2, P2.6). The manifest *carries* a split; it does not *decide* it.
- No cross-record checks that need other records (e.g. family-level split consistency across many manifests). That is SIN-P1.1-009 / P2.6.
- No JSON Schema export (P1.1-G).
- No defaults that invent authority, split, lineage, rights or mandatory status.

## Interfaces touched
- Schemas: new `TaskManifest` v1, `Requirement` v1.
- Tool APIs: none. DB/migrations: none.
- External dependencies: none new.

## Acceptance criteria
Positive:
- [ ] The §20.1 and §20.9 examples, adapted to the approved decisions, validate and round-trip (model → JSON → model) identically.
- [ ] Every source kind validates with its required fields.
- [ ] A manifest's canonical content ID is stable across key order and changes when any field changes (uses `canonical_json_id`).

Negative (each a separate test):
- [ ] Missing `authority_mode`, `split`, `family_id`, `lineage_id`, `variant_id`, `mandatory` or a source `rights` statement → rejected (no silent defaults).
- [ ] Unknown field at any nesting level → rejected.
- [ ] Wrong `schema_version` → rejected.
- [ ] `reference_behavior` without `golden_hash` → rejected.
- [ ] Source kind missing its required fields (e.g. `repo_cut` without `commit` or `licence`) → rejected.
- [ ] `manifest_version > 1` without `supersedes`, or `manifest_version == 1` with it → rejected.
- [ ] `allowed_edit_paths` empty, absolute, or containing `..` → rejected.
- [ ] Duplicate `requirement_ids` → rejected.
- [ ] `original_text` or `normalized_semantics` empty → rejected; the two are never auto-copied into each other.
- [ ] Assumption without a source reference → rejected.
- [ ] `approved` + `mandatory` requirement with no `obligation_ids` → rejected.
- [ ] Unknown disposition, split, task type or source kind → rejected.
- [ ] Float anywhere in either record → rejected (per D5).
- [ ] Records are immutable: attribute assignment raises.

Planted-bug checks (run, record in the handoff, then revert):
- [ ] Giving `split` a default makes the suite fail.
- [ ] Allowing extra fields makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; import-boundary test covers `schemas`.
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
`planned`. Draft for coordinator review; not ready (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
