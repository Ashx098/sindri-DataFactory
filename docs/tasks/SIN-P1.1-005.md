# SIN-P1.1-005 — Observation

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`Observation` exists as a strict, immutable record of **an attempted execution of one declared
EvaluationPolicy check** against one exact candidate: which exact candidate, under which exact
policy version, check and configuration, by which exact executor (action, profile, image, adapter
build), over which exact inputs (including seed and wall-time limit). It carries the raw
`ToolStatus`, typed proof of execution where the status makes a correctness claim, short typed
diagnostics, and content-addressed references to raw evidence. Findings cite it, the judge consumes
it, ReleaseManifests cite it and DatasetRecords inherit it, so everything above the tool layer
trusts only what is traceable to one of these.

## Why / architecture references
- Master architecture:
  - §4 principles 1 and 9;
  - §8 F1 (normalised status, summary, parsed details, raw logs, hashes of everything used; "the adapter checks that expected test IDs appear in the results"; typed tool `run_sim(candidate, test_ids, seed)`);
  - §8.7 (Observation definition; the repository invariant that pass/fail claims reference Observation IDs);
  - §8.8–8.9 (complete keys; no PASS reuse across candidate, tool image, parameter set or evaluator version; broad early invalidation);
  - §11.7 (each random run individually replayable); §11.10 (formal observations record mode, depth, assumptions, configuration);
  - §13 X3 (short, structured observations); §14 J2 (status taxonomy); §20.4 example (starting point only).
- Phase/subphase: P1.1; order: {003, 004} → **005** → {006, 007}.
- ADRs/RFCs: ADR-0002 (raw status never rewritten), ADR-0004, **ADR-0005** (Observation is check evidence; diagnostic and qualification results are separate types).

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash; DV/formal reviewer for execution-proof rules once assigned (role unassigned)

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main` (implementation waits for both; process rule from 003/004)
- Worktree: `../worktrees/SIN-P1.1-005`

## Dependencies
- Required completed tasks: SIN-P1.1-003 and SIN-P1.1-004 (both verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.policy` (`CheckKind`, `Visibility`, `FormalMode`; import only), `sindri.schemas.task.EditPath` (import only), `sindri.core.ids`, `sindri.core.status.ToolStatus`

## Coordinator decisions (PR #13, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| O1 | **Accepted, with ADR-0005.** Observation v1 is for declared EvaluationPolicy-check executions only. Waveform inspection, coverage queries, formal `cover` and ad-hoc undeclared queries use a separate result type, defined later by its first consumer. |
| O2 | **Accepted, amended.** Binding is `candidate_id` + `candidate_manifest_hash` (authoritative) + `source_hash` + `dependency_hash`. **`candidate_manifest_hash` is inside the v1 `execution_key`.** No cross-candidate cache reuse until P1.2 designs derived-observation provenance. |
| O3 | **Accepted.** `policy_id` + `policy_hash` + `check_id` + `configuration_id`. |
| O4 | **Accepted, amended.** `check_id`/`configuration_id` are always required; one Observation per (check, configuration) execution. **Random simulation: one seed per Observation.** The canonical API is `run_sim(…, seed)`, singular, and each random run must be atomic and replayable: status, duration, log, waveform, failure and key are per seed. |
| O5 | **Accepted, strengthened.** Executor identity is `action`, `tool_profile_id`, `tool_profile_hash`, `tool_image_digest`, `adapter_version` (human-readable) **and `adapter_hash: ContentId`**. The hash, not the version string, goes into `execution_key`, because a rebuilt "1.4" adapter must not keep the same key. |
| O6 | **Accepted, amended.** `execution_key` includes `candidate_manifest_hash`, `adapter_hash`, the singular `seed`, `evaluator_bundle_hash` and `wall_time_limit_ms` (construction below). **`evaluator_bundle_hash` is always required**: when a check uses no evaluator artifacts, it is the canonical hash of an empty evaluator bundle. One uniform invariant: every Observation binds its exact evaluator-side artifacts. |
| O7 | **Accepted, amended.** Typed execution reports. **Formal gets expected-property coverage like simulation's expected tests**: `expected_property_ids` vs checked properties, and PASS requires expected == checked, plus reached ≥ requested depth (BMC) or a closed proof (prove). **`EquivalenceRelationId` dropped**: no authoritative relation record consumes it, and the relation is already committed by policy, contract, evaluator bundle and golden. |
| O8 | **Accepted.** Typed compact diagnostics plus content-addressed logs, traces and reports; no `dict[str, Any]`. |
| O9 | **Accepted, amended.** `duration_ms` (integer) and a UTC `started_at`. **`wall_time_limit_ms` is a required execution input on every Observation** (and in `execution_key`), not a nullable field appearing only for TIMEOUT. |
| O10 | **Accepted.** Raw `ToolStatus` only; `INVALID_SUBMISSION`/`INVALID_TASK` stay judge-layer `CheckStatus`. |
| O11 | **Accepted, amended.** Status matrix with the universal wall-time field, and **no `quality` Observation in v1**: quality has no defined acceptance semantics (units, thresholds, library, corner), so a "quality PASS" would only mean "the report was produced". |
| O12 | **Accepted.** Immutable, non-versioned; a rerun is a new Observation. `observation_id` is the handle and `content_id()` the exact identity. |
| O13 | **Principle accepted; self-attested `producer` rejected.** A writer can put any string in a `producer` field. Authentication comes from evidence-store/gateway write authority and append-only event provenance (P1.2–P1.4). `adapter_version`/`adapter_hash`, profile and image already identify *what implementation* produced the semantics. |
| O14 | **Accepted.** Hidden-check Observation contents are protected and never reach solver context. |
| O15 | **Recorded semantic distinction (coordinator).** An Observation is the record of an *attempted* declared check execution, not proof that execution completed. PASS/FAIL require strong typed execution evidence. TOOL_ERROR, TIMEOUT, UNSUPPORTED and INCONCLUSIVE may be partial or may never have reached the candidate, so a TOOL_ERROR must not be required to prove that the check ran. |

### Derived details R1–R5: coordinator decisions on PR #13 (final review)
R1, R2, R4 accepted as proposed. R3 accepted **with a correction**; R5 accepted **with a follow-up**. Each item below states the final rule.
- **R1. Seed scope (accepted).** `seed: StrictInt | None` is a required key: **non-null for both `directed_sim` and `random_sim`** (the master API is `run_sim(candidate, test_ids, seed)` for all simulation, and every invocation stays reproducible), `None` for every other kind. One simulation invocation + one seed = one Observation.
- **R2. Action ↔ kind mapping (accepted as proposed)** (one-to-one, enforced in-record):

  | Check kind | Action |
  |---|---|
  | `integrity_scan` | `integrity_scan` |
  | `parse_elaborate` | `compile` |
  | `lint` | `lint` |
  | `synthesis` | `synth` |
  | `directed_sim`, `random_sim` | `run_sim` |
  | `formal` | `run_formal` |
  | `equivalence` | `check_equiv` |

  `quality` is excluded (O11).
- **R3. Report presence by status (accepted with correction):**
  - **PASS:** a report is mandatory and must be **complete**.
  - **FAIL:** a report is mandatory and **may be partial**, provided it contains sufficient candidate-attributed failure evidence. Example: test_1 PASS, test_2 FAIL, and the runner aborts, so tests 3–20 never run; that is still a valid FAIL.
  - **INCONCLUSIVE:** a formal or equivalence report is mandatory and must show why the proof or bound was not closed.
  - **TOOL_ERROR, TIMEOUT, UNSUPPORTED:** report optional or partial. Such a report can never be read as complete PASS/FAIL evidence, and the status cannot be inferred from it.
- **R4. Equivalence report (accepted):** `EquivalenceReport{proved: bool}`; the counterexample lives in `evidence_refs`. PASS: `proved = true`. FAIL: `proved = false` plus a `counterexample_trace` ref. INCONCLUSIVE: `proved = false` with no counterexample. The relation is committed by `policy_hash`, contract, `evaluator_bundle_hash` and golden artifacts, so no relation ID is needed.
- **R5. Empty evaluator bundle (accepted, with follow-up).** The canonical empty-bundle hash is defined by the task that defines evaluator-bundle construction (P1.4/P1.6). This record only requires a `ContentId` and never accepts `None`.
  - **Follow-up owned by P1.4/P1.6, recorded here:** the evaluator-bundle manifest must be the **authority for the expected inventory**. `Observation.expected_test_ids` must equal the bundle's committed test inventory, and `Observation.expected_property_ids` its committed property inventory.
  - This closes the remaining loophole in which a buggy adapter reports `expected = executed = [T1, T2, T3]` while the real bundle contains T4. In 005, expected == executed only proves completeness relative to what the adapter reports. Anchoring to the bundle belongs where the bundle manifest exists.

## Execution key (single implementation, recomputed in-record)
```
canonical_json_id({"kind": "observation_execution_key_v1",
  "candidate_manifest_hash", "source_hash", "dependency_hash",
  "policy_hash", "check_id", "configuration_id",
  "action", "tool_profile_hash", "tool_image_digest", "adapter_hash",
  "evaluator_bundle_hash", "seed", "formal_mode", "formal_depth",
  "wall_time_limit_ms"})
```
- **Execution request** (in the key): everything listed above.
- **Execution result** (never in the key): `observation_id`, `started_at`, `duration_ms`, `status`, `summary`, `diagnostics`, `log_ref`, `evidence_refs`, `execution_report`.
- `adapter_version`, `tool_profile_id`, `policy_id` and `candidate_id` are human-readable or lookup handles; the key uses their hash counterparts.

## Scope (final; R1–R5 decided on PR #13)
- In scope:
  - `src/sindri/core/ids.py`, additive only: `TestId` (e.g. `stall_stability_004`) and `PropertyId` (e.g. `R03_sva`). No `EquivalenceRelationId`.
  - `src/sindri/schemas/observation.py`:
    - `Observation` (`Record`, non-versioned), with these fields:
      - **binding:** `observation_id`, `candidate_id`, `candidate_manifest_hash`, `source_hash`, `dependency_hash`, `policy_id`, `policy_hash`, `check_id`, `configuration_id`, `check_kind`, `visibility`;
      - **executor:** `action`, `tool_profile_id`, `tool_profile_hash`, `tool_image_digest`, `adapter_version`, `adapter_hash`;
      - **inputs:** `evaluator_bundle_hash`, `seed`, `formal_mode`, `formal_depth`, `wall_time_limit_ms`;
      - **key:** `execution_key`;
      - **result:** `started_at`, `duration_ms`, `status: ToolStatus`, `summary`, `diagnostics`, `diagnostics_truncated`, `log_ref`, `evidence_refs`, `execution_report`.
    - Typed parts: `Diagnostic` (severity, category `candidate|evaluator|infrastructure`, optional code/path/line), `EvidenceRef` (kind `counterexample_trace|waveform|tool_report`, hash), `ObservationAction`.
    - Execution reports:
      - `SimulationReport`: `expected_test_ids`, `test_results` of `{test_id, outcome}`;
      - `FormalReport`: `mode`, `requested_depth`, `reached_depth`, `proof_closed`, `expected_property_ids`, `property_results` of `{property_id, outcome}`;
      - `EquivalenceReport`: `proved`;
      - `StructuralReport`: error/warning counts; synth adds latch/blackbox counts.
    - `observation_execution_key()`: the single implementation of the construction above.
  - In-record invariants:
    - key recomputation;
    - `check_kind ≠ quality`; action ↔ kind (R2); report variant ↔ kind;
    - seed rule (R1); formal mode/depth only on `formal`, with depth iff `bmc`;
    - `wall_time_limit_ms ≥ 1`;
    - the O11/R3 status matrix (below);
    - diagnostics cap of 200 with a truncation flag; summary ≤ 500 characters;
    - `started_at` format;
    - floats rejected (inherited).
  - Status matrix:
    - **PASS:**
      - complete report (mandatory);
      - sim: every expected test present exactly once with PASS;
      - formal: expected properties == checked, all PASS, reached ≥ requested (BMC) or `proof_closed` (prove);
      - equivalence: `proved`;
      - structural: zero errors;
      - in every case: no `error` diagnostics and no counterexample refs.
    - **FAIL:** a report is mandatory and may be partial (R3); it must contain a candidate-attributed failure locus:
      - sim: ≥ 1 test FAIL;
      - formal/equivalence: a counterexample ref;
      - structural: ≥ 1 candidate-category error.
    - **TOOL_ERROR:** ≥ 1 infrastructure diagnostic, and no candidate error, failing test or counterexample.
    - **TIMEOUT:** `duration_ms ≥ wall_time_limit_ms`, and no failure locus.
    - **INCONCLUSIVE:** formal or equivalence only; the report is mandatory and shows the unmet bound.
    - **TOOL_ERROR / TIMEOUT / UNSUPPORTED:** report optional or partial, and never counted as PASS/FAIL evidence.
    - **UNSUPPORTED:** ≥ 1 diagnostic whose code names the unsupported capability.
  - Tests under `tests/contract/`, with an adapted §20.4 fixture.
- Allowed paths: `src/sindri/schemas/observation.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-005.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none; fixtures use synthetic IDs and hashes only.
- Other forbidden paths:
  - verified records (`_base`, `task`, `requirement`, `policy`, `candidate`): import only;
  - existing ID patterns;
  - `core/status.py`: no new statuses.

## Non-goals
- No diagnostic/qualification result type (ADR-0005: first consumer defines it). No `quality` Observations (O11).
- No `producer` field and no signing (O13): authentication is write authority, P1.2–P1.4.
- No cross-candidate cache reuse or derived-observation provenance (O2: P1.2). No gateway, adapters, parsers, sandbox, golden logs or evaluator-bundle construction (P1.3/P1.4/P1.6).
- No judge logic or verdict mapping (P1.7). No solver projection (P1.5/P5).
- No Finding, EpisodeState, ReleaseManifest or DatasetRecord.

## Cross-record invariants deferred to SIN-P1.1-009
- `candidate_manifest_hash` is the `content_id()` of the CandidateManifest with `candidate_id`; `source_hash`/`dependency_hash` equal that manifest's.
- `policy_hash` is the `content_id()` of the EvaluationPolicy with `policy_id`; the policy's `task_id` equals the candidate's `task_id`.
- `check_id` exists in that policy; `configuration_id` is targeted by that check; the pair is not excluded by a policy exception.
- `check_kind`, `visibility`, `tool_profile_id` and the requested formal mode/depth equal the policy check's.
- `evaluator_bundle_hash` matches the bundle bound to the task's evaluator (once that record exists); for equivalence it commits to the task's `golden_hash`.
- Citations carry an `observation_id` and `content_id()` that agree.
- The P1.1-009 enforcement rule (PR #9) is evaluated over Observations of mandatory, non-quality, applicable checks.

## Follow-ups owned by later tasks (not 009)
- P1.4/P1.6, evaluator-bundle manifest (R5): the bundle commits to the expected test and property inventories, and `Observation.expected_test_ids` / `expected_property_ids` must equal them. Until then, 005 guarantees completeness only relative to the adapter-reported expectation.

## Interfaces touched
- Schemas: new `Observation` v1. IDs: additive `TestId`, `PropertyId`.
- Tool APIs: none (P1.4 adapters will emit this record). DB/migrations: none. External dependencies: none new.

## Acceptance criteria
Positive:
- [x] The adapted §20.4 example (FAIL, BMC, expected properties, a counterexample ref, `duration_ms`, `wall_time_limit_ms`, full bindings) validates, round-trips and re-serializes to identical JSON.
- [x] One valid Observation for each allowed status on representative kinds, including:
  - a sim PASS with every expected test passed;
  - a sim FAIL with a **partial** report (test_1 PASS, test_2 FAIL, remaining expected tests never ran) (R3);
  - a formal PASS with every expected property checked;
  - a TIMEOUT with no report;
  - a TOOL_ERROR with no report and an infrastructure diagnostic;
  - a formal INCONCLUSIVE with unmet depth;
  - an UNSUPPORTED with a capability code.
- [x] Two random-sim Observations differing only in seed have different execution keys.
- [x] `observation_execution_key` matches an independent byte-level `hashlib` vector and changes when any key input changes. It does **not** change with `observation_id`, `started_at`, `duration_ms`, `status`, `summary` or `log_ref`.

Negative (each a separate test):
- [x] Every field required (no defaults); unknown fields rejected at every level, including `producer`, `seeds`, `duration_s`, `tool`, `executed`.
- [x] A stored `execution_key` that disagrees with recomputation → rejected (wrong tag, unsorted, or one tampered input, e.g. a different `candidate_manifest_hash` or `adapter_hash`).
- [x] `check_kind: quality` → rejected; an action incompatible with the kind (R2) or a report variant incompatible with the kind → rejected.
- [x] Missing `evaluator_bundle_hash` or `None` → rejected (always required); `wall_time_limit_ms` missing or < 1 → rejected.
- [x] Seed violating R1 (missing on sim, present on non-sim) → rejected.
- [x] Sim PASS with a missing, extra, duplicated or non-PASS test → rejected.
- [x] Formal PASS with a missing, extra or non-PASS property; BMC `reached_depth < requested_depth`; prove PASS without `proof_closed` → rejected.
- [x] PASS or FAIL without a report → rejected; PASS with a partial report → rejected; FAIL with a partial report but **no** candidate-attributed failure → rejected (R3).
- [x] FAIL without a failure locus (per kind) → rejected.
- [x] TOOL_ERROR with a candidate error, failing test or counterexample, or without an infrastructure diagnostic → rejected.
- [x] TIMEOUT with `duration_ms < wall_time_limit_ms` or with a failure locus → rejected.
- [x] INCONCLUSIVE on a non-formal/non-equivalence kind, or with a met bound → rejected.
- [x] A `ToolStatus` outside the enum, or `INVALID_SUBMISSION`/`INVALID_TASK` → rejected.
- [x] More than 200 diagnostics, a blank or over-long summary, malformed `started_at`, float duration → rejected.
- [x] The record is immutable; there is no `supersedes` field.

Planted-bug checks (run, record in the handoff, revert):
- [x] Allowing TIMEOUT with a failing test ("timeout means fail") makes the suite fail.
- [x] Accepting sim PASS when executed tests ⊂ expected makes the suite fail.
- [x] Accepting formal PASS when checked properties ⊂ expected makes the suite fail.
- [x] Dropping `candidate_manifest_hash` or `adapter_hash` from the key makes the suite fail.
- [x] Making `evaluator_bundle_hash` nullable makes the suite fail.

General:
- [x] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [x] `components/schemas.yaml` gains Observation invariants (ADR-0005 boundary, execution key, status matrix, hidden protection); `docs/REPO_MAP.md` updated.
- [x] Handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/observation.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_observation.py`, `tests/contract/examples/observation.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Status
`review` (authoritative status: `implementation/task_board.yaml`). Decisions O1–O15 and R1–R5 implemented as written.

## Completion evidence
- Files changed:
  - `src/sindri/core/ids.py` (additive `TestId`, `PropertyId`; only docstring lines edited, no pattern changed);
  - `src/sindri/schemas/observation.py` (new), `src/sindri/schemas/__init__.py` (exports);
  - `tests/contract/test_observation.py` and `tests/contract/examples/observation.json` (new), `tests/unit/test_ids.py`;
  - `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff.
- Tests run/results:
  - `ruff` clean; `mypy --strict` clean (16 files);
  - `pytest`: 595 passed, 8 skipped, no warnings (165 Observation contract tests, 482 contract tests in total).
- Acceptance evidence:
  - The adapted §20.4 fixture is itself a **partial-report FAIL**: R17_sva never checked, and BMC stopped at depth 23 of 40 at the counterexample. It validates and re-serializes to identical JSON (R3).
  - `observation_execution_key` is pinned by an independent byte-level `hashlib` vector over all 16 request fields. Twelve tests show each request input changes the key, a further test shows `formal_mode` does too, and ten show that result and handle fields do not.
  - Rejection reasons spot-checked: incomplete sim/formal PASS, TIMEOUT or TOOL_ERROR with failure evidence, INCONCLUSIVE on sim, action mismatch, seed on formal, `None` bundle, and infrastructure-only structural FAIL each fail on their own rule.
  - Planted bugs, each caught and the source restored byte-identical:
    - TIMEOUT with a failing test allowed → 3 failures;
    - sim PASS with executed ⊂ expected → 1;
    - formal PASS with checked ⊂ expected → 1;
    - `candidate_manifest_hash` dropped from the key → 12;
    - `adapter_hash` dropped from the key → 12;
    - `evaluator_bundle_hash` nullable → 1.
- Implementation interpretations where the packet left detail open, for coordinator review:
  1. **Formal FAIL** requires both a failing property *and* a counterexample ref; equivalence FAIL requires `proved=false` and a counterexample. Both are part of "sufficient candidate-attributed failure evidence" (R3).
  2. **Results outside the expected inventory, or duplicated results, are rejected for every status**, not only PASS: a result for an undeclared test means the inventory itself is wrong.
  3. **Non-verdict statuses** (TIMEOUT, TOOL_ERROR, UNSUPPORTED, INCONCLUSIVE) reject any candidate failure evidence, including candidate-category error diagnostics.
  4. **Structural PASS** means zero errors. Latch/blackbox counts are recorded for synthesis but not judged, because "unexpected" latches need policy semantics this record does not have.
  5. The **formal report must echo** the requested mode and depth.
  6. **`diagnostics_truncated=true`** requires exactly 200 entries; `started_at` must be zero-padded `YYYY-MM-DDTHH:MM:SSZ` (`strptime` alone accepts `2026-1-4`).
  7. The test suite imports `TestId` under an alias (`SimTestId`), because pytest otherwise tries to collect a domain type named `Test*` as a test class. No product code was changed for this.
- Known limitations: completeness is relative to the adapter-reported inventory until the P1.4/P1.6 evaluator-bundle manifest anchors it (R5 follow-up). Cross-record invariants are SIN-P1.1-009.
- Handoff/next action: `docs/handoffs/SIN-P1.1-005.md`.
