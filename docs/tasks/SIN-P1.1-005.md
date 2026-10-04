# SIN-P1.1-005 — Observation

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`Observation` exists as a strict, immutable record of **authenticated evidence from one exact
execution of one declared check**: which exact candidate, under which exact policy version, check
and configuration, by which exact executor (action, profile, image, adapter), over which exact
inputs. It carries the raw `ToolStatus`, typed proof that the declared check actually ran, short
typed diagnostics, and content-addressed references to raw evidence. It is the record that
Findings cite, the judge consumes, ReleaseManifests cite and DatasetRecords inherit, so nothing
above the tool layer trusts anything that is not traceable to one of these.

## Why / architecture references
- Master architecture:
  - §4 principles 1 and 9 (only deterministic tools produce observations; results bind to exact artifacts);
  - §8 F1 (Observation: normalised status, summary, parsed details, raw logs, hashes of everything used; "the adapter checks that expected test IDs appear in the results");
  - §8.7 ("authenticated tool output tied to immutable inputs; status, scope, diagnostics and raw evidence", and the repository invariant that pass/fail claims must reference Observation IDs);
  - §8.8–8.9 (complete cache keys; "a PASS from a previous candidate, tool image, parameter set or evaluator version is not reusable unless the complete key matches");
  - §11.7 (random runs record seed, configuration, tool image); §11.10 (formal observations record solver, mode, depth, assumptions, configuration);
  - §13 X3 (observations short and structured);
  - §14 J2 (status taxonomy and training use); §20.4 example (starting point only).
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md`: {003, 004} → **005** → {006, 007}.
- ADRs/RFCs: **ADR-0002** (raw status is never rewritten; TIMEOUT stays TIMEOUT), ADR-0004.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash; DV/formal reviewer for execution-proof rules once assigned (role unassigned)

## Base
- Base branch: `main`
- Base commit: `main` when the packet is merged **and** marked ready (implementation waits for both; see the process deviation recorded for 003/004)
- Worktree: `../worktrees/SIN-P1.1-005`

## Dependencies
- Required completed tasks: SIN-P1.1-003 and SIN-P1.1-004 (both verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.policy` (`CheckKind`, `Visibility`, `FormalMode`; import only), `sindri.schemas.task.EditPath` (import only), `sindri.core.ids`, `sindri.core.status.ToolStatus`

## Open decisions (coordinator to decide; the agent recommends)

### O1 — Scope: is every Tool Gateway operation an Observation?
**Recommendation: no.** `Observation` is reserved for executions of a **declared EvaluationPolicy check** against a candidate. Diagnostic operations produce a different, separately typed record, so a diagnostic success **cannot be spelled as a correctness PASS at all**.
- The master's typed tools split into two families:
  - **check executions**: `lint`, `compile`, `run_sim`, `run_formal` (bmc/prove), `check_equiv`, `synth`. These run the candidate and can map to a `CheckKind`.
  - **diagnostic queries**: `inspect_waveform(run_id, …)` and `coverage(run_id)`. These take a previous run as input; they query an execution's artifacts rather than execute the candidate.
- Two further cases fall outside correctness evidence:
  - `run_formal` in `cover` mode is a reachability/qualification run, which E4 excludes from obligations;
  - a solver's ad-hoc `lint`/`compile`/`run_sim` that matches no declared check is also not policy evidence.
- The master uses "observation" informally for any tool output (§13: the solver sees "its own tool observations"). The schema narrows the *record type* name; it does not forbid giving the solver diagnostic results.
- **Proposed shape:** a separate `DiagnosticResult` record (no `ToolStatus`; its own outcome type), defined by the first task with a real consumer (P1.4 `inspect_waveform`/`coverage`, or P1.8's repair loop), following the no-abstraction-without-consumer rule. Judge, qualification and dataset APIs accept `Observation` only, so the type system enforces the boundary.
- Findings (006) may cite diagnostic results as *supporting* evidence for a hypothesis, but confirming or refuting a correctness claim needs an `Observation`. This is for decision in 006.
- Solver development runs of **development-visibility** policy checks *are* Observations (`visibility: development`), as the trajectory format requires.
- Alternatives:
  - (b) a single Observation type with a `scope: check | diagnostic` discriminator, where diagnostics forbid PASS/FAIL. Weaker: every consumer must remember to filter on scope.
  - (c) every gateway call is an Observation. **Rejected**: a waveform query could carry PASS, and cover runs contradict E4.

### O2 — Exact candidate binding
**Recommendation:**
- `candidate_id` (lookup) and `candidate_manifest_hash` (the CandidateManifest's `content_id()`, the authoritative binding that commits to files, ancestry and provenance).
- Also `source_hash` and `dependency_hash` copied from the manifest, because they are the **execution-relevant** subset used in the execution key (O6).
- Consistency with the manifest is a 009 cross-record check. `candidate_id` alone is never sufficient.

### O3 — Exact policy binding
**Recommendation:** `policy_id`, plus `policy_hash` (the EvaluationPolicy's `content_id()`, which pins the exact version), plus `check_id` and `configuration_id`. IDs alone could recur in a later policy version. Policy/check/configuration consistency is checked in 009.

### O4 — Check/configuration semantics
**Recommendation:** under O1, `check_id` and `configuration_id` are **always required**, with no nullable diagnostic variant. An Observation never declares its own checks; the check must exist in the bound policy and target the configuration (009).
- **One Observation per (check, configuration) execution.** A check over four configurations yields four Observations.
- A `random_sim` execution over several seeds is one Observation with a `seeds` tuple (O6).
- The record carries `check_kind` (and `visibility`) copied from the policy check so in-record rules (O7, O11) can be enforced, with equality to the policy checked in 009.

### O5 — Executor identity
**Recommendation:**
- `action` (enum of the check-execution tools: `lint`, `compile`, `run_sim`, `run_formal`, `check_equiv`, `synth`, `integrity_scan`), with an in-record compatibility rule against `check_kind`.
- `tool_profile_id` plus `tool_profile_hash` (the exact profile content; the profile record arrives in P1.4).
- `tool_image_digest` (OCI `sha256:` digest).
- `adapter_version`. The status is produced by the gateway's parser/normaliser, so the same tool output under a fixed adapter could normalise differently. The adapter is part of the executor.

### O6 — Complete input identity and execution key
**Recommendation:** a required `execution_key: ContentId`, recomputed in-record from a domain-separated construction (like `candidate_file_set_v1`):
```
canonical_json_id({"kind": "observation_execution_key_v1",
  "source_hash", "dependency_hash", "policy_hash", "check_id", "configuration_id",
  "action", "tool_profile_hash", "tool_image_digest", "adapter_version",
  "evaluator_bundle_hash", "seeds", "formal_mode", "formal_depth"})
```
- **New input `evaluator_bundle_hash: ContentId | None`:** the exact test/property/reference-model/golden artifacts used. The policy does not hash these, yet §8.9 forbids reuse across "evaluator versions". It is `None` only for kinds that use no evaluator artifacts (`lint`, `parse_elaborate`, `synthesis`, `integrity_scan`); it is required for `directed_sim`, `random_sim`, `formal` and `equivalence` (equivalence's bundle includes the golden).
- **Seeds:** `seeds: tuple[StrictInt, …]`, non-empty for `random_sim` and empty otherwise.
- **Assumptions** are covered via `policy_hash`, because assumptions live in the policy.
- **Not included:** `candidate_manifest_hash` (it includes model provenance, which does not affect execution). That allows a future cache to reuse results across content-identical candidates. *Whether* and *how* a cache hit is recorded (new Observation or reference) is P1.2/F5's decision, not this record's.

### O7 — Execution proof (what shows the declared check actually ran)
**Recommendation:** a typed `execution_report`, discriminated by kind. Each variant is structured, cross-checkable evidence parsed from tool output, not a bare `executed: true`:
- **`SimulationReport`** (directed/random sim):
  - `expected_test_ids`, declared from the evaluator bundle before the run;
  - `test_results`, a tuple of `{test_id, outcome: ToolStatus}` parsed from the tool.
  - PASS requires every expected test to appear exactly once with outcome PASS. A test that never ran makes PASS impossible.
- **`FormalReport`:**
  - `mode` (bmc/prove), `requested_depth` (bmc), `reached_depth` (bmc), `proof_closed` (prove);
  - `properties_checked` (property names) and `assumption_count`.
  - BMC PASS requires `reached_depth ≥ requested_depth`. Prove PASS requires `proof_closed`. Anything short of that is INCONCLUSIVE, never PASS.
- **`EquivalenceReport`:** `relation` (the declared equivalence relation ID), `bounded_depth | None`, `proved`.
- **`StructuralReport`** (lint/parse/synth/integrity): `error_count`, `warning_count`, plus kind-specific counts (synth: `latch_count`, `blackbox_count`).
- Requested values (mode, depth) must equal the bound policy's (009). Parser correctness is proven by P1.4 golden-log tests; this record makes a false "ran" claim *structurally inconsistent* rather than merely asserted.

### O8 — Raw evidence and diagnostics
**Recommendation (no `dict[str, Any]`):**
- `summary`: non-blank, at most 500 characters ("short and structured").
- `diagnostics`: tuple of `Diagnostic{severity: error|warning|info, category: candidate|evaluator|infrastructure, code: str|None, message, path: EditPath|None, line: int ≥ 1|None}`, capped at 200 entries, with a required `diagnostics_truncated: bool`.
- `log_ref: ContentId`: the raw log blob, required.
- `evidence_refs`: tuple of `EvidenceRef{kind: counterexample_trace|waveform|coverage_db|tool_report, hash: ContentId}`.
- Larger or tool-specific detail always goes in a referenced blob, never inline.

### O9 — Timing and resources
**Recommendation:**
- `duration_ms: StrictInt ≥ 0` (D5: no floats; replaces §20.4's `duration_s: 41.2`).
- `started_at`: a UTC RFC 3339 string with second precision and a `Z` suffix, pattern-validated. It is an audit fact, not an input, and is excluded from `execution_key`.
- For TIMEOUT, `timeout_limit_ms` is required.
- No CPU, memory or cost fields in v1: those are observability (non-authoritative, §13 telemetry). Resource *limits* are already inside `tool_profile_hash`.

### O10 — Status authority
**Recommendation:** `status: ToolStatus`, with no second raw taxonomy. `INVALID_SUBMISSION` and `INVALID_TASK` stay judge-layer `CheckStatus` concepts (§14 J2): integrity-scan *findings* are FAILs of an `integrity_scan` check, and the judge decides `INVALID_SUBMISSION`. The raw status is never rewritten by any component (ADR-0002); TIMEOUT stays TIMEOUT.

### O11 — Status-conditional invariants (a kind × status matrix)
**Recommendation:**
- **PASS:**
  - the execution report is complete per O7;
  - no `error`-severity diagnostics;
  - no counterexample refs.
- **FAIL:** at least one candidate-attributed failure locus:
  - sim: ≥ 1 test with outcome FAIL;
  - formal/equivalence: a `counterexample_trace` evidence ref is required;
  - structural kinds: ≥ 1 `error` diagnostic with category `candidate`.
- **TOOL_ERROR:**
  - ≥ 1 diagnostic with category `infrastructure`;
  - **no** candidate-category error, failing test or counterexample. It identifies an infrastructure failure without labelling the RTL.
- **TIMEOUT:**
  - `timeout_limit_ms` set and `duration_ms ≥ timeout_limit_ms`;
  - no failure locus. Partial results are not a verdict, and a TIMEOUT is never re-expressed as FAIL.
- **INCONCLUSIVE:**
  - only for `formal` and `equivalence`;
  - the report shows the unmet bound (reached depth < requested, or proof not closed).
- **UNSUPPORTED:** ≥ 1 diagnostic with a `code` naming the unsupported capability.
- **Timeout context:** `timeout_limit_ms` must be `None` for any status other than TIMEOUT.

### O12 — Identity and versioning
**Recommendation:**
- **Immutable and non-versioned**: no `observation_version` and no `supersedes`. A rerun is a new Observation; corrections are new records (§8 F2).
- `observation_id` (assigned by the gateway, unique) is the reference handle.
- `content_id()` is the exact record identity. Citations in later records (Finding, judge verdicts, ReleaseManifest) carry both, and 009 checks they agree.

### O13 — Authentication (derived; not in the coordinator's list)
**Recommendation:**
- For v1, "authenticated" means **provenance plus write authority**, not cryptographic signatures.
- The record carries `producer: {component: "tool_gateway", adapter_version}`, and only the gateway may write Observations. Write authority is enforced by the evidence store and permissions (P1.2/P1.3), not by a field an adapter could fill in.
- Signing is deferred to the security work in P1.3/P4.9 if needed.

### O14 — Visibility (derived)
**Recommendation:**
- `visibility` is copied from the policy check; equality is checked in 009.
- Observations of `hidden` checks are judge-side protected.
- A solver may receive development-check Observations only; the projection is P1.5/P5.
- `summary` and `diagnostics` of hidden Observations must never reach solver context (§14 J4).

## Scope (written for the recommended options; finalized after decisions)
- In scope:
  - `src/sindri/core/ids.py`, additive only: `TestId` (e.g. `stall_stability_004`), `PropertyId` (e.g. `R03_sva`), and `EquivalenceRelationId` if O7's relation stays.
  - `src/sindri/schemas/observation.py`:
    - `Observation` (`Record`, non-versioned), with all fields from O2–O9, O13 and O14;
    - `Diagnostic`, `EvidenceRef`, `Producer`;
    - the four `execution_report` variants (O7);
    - `ObservationAction` (O5);
    - `observation_execution_key()`: the single implementation of O6.
  - In-record invariants:
    - `execution_key` recomputation;
    - action ↔ `check_kind` compatibility;
    - report variant ↔ `check_kind`;
    - the evaluator-bundle and seeds rules (O6);
    - the O11 status matrix;
    - diagnostics cap/truncation;
    - `started_at` format;
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.4 fixture: a FAIL BMC run with a counterexample, `duration_ms` and full bindings.
- Allowed paths: `src/sindri/schemas/observation.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-005.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none; fixtures use synthetic IDs and hashes only.
- Other forbidden paths:
  - all verified records (`_base`, `task`, `requirement`, `policy`, `candidate`): import only;
  - existing ID patterns;
  - `core/status.py`: no new statuses (O10).

## Non-goals
- No `DiagnosticResult` record (O1: introduced by its first consumer).
- No gateway, adapters, parsers, sandbox or golden-log tests (P1.3/P1.4). No cache semantics (P1.2/F5).
- No judge logic and no `CheckStatus`/`Verdict` mapping (P1.7). No solver projection (P1.5/P5). No signing (O13).
- No Finding, EpisodeState, ReleaseManifest or DatasetRecord.

## Cross-record invariants deferred to SIN-P1.1-009
- `candidate_manifest_hash` is the `content_id()` of the CandidateManifest with `candidate_id`; `source_hash` and `dependency_hash` equal that manifest's.
- `policy_hash` is the `content_id()` of the EvaluationPolicy with `policy_id`; the policy's `task_id` equals the candidate's `task_id`.
- `check_id` exists in that policy; `configuration_id` is targeted by that check; the pair is **not** excluded by a policy exception.
- `check_kind`, `visibility` and `tool_profile_id` equal the policy check's. Requested formal mode/depth equal the policy check's.
- `evaluator_bundle_hash` equals the bundle referenced by the task's EvaluatorCertificate (once that record exists). For equivalence, the bundle commits to the task's `golden_hash`.
- Citations carry an `observation_id` and `content_id()` that agree (O12).
- The P1.1-009 enforcement rule (PR #9) is evaluated over Observations of mandatory, non-quality, applicable checks.

## Interfaces touched
- Schemas: new `Observation` v1. IDs: additive per Scope.
- Tool APIs: none (this record is what P1.4 adapters will emit). DB/migrations: none. External dependencies: none new.

## Acceptance criteria
Positive:
- [ ] The adapted §20.4 example (FAIL, BMC, counterexample ref, `duration_ms`, full bindings) validates, round-trips and re-serializes to identical JSON.
- [ ] One valid Observation per status that the matrix allows for representative kinds, including a sim PASS with every expected test passed, a TIMEOUT with a limit, a TOOL_ERROR with an infrastructure diagnostic, a formal INCONCLUSIVE with unmet depth, and an UNSUPPORTED with a capability code.
- [ ] `observation_execution_key` matches an independent byte-level `hashlib` vector (as in 004) and changes when any input in its construction changes; it does **not** change with `started_at`, `duration_ms`, `observation_id` or `candidate_manifest_hash`.

Negative (each a separate test):
- [ ] Every field required (no defaults); unknown fields rejected at every level (including `executed`, `duration_s`, `tool`).
- [ ] A stored `execution_key` that disagrees with its recomputation → rejected (wrong tag, missing field, unsorted, or one tampered input).
- [ ] A `ToolStatus` outside the enum, or `INVALID_SUBMISSION`/`INVALID_TASK` → rejected.
- [ ] Sim PASS with a missing, extra or duplicated expected test, or any non-PASS test → rejected.
- [ ] BMC PASS with `reached_depth < requested_depth`; prove PASS without `proof_closed` → rejected.
- [ ] FAIL without a failure locus (per kind) → rejected; formal/equivalence FAIL without a counterexample ref → rejected.
- [ ] TOOL_ERROR carrying a candidate error, failing test or counterexample → rejected; TOOL_ERROR without an infrastructure diagnostic → rejected.
- [ ] TIMEOUT without `timeout_limit_ms`, with `duration_ms < timeout_limit_ms`, or with a failure locus → rejected; `timeout_limit_ms` on a non-TIMEOUT → rejected.
- [ ] INCONCLUSIVE on a non-formal/non-equivalence kind, or with a fully met bound → rejected.
- [ ] Action incompatible with `check_kind`; report variant incompatible with `check_kind` → rejected.
- [ ] `evaluator_bundle_hash` missing for sim/formal/equivalence, or present for structural kinds; seeds present for non-random kinds or empty for `random_sim` → rejected.
- [ ] More than 200 diagnostics, `summary` over the limit or blank, malformed `started_at`, float `duration` → rejected.
- [ ] The record is immutable; there is no `supersedes` field.

Planted-bug checks (run, record in the handoff, revert):
- [ ] Allowing TIMEOUT with a failing test (i.e. "timeout means fail") makes the suite fail.
- [ ] Accepting sim PASS when executed tests ⊂ expected makes the suite fail.
- [ ] Dropping the domain tag from `observation_execution_key` makes the suite fail.
- [ ] Removing `evaluator_bundle_hash` from the key makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [ ] `components/schemas.yaml` gains Observation invariants (O1 reservation, O6 key, O11 matrix, O14 protection); `docs/REPO_MAP.md` updated.
- [ ] Handoff written; report ends with "Awaiting coordinator assignment."

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
`planned`. Draft for coordinator review; decisions O1–O14 open (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
