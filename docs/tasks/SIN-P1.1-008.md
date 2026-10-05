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
- Owner: coding agent (Claude Code), assigned 2026-10-05
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-008`

## Dependencies
- Required completed tasks: SIN-P1.1-006 and SIN-P1.1-007 (verified)
- Required schemas/contracts: all of `sindri.schemas`, `sindri.core.ids` (`canonical_json_bytes`, `canonical_json_id`); read-only use

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

## Coordinator decisions (PR #22, 2026-10-05; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| S1 | **Accepted, with byte-scope clarification.** For every top-level record and every nested discriminated-union variant, three paths each return an equal record with the same `content_id()`: `model_validate_json(model_dump_json(r))`, `model_validate(model_dump(mode="json"))`, `model_validate_json(canonical_json_bytes(model_dump(mode="json")))`. "Byte-identical on the second pass" applies to bytes **re-emitted by the same serializer from the parsed model** (transport → transport, canonical → canonical). Arbitrary incoming bytes, whitespace, key order or `-0` need not be reproduced. |
| S2 | **Accepted.** A round trip must preserve `content_id()`. |
| S3 | **Contract accepted; test amended.** `Record.content_id()` is defined as `canonical_json_id(record.model_dump(mode="json"))`; `model_dump_json()` is transport serialization, not the identity contract. Tests assert, for every catalog record:<br>• `record.content_id() == canonical_json_id(record.model_dump(mode="json"))`;<br>• canonical bytes are stable under mapping-key permutation and formatting changes;<br>• a transport round trip preserves the record and its content_id.<br>`model_dump_json() != canonical_json_bytes(…)` is **not** a permanent invariant: they differ today, but a future serializer could coincide without changing the contract. A representative fixture may *document* today's difference, but must not define correctness. |
| S4 | **Product change rejected.** No `mode="before"` version gate in verified `_base.py`. The current StrictInt + `schema_version == 1` rejection is sound; a v2-shaped record raising both `schema_version` and `extra_forbidden` errors is just multiple validation failures. Tests assert that unsupported/malformed `schema_version` is rejected and that the error set **includes** the schema-version failure, not that it is the only error. |
| S5 | **Accepted.** A v1 reader only; unknown schema versions are rejected; no dispatch registry. |
| S6 | **Accepted, with terminology fix.** Every P1.1 top-level record has `schema_version = 1`. TaskManifest, Requirement and EvaluationPolicy additionally have **domain revision chains** (`manifest_version`, `requirement_version`, `policy_version` + `supersedes`); the others do not. "Version > 1" tests keep `schema_version = 1` and increment the **domain revision version**. They are never called schema version 2. The catalog locks this inventory. |
| S7 | **Accepted.** Typed IDs, enum members, required-null keys, empty tuples and configurations, and discriminated-union classes survive the round trip. |
| S8 | **Accepted.** Nested floats, and NaN/Infinity tokens where the parser admits them, are rejected by the authoritative model before becoming record state. |
| S9 | **Accepted.** Driven by a typed field inventory. `ExactScalar` positions are the intentional exception: bool, int and string are three distinct valid JSON scalar choices there. |
| S10 | **Accepted.** `content_id()` is invariant to JSON **object key** order at every depth. This applies to mapping keys only, never to arrays or tuples. |
| S11 | **Option (a); no ADR-0007.** No global canonical-order validators and no silent sorting. `ContentId` identifies the **exact authoritative record**, not a semantic-equivalence class. Object key order and whitespace are presentation noise and are canonicalized; **array order is part of the JSON value and stays identity-bearing**, unless a specific record defines a separate semantic hash. The architecture already shows the split: `CandidateManifest.source_hash` gives the file set an order-independent identity while the manifest's `content_id()` identifies the exact record, and `Configuration.assignment_key()` compares assignment sets while the policy's `content_id()` identifies the exact representation. 008 does **not** classify the 31 tuple fields; it pins the rule:<br>• mapping order does not affect `content_id`;<br>• sequence order **does** affect exact record identity by default;<br>• specialized semantic identities (`source_hash`, `assignment_key`) may intentionally ignore order.<br>009 and P1.2 may compare membership or specialized hashes where a rule needs it. |
| S12 | **Accepted.** The complete fixture and generated-variant catalog, with existing hash constructions re-checked after the round trip. |
| S13 | **Accepted.** 008 only proves that `model_json_schema()` generates; exported/checked-in schema equivalence stays in P1.1-G. |
| S14 | **Accepted.** No migration framework. |
| S15 | **Deferred to P1.2; no xfail in 008.** Duplicate member names are an *ingest-byte parsing* concern, not a property of a built record. **Hard P1.2 requirement:** the authoritative evidence-store ingest boundary (which owns any strict JSON loader) rejects duplicate object member names, NaN/Infinity and malformed bytes **before** model validation, and proves it with its own tests. 008's `model_validate_json()` tests cover repository-generated, known-good transport round trips only. They do not authorize using Pydantic's parser directly on arbitrary evidence-store bytes. |
| S16 | **Deferred to P1.2.** No global integer constraint in P1.1. P1.2 chooses storage/interop representations that preserve integers exactly, or rejects out-of-range values explicitly at that boundary; authoritative records are never silently narrowed. |
| S17 | **Accepted.** No Unicode normalization; text is preserved verbatim, and NFC/NFD-different strings may have different content_ids. Pinned by a property test. |

**Resulting scope:** with S4 rejected and S11 = (a), **008 is tests and docs only**. No edits to verified schema modules or `_base.py`, no ADR-0007, no migration framework, no strict ingest loader.

## Scope (final; tests and docs only)
- In scope, tests:
  - `tests/contract/_record_catalog.py` (helper): one entry per top-level record giving its fixture, model, generated union variants and domain-revision fields (S6).
  - `tests/contract/test_round_trip.py`: S1, S2, S7 and S12 over every record and union variant.
  - `tests/contract/test_identity_encoding.py`:
    - S3: the canonical identity contract per record;
    - S10: the mapping-key permutation property;
    - S11: exact-record sequence order, with representatives: `CandidateManifest.files` reordered changes `content_id` but not `source_hash`; `TaskManifest.requirement_ids` reordered changes `content_id`; `Configuration.assignment_key()` is order-independent;
    - S17: Unicode NFC/NFD property;
    - hash constructions re-checked after the round trip.
  - `tests/contract/test_schema_versioning.py`: S4 (schema-version error *present*), S5, S6 domain-revision chains, S13 schema generation.
  - `tests/contract/test_strict_deserialization.py`: S8 and S9 via the typed field inventory, with the `ExactScalar` exception.
- Allowed paths: `tests/contract/`, `tests/unit/`, `components/schemas.yaml` (invariant/doc additions only), `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-008.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- `src/sindri/schemas/*.py`, including `_base.py`: no product edits (S4, S11).
- `src/sindri/core/ids.py`: no strict loader (S15 → P1.2) and no identity-encoding change.
- No change to any hash construction (`candidate_file_set_v1`, `observation_execution_key_v1`, canonical JSON). No ADR-0007.
- Hidden evaluator/final-eval paths: none.

## Non-goals
- No cross-record semantics (that is SIN-P1.1-009; table below).
- No version-dispatch registry, migration framework, version gate or canonical-order validators (S4, S5, S11, S14).
- No exported JSON Schemas (P1.1-G).
- No evidence-store ingest, strict JSON loader, duplicate-key test or integer bounds (S15, S16 → P1.2).

## Follow-ups owned by P1.2 (recorded here)
- **Authoritative ingest boundary (S15):** reject duplicate object member names, NaN/Infinity and malformed bytes before model validation, with its own tests.
- **Integer storage/interop (S16):** preserve integers exactly, or reject out-of-range values explicitly at the storage boundary. Never narrow silently.

## Single-record (008) vs cross-record (009)
| 008: one record at a time | 009: needs two or more records |
|---|---|
| round trip, identity, key-order independence | hashes matching the records they name (`candidate_manifest_hash`, `policy_hash`, `observation_hash`, `budget_hash`, `finding_hash`) |
| `schema_version` strictness; domain-revision chain shape (revision 1 ⇔ no `supersedes`) | supersession chains resolve and keep identity (C5: task/family/lineage/split constant) |
| strict scalars, float rejection after JSON | Observation ↔ policy check/configuration/exception consistency; Finding citations bound to the exact candidate; probe→terminal prohibition; verdict mapping vs `confirming_status` |
| mapping-order independence and exact-record sequence order | EpisodeState chains (edges, resume-to-recorded-state, monotonic accounting, constant budget/policy/solver hashes) |
| hash vectors re-checked after round trip | approved mandatory requirements enforced per configuration after exceptions (PR #9) |

## Interfaces touched
- None. Tests and docs only.

## Acceptance criteria
Positive:
- [x] S1/S2: three round-trip paths per record and per union variant return equal records with equal content_ids. Re-emitting with the same serializer from the parsed model is byte-identical (transport → transport, canonical → canonical).
- [x] S3: for every catalog record, `content_id() == canonical_json_id(model_dump(mode="json"))`; canonical bytes are stable under key permutation and formatting changes.
- [x] S7: typed IDs, enum members, `null` required keys, empty tuples (incl. zero-parameter `assignments: []`) and union variant classes survive.
- [x] S10: content_id is invariant under object-key permutation at every depth (property test).
- [x] S11: `CandidateManifest.files` reordered changes `content_id` but not `source_hash`; `TaskManifest.requirement_ids` reordered changes `content_id`; `Configuration.assignment_key()` is order-independent.
- [x] S6: every record has `schema_version = 1`; TaskManifest, Requirement and EvaluationPolicy round-trip domain revision > 1 with `supersedes`; the inventory of domain-revision vs non-revision records is locked.
- [x] S12: every fixture and generated variant passes; hash constructions re-verified after the round trip.
- [x] S13: `model_json_schema()` generates for all nine records.
- [x] S17: NFC- and NFD-encoded versions of the same text survive verbatim and yield different content_ids.

Negative:
- [x] S4/S5: `schema_version` 0, 2, 99, −1, absent, `true`, `1.0` and `"1"` are rejected for every record, and the error set includes the schema-version failure (other errors may also be present).
- [x] S8: a float (and NaN/Infinity where admitted) at any depth of any record is rejected after JSON parsing.
- [x] S9: `true`, `1.0` and `"1"` are rejected for every authoritative int; `1` and `"true"` for every authoritative bool; `ExactScalar` positions keep `true`, `1` and `"1"` distinct.

Planted-bug checks (run, record in handoff, revert):
- [x] Dumping with `exclude_none=True` in the round-trip helper makes the suite fail (nullable required keys).
- [x] Changing `Record.content_id()` to hash `model_dump_json()` bytes is caught by the **canonical-identity equality/vector tests**.
- [x] Accepting `schema_version` 2 as 1 makes the suite fail.
- [x] Removing the float walker (`_reject_floats`) makes the suite fail.
- [x] Making the canonical encoding sort array elements (order-insensitive identity) makes the S11 sequence-order tests fail.

General:
- [x] `ruff`, `mypy --strict`, full `pytest` green; contract tests green.
- [x] Handoff written (including the P1.2 follow-ups); report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`tests/contract/_record_catalog.py`, `tests/contract/test_round_trip.py`, `tests/contract/test_identity_encoding.py`, `tests/contract/test_schema_versioning.py`, `tests/contract/test_strict_deserialization.py`, plus doc updates (`components/schemas.yaml`, `docs/REPO_MAP.md`). No product files.

## Status
`review` (authoritative status: `implementation/task_board.yaml`). Decisions S1–S17 implemented as written: tests and docs only.

## Completion evidence
- Files changed (tests and docs only): `tests/contract/_record_catalog.py`, `tests/contract/test_round_trip.py`, `tests/contract/test_identity_encoding.py`, `tests/contract/test_schema_versioning.py`, `tests/contract/test_strict_deserialization.py` (all new), `components/schemas.yaml` (INV-SER-001…004, related doc), `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff. **No `src/` file changed.**
- Tests run/results: `ruff` clean; `mypy --strict` clean (18 files); `pytest`: 1572 passed, 8 skipped (773 new 008 tests); contract: 1456 passed.
- Acceptance evidence:
  - **Catalog:** 10 fixtures plus 29 generated variants (39 entries), each validated at import, covering every record and every union branch:
    - 6 source kinds, the read-only edit scope and revision 2 (TaskManifest);
    - all-supported-configs, exact scalars and revision 2 (Requirement);
    - the zero-parameter `cfg_default` policy with a prove check, and revision 2;
    - first, reconstructor and oracle-explorer candidates;
    - sim-pass, synth-pass, equivalence-pass, tool-error-no-report and prove-inconclusive Observations;
    - component and human producers;
    - existing-policy-check, formal-probe and dropped transitions;
    - WAITING→PLAN with a candidate-less job, ABORTED, and a PREPARE head;
    - zero-limit budgets.
  - **S1/S2:** three paths are equal with an equal content_id for all 39 entries; same-serializer re-emission is byte-stable (transport and canonical).
  - **S7:** a recursive type fingerprint (model classes, typed IDs, enums, scalars, tuples) is identical after the round trip, and every key, including nulls, is present at every depth in both dump forms.
  - **S3:** `content_id() == canonical_json_id(model_dump(mode="json"))` for all 39 entries, plus an independent byte-level `hashlib` vector for EpisodeBudget's content_id. Transport/canonical inequality is not asserted.
  - **S10:** 5 seeded key permutations × mixed formatting per entry leave identity unchanged.
  - **S11:** `files` reordered changes `content_id` but not `source_hash`; `requirement_ids` reordered changes `content_id`; `assignment_key()` is order-independent while policy identity is not.
  - **Hash re-checks:** source hash and execution key are recomputed after the round trip; the `candidate_file_set_v1` byte vector is re-pinned.
  - **S4/S5/S6:**
    - `schema_version` 0, 2, 99, −1, `true`, `1.0`, `"1"`, `null` and absent are rejected for all nine records, with the version failure present in the error set;
    - v2-shaped records fail loudly;
    - the revision inventory is locked (exactly three records);
    - revision 2 with `supersedes` keeps `schema_version` 1 and round-trips;
    - the chain shape is enforced.
  - **S8:** a float injected at **every leaf** of every entry is rejected with its **exact JSON path**; NaN, Infinity and −Infinity tokens (which Pydantic's parser admits) are rejected.
  - **S9:** every authoritative int rejects `true`/float/numeric string; every bool rejects `1`/`0`/`"true"`; ExactScalar positions keep `true`, `1` and `"1"` distinct.
  - **S13:** `model_json_schema()` generates for all nine records. **S17:** NFC and NFD text survive verbatim and differ in identity.
  - Planted bugs, each caught and restored, with `src/` verified clean afterwards:
    - `exclude_none=True` in the round-trip helper → 137 failures;
    - `content_id` hashing `model_dump_json()` bytes → 41, caught by the canonical-identity contract (39) and the byte-level vector (plus one budget test);
    - `schema_version` 2 accepted → 21;
    - float walker removed → 167;
    - canonical encoding sorting arrays → 10, including all three S11 sequence-order tests.
- Known limitations:
  - The S9 int/bool walkers assert rejection only: for Observations an injected value can also fail via the execution-key mismatch, so the reason is not pinned per leaf. The S8 float walker *does* pin path and reason.
  - Duplicate-key, NaN and malformed-byte rejection at authoritative ingest, and integer storage range, are P1.2 requirements (see below).
- Handoff/next action: `docs/handoffs/SIN-P1.1-008.md`.
