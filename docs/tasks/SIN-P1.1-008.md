# SIN-P1.1-008 — Serialization and schema-versioning tests

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
Prove, for the complete P1.1 record set, that

```
authoritative record → serialize → transport/storage bytes → parse later
  → same exact meaning, same strict types, same content identity,
    no silent version reinterpretation
```

for **TaskManifest, Requirement, EvaluationPolicy, CandidateManifest, Observation, Finding,
FindingTransition, EpisodeBudget and EpisodeState**, including every nested discriminated union.
This is not "can Pydantic dump JSON": it is a set of executable guarantees that the evidence store
(P1.2), the controller (P1.5) and every later consumer can rely on.

## Why / architecture references
- Master architecture: §4 principle 9 (results bind to exact artifacts); §8 F2 (store by content hash; never edit history); §8.7 (authority records); §8.8–8.9 (complete keys; caches content-addressed by all relevant inputs); §20 record examples.
- P1.1 breakdown (`CURRENT_PHASE.md`): "SIN-P1.1-008 — round-trip of every master §20 example; schema_version stored; old versions never silently reinterpreted".
- ADRs: ADR-0001 (stack), ADR-0002, ADR-0004, ADR-0005, ADR-0006.
- Phase/subphase: P1.1; order: {006, 007} → **008** → 009 → P1.1-G.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-008`

## Dependencies
- Required completed tasks: SIN-P1.1-006 and SIN-P1.1-007 (verified)
- Required schemas/contracts: all of `sindri.schemas`, `sindri.core.ids` (`canonical_json_bytes`, `canonical_json_id`)

## Facts established by read-only probes on `main` `135a54b` (before drafting)
| # | Observation | Consequence |
|---|---|---|
| P1 | `model_dump_json()` ≠ `canonical_json_bytes(model_dump(mode="json"))` | Pydantic transport JSON is **not** the identity encoding (S2, S3) |
| P2 | `model_validate_json(model_dump_json(r)) == r` and the content_id is equal (CandidateManifest example) | A round-trip guarantee is achievable today (S1) |
| P3 | Reordering `CandidateManifest.files` keeps `source_hash` equal but **changes `content_id()`** | Identical candidate content can have two record identities (S11) |
| P4 | Reordering `TaskManifest.requirement_ids` changes `content_id()` | The same applies to every set-like tuple (S11) |
| P5 | **Duplicate JSON keys are accepted, and the last one wins** | Transport bytes can be ambiguous across parsers (S15) |
| P6 | `schema_version` `2`, `true`, `1.0` and `"1"` are all rejected | v1 strictness already holds (S4) |
| P7 | A v2 record with a new field yields **two** errors (version + extra field) | The version failure is loud but not isolated (S4) |
| P8 | Integers beyond 2⁵³ (and 2⁶³) are accepted | An interop/storage range question (S16) |

## Open decisions (coordinator decides; the agent recommends)

| ID | Question | Agent recommendation |
|---|---|---|
| S1 | **Round-trip guarantee.** | For every record and every variant of every discriminated union, three paths must each return an **equal** record with an **equal `content_id()`**: (a) `model_validate_json(model_dump_json(r))`; (b) `model_validate(model_dump(mode="json"))`; (c) `model_validate_json(canonical_json_bytes(model_dump(mode="json")))`. A second round trip must be byte-identical to the first (no drift). |
| S2 | **Must the round trip preserve `content_id()`?** | **Yes, always.** This is the core guarantee: identity survives storage and transport. |
| S3 | **Canonical vs transport encoding.** | The repository *already* defines the identity encoding as `canonical_json_bytes(record.model_dump(mode="json"))` (`Record.content_id()`, `core/ids.py`). It is **not** Pydantic's emitted JSON. Transport JSON is *any* JSON that parses to an equal record. Tests assert P1 explicitly, so nobody later assumes `model_dump_json()` bytes are identity. **No new public API** (e.g. `Record.canonical_bytes()`) until a consumer exists (P1.2). |
| S4 | **`schema_version` strictness and loud failure.** | v1 is already strict (P6). Proposal: add a small **version gate** to `Record` (a `mode="before"` check) that rejects any `schema_version` other than strict integer 1 *before* structural validation, with one specific error naming the record type and version (for example "unsupported TaskManifest schema_version 2; this code reads 1"). This makes a v2 record fail with one clear reason instead of version + extra-field noise (P7). **This edits the verified `_base.py`**, hence a decision. *Alternative:* no product change; tests only assert that the version error is present among the errors. |
| S5 | **Historical versions / dispatch boundary.** | **v1 only.** 008 proves that unknown versions (0, 2, 99, negative, absent) are rejected; it introduces **no version-dispatch registry** and no parsing of older or newer shapes. |
| S6 | **Versioned vs non-versioned records.** | Lock the inventory with a test: **versioned** (`*_version` + `supersedes`): TaskManifest, Requirement, EvaluationPolicy. **Non-versioned immutable**: CandidateManifest, Observation, Finding, FindingTransition, EpisodeBudget, EpisodeState (snapshots chain by `previous_state_hash` / `previous_transition_hash`, which is not supersession). Round-trip tests cover version > 1 with `supersedes` for each versioned record, and assert that non-versioned records have no `supersedes`/`*_version` field. |
| S7 | **Exact preservation after JSON.** | After parsing, assert: typed IDs come back as their typed classes (not bare `str`); enums as enum members; nullable required keys are present as `null` in every dump (no `exclude_none` anywhere); empty tuples stay empty tuples (e.g. zero-parameter `assignments: []`); each discriminated union yields the same variant class. |
| S8 | **Floats after deserialization.** | JSON numbers with a fraction or exponent (`1.0`, `1e3`, `-0.0`), and the non-standard tokens `NaN`, `Infinity` and `-Infinity` if the parser admits them, are rejected **at every nesting level** of every record, with the records' float message. Driven by a generic walker over each fixture. |
| S9 | **Strict scalars after JSON.** | For every authoritative integer: JSON `true`, `1.0` and `"1"` are rejected. For every authoritative boolean: `1`, `0` and `"true"` are rejected. For `ExactScalar` positions: `true`, `1` and `"1"` round-trip as three distinct values. Driven by a field inventory, not hand-picked samples. |
| S10 | **`content_id()` vs input key order.** | A property test permutes the keys of every mapping at every depth of every fixture; the content_id is unchanged. |
| S11 | **Collection ordering and identity.** The probes show that every tuple's order currently changes `content_id()` (P3, P4); 31 tuple fields exist (inventory below). | Classify each tuple field as **ordered** (order is meaning) or **set-like** (order is accidental). Proposed ordered fields: `Observation.diagnostics` (emission order; truncation keeps the first 200), `SimulationReport.test_results` and `FormalReport.property_results` (execution order matters for partial FAILs). Every other field is set-like. Options for set-like fields:<br>(a) leave as is, document that identity reflects producer order, and live with duplicate identities for equal content;<br>(b) **require canonical order**: validators *reject* (never silently sort) set-like tuples that are not in their declared canonical order, giving one identity per content;<br>(c) silently sort, rejected because it mutates input and breaks round-trip byte stability.<br>**Recommend (b)**, recorded as **ADR-0007 (canonical collection order)**. Now is the cheapest moment (no stored data yet). It edits verified schemas and fixtures, so **either** widen 008's allowed paths **or** split it into a separate task before 008. The coordinator chooses. |
| S12 | **Fixture coverage.** | Every existing fixture round-trips under S1–S10. The fixtures are task manifest, requirement, evaluation policy, candidate manifest, observation, finding, both finding transitions, episode budget and episode state. Generated variants also cover: the zero-parameter policy (`cfg_default`, `[]`); each source kind; each producer kind; both proposal kinds; each execution-report variant; WAITING with a candidate-less job; ABORTED. The three **hash vectors**, already pinned byte-for-byte by their own tests (`candidate_file_set_v1`, `observation_execution_key_v1`, record `content_id`), are re-checked after a round trip: the stored hash still equals the recomputation. |
| S13 | **JSON Schema in 008 vs P1.1-G.** | 008 only asserts that `model_json_schema()` **generates** for every record without error. Exporting, committing and checking exported schemas against models stays in **P1.1-G**. |
| S14 | **Migration framework.** | **None.** No speculative migration subsystem; the first real v2 change defines its migration with its consumer. |
| S15 | **Duplicate JSON keys** (derived from P5). | Pydantic accepts duplicate keys with last-wins, so the same bytes could mean different records to different parsers. Options:<br>(a) a strict loader `parse_json_strict(bytes)` in `core/ids.py`, rejecting duplicate keys, NaN and Infinity, used by tests and later by P1.2 ingest;<br>(b) defer to P1.2 as an explicit evidence-store ingest requirement, with 008 adding an `xfail(strict=True)` test "duplicate keys are rejected at authoritative ingest" that flips when P1.2 lands.<br>**Recommend (b)**: no consumer exists in P1.1. |
| S16 | **Integer range** (derived from P8). | Python and canonical JSON are exact for any integer, but JavaScript consumers lose precision above 2⁵³, and PostgreSQL `bigint` stops at 2⁶³−1 (P1.2). **Recommend:** record this as a P1.2 storage/interop requirement and constrain nothing in P1.1. *Alternative:* bound every authoritative integer to signed 64-bit now. |
| S17 | **Unicode normalization** (derived). | No normalization: text fields stay verbatim (`Requirement.original_text` must). Identity is byte-exact, so visually identical NFC and NFD strings have different content_ids. Record this as a documented property with a test, not a bug. |

### Tuple-field inventory (for S11)
| Record | Tuple fields (proposed class) |
|---|---|
| TaskManifest | `allowed_edit_paths` (set), `requirement_ids` (set) |
| Requirement | `legal_environment` (set), `assumptions` (set), `ParameterScope.parameters` (set by name), `ParameterValues.values` (set) |
| EvaluationPolicy | `configurations`, `Configuration.assignments`, `checks`, `Check.configuration_ids`, `environment_assumptions`, `obligations`, `Obligation.check_ids`, `exceptions`, `PolicyException.excludes` (all set) |
| CandidateManifest | `files` (set by path; already canonicalized inside `source_hash`, not inside `content_id`) |
| Observation | `diagnostics` (**ordered**), `evidence_refs` (set), `SimulationReport.expected_test_ids` (set), `SimulationReport.test_results` (**ordered**), `FormalReport.expected_property_ids` (set), `FormalReport.property_results` (**ordered**) |
| Finding | `correctness_citations` (set), `supporting_evidence` (set) |
| FindingTransition | `deciding_citations` (set), `DevelopmentProbeRequest.test_ids` / `property_ids` (set) |
| EpisodeState | `pending_jobs` (set by `job_id`) |

## Scope (written for the recommended options; finalized after decisions)
- In scope, tests:
  - `tests/contract/test_round_trip.py`: S1, S2, S7 and S12 over every record and union variant (fixture-driven plus generated variants).
  - `tests/contract/test_identity_encoding.py`: S3 (transport ≠ canonical), S10 (key-order property), S11 (ordered vs set-like behaviour per the decision), S17, and re-checking the hash vectors after a round trip.
  - `tests/contract/test_schema_versioning.py`: S4, S5, S6, plus `model_json_schema()` generation (S13).
  - `tests/contract/test_strict_deserialization.py`: S8 and S9, driven by a field-type inventory walker; the S15 `xfail(strict=True)` test.
  - `tests/contract/_record_catalog.py` (test helper): one entry per record with fixture, model, version-chain fields, ordered/set-like tuple map.
- In scope, product (**only if approved**):
  - S4: version gate in `src/sindri/schemas/_base.py`.
  - S11(b): canonical-order validators in the affected schema modules, regenerated fixtures and recomputed hash vectors in their tests, and `docs/adr/0007-canonical-collection-order.md`.
- Allowed paths (default, tests only): `tests/contract/`, `tests/unit/`, `components/schemas.yaml` (invariant additions), `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-008.md`, `implementation/task_board.yaml` (status-only governance state).
- Additional allowed paths **only if** S4 / S11(b) are approved: `src/sindri/schemas/*.py`, `tests/contract/examples/*.json`, `docs/adr/0007-*.md`.

## Forbidden paths / authority boundaries
- `src/sindri/core/ids.py`: no strict loader (S15 → P1.2) and no identity-encoding change.
- No change to any hash construction (`candidate_file_set_v1`, `observation_execution_key_v1`, canonical JSON).
- Hidden evaluator/final-eval paths: none.

## Non-goals
- No cross-record semantics (that is SIN-P1.1-009; list below).
- No version-dispatch registry and no migration framework (S5, S14).
- No exported JSON Schemas (P1.1-G). No evidence-store ingest or strict JSON loader (P1.2). No integer bounds (S16 → P1.2).

## Single-record (008) vs cross-record (009)
| 008: one record at a time | 009: needs two or more records |
|---|---|
| round trip, identity, key-order independence | hashes matching the records they name (`candidate_manifest_hash`, `policy_hash`, `observation_hash`, `budget_hash`, `finding_hash`) |
| version strictness, version-chain shape (v1 ⇔ no `supersedes`) | supersession chains resolve and keep identity (C5: task/family/lineage/split constant) |
| strict scalars, float rejection after JSON | Observation ↔ policy check/configuration/exception consistency; Finding citations bound to the exact candidate; probe→terminal prohibition; verdict mapping vs `confirming_status` |
| ordered vs set-like collection behaviour | EpisodeState chains (edges, resume-to-recorded-state, monotonic accounting, constant budget/policy/solver hashes) |
| hash vectors re-checked after round trip | approved mandatory requirements enforced per configuration after exceptions (PR #9) |

## Interfaces touched
- Default: none (tests only). Conditional: `Record` version gate (S4); canonical-order validators (S11).

## Acceptance criteria
Positive:
- [ ] S1: three round-trip paths per record and per union variant return equal records with equal content_ids; a second round trip is byte-identical.
- [ ] S7: typed IDs, enum members, `null` required keys, empty tuples and union variant classes survive.
- [ ] S10: content_id is invariant under key permutation at every depth (property test).
- [ ] S6: versioned records round-trip version > 1 with `supersedes`; the inventory of versioned vs non-versioned records is locked.
- [ ] S12: every fixture and generated variant passes; hash vectors are re-verified after a round trip.
- [ ] S13: `model_json_schema()` generates for all nine records.

Negative:
- [ ] S4/S5: `schema_version` 0, 2, 99, −1, absent, `true`, `1.0` and `"1"` are rejected for every record (and with one isolated version error if S4 is approved).
- [ ] S8: a float at any depth of any record is rejected after JSON parsing.
- [ ] S9: `true`, `1.0` and `"1"` are rejected for every authoritative int; `1` and `"true"` for every authoritative bool.
- [ ] S11: per the decision, either set-like reorders are *rejected* (b) or their identity effect is documented by tests (a); ordered fields keep order and identity.
- [ ] S3: `model_dump_json()` bytes are asserted to differ from the canonical bytes for at least one record (guarding against a false "this is the identity encoding" assumption).
- [ ] S15: the duplicate-key test is present as `xfail(strict=True)` referencing P1.2.

Planted-bug checks (run, record in handoff, revert):
- [ ] Dumping with `exclude_none=True` in the round-trip helper makes the suite fail (nullable required keys).
- [ ] Making `Record.content_id()` hash `model_dump_json()` bytes instead of canonical bytes makes the key-order property fail.
- [ ] Accepting `schema_version` 2 as 1 makes the suite fail.
- [ ] Removing the float walker (`_reject_floats`) makes the suite fail.
- [ ] If S11(b): removing one canonical-order validator makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; contract tests green.
- [ ] Handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`tests/contract/_record_catalog.py`, `tests/contract/test_round_trip.py`, `tests/contract/test_identity_encoding.py`, `tests/contract/test_schema_versioning.py`, `tests/contract/test_strict_deserialization.py`; plus the conditional product files under S4/S11.

## Status
`planned`. Draft for coordinator review; decisions S1–S17 open, notably S4 and S11 (both would edit verified schemas) and S15/S16 (deferrals to P1.2) (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
