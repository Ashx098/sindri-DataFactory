# SIN-P1.1-010 — P1.1-G: P1.1 Foundation Integration Gate

## Phase identity
- Phase: `P1`
- Subphase: `P1.1` (subphase integration gate; not a feature task)
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
An evidence packet, `docs/implementation/gates/P1.1-G.md`, proves that SIN-P1.1-001…009 form **one
coherent foundation on authoritative `main`**, and lists every correction that must land before
persistence (P1.2) or real tool integration. The coordinator then decides
`APPROVED | BLOCKED`. Agents never set the gate.

This gate audits and closes P1.1. It builds no adapters, store, controller or judge.

## Why / architecture references
- P1.1 breakdown (`CURRENT_PHASE.md`), SIN-P1.1-G:
  - all P1.1 tasks verified on `main`;
  - exported JSON Schemas match the models;
  - the float/identity rule (SIN-P1.1-001 follow-up) is applied consistently across records.
- SIN-P1.1-001 stays `verified`, not `closed`, until that follow-up is carried forward (002 D5, P1.1-G).
- SIN-P1.1-008 S13: 008 proved only that `model_json_schema()` generates; exported, checked-in equivalence was left to this gate.
- SIN-P1.1-009: the closed-bundle validator, rule-removal harness and CT-1…CT-4.
- AGENTS.md §3, §5A and §9; `docs/implementation/PHASE_GATES.md`; gate template `docs/implementation/gates/TEMPLATE.md`.
- Coordinator architecture review (assignment of this packet):
  - G-A: no acceptance-critical Python `assert`;
  - G-B: ID allocation before persistence and concurrency;
  - post-gate vertical-slice strategy.

## Owner / coordinator
- Owner: assigned by coordinator when the gate is authorized
- Integrator / gate decision: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged and gate execution is authorized (drafted against `efe9ccb`)
- Worktree: `../worktrees/SIN-P1.1-010`

## Dependencies
- SIN-P1.1-001…009 `verified` on `main`, confirmed at `efe9ccb` (task board).

## Facts established by read-only probes on `main` `efe9ccb` (before drafting)
| # | Observation | Consequence |
|---|---|---|
| G1 | Task board: SIN-P1.1-001…009 all `verified`; nothing `ready`. | Precondition met; gate check A1 re-confirms it at execution time. |
| G2 | `ruff`, `mypy --strict` (19 files) and `pytest` pass (1808 passed, 8 skipped); the contract suite is 1692. | Baseline for A2. |
| G3 | **One runtime `assert` in `src/`:** `FormalReport.bound_met` (`observation.py:189`) asserts BMC depths are present before comparing them. | G-A. For *validated* records it only narrows types, because `_consistent` already rejects BMC without depths. If validation is bypassed, under `python -O` the comparison becomes `None >= None` → `TypeError`. It is not a silent PASS, but acceptance semantics must not depend on `assert`. |
| G4 | `python -O -m pytest` passes, but pytest warns that **asserts outside test modules are ignored**. `tests/contract/cross_record/_case.py` (`assert_isolated`) and `tests/contract/_record_catalog.py` (import-time catalog checks) use plain `assert`. | Under `-O` the 009 negative cases would pass **vacuously**. Any `-O` evidence is meaningless until helper asserts are rewritten or made explicit (G-A2). |
| G5 | `model_json_schema()` generates for all 48 exported models in validation and serialization modes, and the two are identical. There is no float/`number` type anywhere, and `additionalProperties: false` is set. | Export is feasible (A4). |
| G6 | The generated schemas are **structurally looser than the models**: typed IDs and `ContentId` are plain `string` with no pattern; `schema_version` is plain `integer` with no `const: 1`; non-blank text, the UTC timestamp format, and every model-level invariant are absent. In JSON Schema `1.0` is a valid `integer`. | A JSON Schema validator would accept records that the models reject. The authority question must be decided (decision G-JS). |
| G7 | `schemas.__all__` exports 77 names (48 models, 9 `Record`s). Public names defined but not exported: `episode.S` (a private alias) and `cross_record.run_rules` (the harness API). | The inventory check is feasible (A3). One decision: is `run_rules` public? |
| G8 | Floats: `StrictModel` rejects binary floats recursively at every depth, for records **and** nested parts (D5). `core.ids.canonical_json_bytes` is generic and still accepts finite floats, while rejecting NaN/Inf, tuples and non-str keys. No record can produce a float, so record identity is float-free. | The follow-up holds at the record boundary. Whether the core encoder should also reject floats is decision G-F. |
| G9 | `docs/REPO_MAP.md` lists the record set without `FindingTransition`. `CURRENT_PHASE.md` still says 001 is "kept at verified until the follow-up is carried forward". Otherwise there are no stale READY/planned claims for 001–009; every packet status line reads `verified`. | Doc corrections B3. |
| G10 | Domain IDs are **sequential-style examples, per §20**: `e17`, `F42`, `R17`, `ob_88121`, `job_771`. `core/ids.py` says "earlier types and patterns are frozen". `EpisodeId = e[0-9]+` and `FindingId = F[0-9]+` are digits-only. `ObservationId = ob_[0-9a-z]+`, `CandidateId = c_<slug>`, `JobId = job_<slug>` and `TaskId` (slug) would admit lowercase ULID/UUIDv7-hex suffixes. No document states each ID's uniqueness scope or allocator. | G-B decision before P1.2. |
| G11 | `scripts/docx_to_md.py:181` uses `assert` on a parsing step. | Tooling only, not acceptance-critical; listed in the G-A audit and not a blocker. |

## A — Gate checks executable immediately over current P1.1
Each check records its command, result and CI run in the gate evidence packet.

| # | Check | Pass criterion |
|---|---|---|
| A1 | Authoritative state | `implementation/task_board.yaml`: 001…009 are `verified`; `implementation/current.yaml`: P1 is `ACTIVE`; gate base = `main` HEAD with merged-main CI green. |
| A2 | Repository quality gate | `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest -q` and `uv run pytest -q tests/contract` all pass on the gate base, and the CI script steps run. |
| A3 | Public API inventory | A test enumerates every public class and function defined in `sindri.schemas.*` and asserts it is exported in `schemas/__init__.__all__` or appears on an explicit private allow-list (`S`, plus `run_rules` if G7 decides internal). `__all__` has no stale or dangling names, and the 9 top-level `Record`s are exactly the P1.1 record set. |
| A4 | JSON Schema export consistency | A deterministic exporter writes one schema per top-level record (9 files, nested definitions in `$defs`), checked in. A test regenerates and asserts byte equality (drift guard) for every record and every nested public boundary model reachable from them. The documented fidelity gaps (G6) are listed in the evidence and asserted, per G-JS. |
| A5 | Float / identity / strict scalars | Re-run 008 S1–S17 (round trip, `content_id == canonical_json_id(model_dump(mode="json"))`, key-order independence, sequence-order identity, float/NaN/Inf rejection at every leaf with its path, strict int/bool at the exact field, ExactScalar distinctness). Add one sweep asserting every hash constructor input (`content_id`, `candidate_source_hash`, `observation_execution_key`) is float-free for every catalog entry. |
| A6 | Serialization + cross-record together | `pytest tests/contract` (008 and 009 suites) passes in one run on the gate base. |
| A7 | Coherent 009 bundle | `check_records(records(positive_spec())) == ()`, and every variant positive stays clean. |
| A8 | Rule-removal harness | For all 54 runtime `InvariantCode`s, removing exactly that rule silences at least one isolated negative case, and the positive bundle stays clean. `RULES` equals `InvariantCode`. |
| A9 | Contract tests | CT-1 (37 `ContentId` fields classified), CT-2 (one set head), CT-3 (no-cascade ownership, including the PR #28 cases) and CT-4 (T1 implied by B1 + B2) are green. |
| A10 | Docs / source-of-truth | No stale READY/planned/drafting claim for completed P1.1 work in `PROJECT_STATE.md`, `CURRENT_PHASE.md`, `REPO_MAP.md`, `components/*.yaml`, task packets or handoffs. `components/schemas.yaml` lists every public interface from A3. |
| A11 | Hidden-evaluator boundary | The import-boundary tests (`tests/architecture`) pass. No `src/` module imports judge, solver, triage or forge packages, or reads `hidden_final_eval` paths. The `Visibility.HIDDEN` protections (O14 / XR-F9, EvaluationPolicy judge-side, INV-EP-001) are unchanged since `efe9ccb` (diff review). No hidden fixture content exists outside test data. |
| A12 | `-O` safety (after B1/B2) | `uv run python -O -m pytest -q` passes, **with** helper asserts effective. A planted always-false helper assertion must fail under `-O`, proving the run is not vacuous. |

## B — Corrections that must block gate completion (proposed; coordinator decides each)
| # | Correction | Proposed handling | Why blocking |
|---|---|---|---|
| B1 (G-A) | **Acceptance-critical `assert` in `src/`.** Replace the `assert` in `FormalReport.bound_met` with an explicit, fail-closed branch: `if self.reached_depth is None or self.requested_depth is None: raise ValueError("bmc report without depths")`. Add a test that runs under `python -O` (subprocess) against a validation-bypassed (`model_construct`) BMC report and asserts the explicit error, never `True` and never a `TypeError`. Add a guard test: an AST scan of `src/` finds **no** `assert` statements. | **Recommended: fix inside P1.1-G** as a bounded gate correction: one function, no schema or identity change, no stored data. The alternative is making it a P1.2 blocker, but leaving it open would let acceptance semantics depend on interpreter flags. | Acceptance-critical behaviour must not disappear under `-O` (coordinator G-A). |
| B2 (G-A2) | **Test-helper asserts are skipped under `-O`.** Either register the helpers for pytest assertion rewriting (`pytest.register_assert_rewrite("tests.contract._record_catalog", "tests.contract.cross_record._case")` in a new `tests/conftest.py`), or replace helper `assert`s with explicit `raise AssertionError`. | **Recommended: explicit raises** in the two helpers. Registration is easy to forget for future helpers, so the AST guard from B1 is extended to `tests/**/_*.py`. | Without this, A12 and any `-O` evidence are vacuous. |
| B3 | **Stale docs:** `REPO_MAP.md` record list lacks `FindingTransition`; the `CURRENT_PHASE.md` 001 note must say the follow-up was verified by P1.1-G. `components/schemas.yaml` must name the JSON Schema export and its fidelity status. | Doc edits in the gate PR. | Source-of-truth accuracy (A10). |
| B4 | **JSON Schema export does not exist yet** (A4). | Exporter script, checked-in schemas and drift test, per G-JS. | P1.1 breakdown: "exported JSON Schemas match models". |
| B5 | Any A-check that fails at execution. | Fixed in the gate PR if it is a bounded correction (same rules as B1); otherwise the gate is `BLOCKED` with an owner. | Gate integrity. |

The gate PR may touch product code **only** for B1, plus any bounded B5 fix the coordinator accepts. No schema field, ID pattern, identity encoding or record semantics change in P1.1-G.

## C — Decisions to resolve before P1.2 persistence (surfaced; not changed by the gate)
| # | Decision | Options | Agent recommendation |
|---|---|---|---|
| **G-B** | **ID allocation under persistence and multi-worker concurrency.** See the audit table below. Minted IDs (`CandidateId`, `ObservationId`, `EpisodeId`, `FindingId`, `JobId`, and registry-minted `TaskId`) use sequential-style §20 examples, with no stated uniqueness scope or allocator. Concurrent gateway workers, triage agents and controllers will mint them. | **(1) Central allocator:** a store sequence per ID kind and scope. Keeps the patterns, needs a store round trip per ID, and creates a single point of contention. **(2) Collision-resistant IDs:** `<prefix>_<ULID or UUIDv7>` in lowercase base32/hex, time-ordered and allocated without coordination. `e[0-9]+` and `F[0-9]+` cannot hold them, so those two patterns need an ADR. **(3) Hybrid:** authored IDs (requirements, policy-local check/config/obligation/exception, family/lineage/variant/contract, test/property) stay human-readable; minted IDs use (2). | **(3) Hybrid, decided by ADR before P1.2.** No P1.1 record is persisted yet, so changing `EpisodeId`/`FindingId` patterns now costs fixtures only, while after P1.2 it costs a migration. Also record each ID's **uniqueness scope** (global vs per task vs per policy). "Types and patterns are frozen" in `core/ids.py` should be read as *no silent change*, not as a ban on an ADR-driven change before persistence. Its wording is clarified when that ADR lands. **Not changed in this planning PR or by the gate.** |
| G-JS | Role of JSON Schema (G6). | (a) Exported schemas are a **structural interop projection**; the Pydantic models are the only authority. The known gaps are documented and asserted, and the drift guard keeps them in sync. (b) Enrich the schemas: ID `pattern`s, `const: 1`, text `minLength`/`pattern` via `__get_pydantic_json_schema__` on typed IDs. Cross-field invariants still cannot be expressed. | **(a) for P1.1-G.** Whether P1.2 ingest uses JSON Schema as a *pre-filter* (which needs (b)) is decided with P1.2's strict loader (008 S15). Option (b) changes the generated schema only, not records or identity. |
| G-F | Should `core.ids.canonical_json_bytes` reject finite floats too (G8)? | (a) Keep it generic: records are float-free by construction, and A5 proves every hash input is float-free. (b) Reject floats in the encoder. That is an identity-encoding change and needs an ADR. | **(a).** Revisit only if a non-record identity ever needs JSON hashing. |
| G-R | Is `cross_record.run_rules` public API? | Internal (harness only; rename `_run_rules`, or list it on the allow-list) vs public (export it). | Internal: P1.2/P1.5/P1.7 consume `check_records` only. |
| G-S | Strict ingest and integer range (008 S15/S16) | Already decided as **hard P1.2 requirements**. | Carried forward unchanged, as a P1.2 entry criterion. |
| G-U | Store authority for 009 D1/D2: global uniqueness, chain completeness, global head. | Owned by P1.2 per 009 table D. | P1.2's packet must state how `check_records` is fed a *closed* bundle (X4). |
| G-O | `-O` policy | Add a CI job running `python -O -m pytest` (after B1/B2), or forbid `assert` in `src/` by test only. | Both: the AST guard (B1) is cheap, and one `-O` CI job proves it. Whether that job is added is the coordinator's CI decision. |

### G-B audit: domain ID allocation (current patterns, no change proposed here)
| ID | Pattern | Minted or authored by (expected) | Scope (to be decided) | Fits a ULID/UUIDv7 suffix? | Concurrency risk |
|---|---|---|---|---|---|
| `TaskId` | slug | Task Forge registry | global | yes | medium (bulk generation) |
| `CandidateId` | `c_<slug>` | controller/solver per edit | global | yes | **high** |
| `ObservationId` | `ob_[0-9a-z]+` | tool gateway per run | global | yes | **highest** (parallel jobs) |
| `EpisodeId` | `e[0-9]+` | controller | per task (ED15) | **no** (digits only) | **high** |
| `FindingId` | `F[0-9]+` | triage/critic agents | undocumented (009 B1 treats it as global within a bundle) | **no** (digits only) | **high** |
| `JobId` | `job_<slug>` | controller | per episode | yes | medium |
| `PolicyId` | `ep_<slug>` | authored | global | n/a | low |
| `RequirementId` | `R[0-9]+` | authored per task (Spec Forge, reviewed) | per task | n/a | low (single author/reviewer) |
| Family/Lineage/Variant/Contract | slugs | authored / registry | global | n/a | low |
| Obligation/Check/Configuration/ToolProfile/Exception | prefixed slugs | authored inside one policy | per policy | n/a | none |
| `TestId`/`PropertyId` | identifiers | evaluator bundle | per bundle | n/a | none |
| `ContentId` | `sha256:<hex>` | content-derived | global | n/a | none (no allocation) |

## D — Later real-tool risks the vertical slice will test (not P1.1-G work)
| # | Risk | Where it is exercised | Existing record |
|---|---|---|---|
| D1 | Expected test/property inventories are adapter-reported until the evaluator-bundle manifest anchors them (005 R5) | first real sim/formal run | 005 follow-up, 009 D4 |
| D2 | Expected-latch semantics need evaluator/profile meaning (005, PR #15) | first real synthesis run | 005 follow-up |
| D3 | `tool_profile_hash`, `tool_image_digest`, `adapter_hash` resolve to real profiles, images and adapters | first adapter | 009 D5 |
| D4 | TIMEOUT vs FAIL normalization, wall-time limits and clock injection (`started_at`, `duration_ms`) under real processes | first sandboxed run | ADR-0002, 005 |
| D5 | Golden-log normalizers mapping real stdout/exit codes to semantic status (never exit code alone) | first adapter | AGENTS §3, SECURITY attacks |
| D6 | Seeds and determinism of real simulators; replay equality | rerun/replay step | 005 R1, P1.G |
| D7 | `execution_key` reuse rules once a store exists (no cross-candidate reuse) | rerun step | 005 O2, P1.2 |
| D8 | ID allocation by concurrent workers (G-B) | first parallel jobs | G-B |
| D9 | Contract and evaluator-bundle records (009 D4/D6) | FIFO authority package | P1.6 |
| D10 | `check_records` fed from real persisted evidence (closed-bundle assembly) | judge/replay step | 009 X4, G-U |

## Post-gate execution strategy (direction for the next planning; nothing here is built in P1.1-G)
After the gate, development deliberately switches from **horizontal, schema-first** work to the
**smallest real vertical hardware slice**. The next implementation planning should get one real
FIFO through real tool execution before broadening any abstraction. Target shape:

```text
one FIFO (P1.6 authority package, minimal)
 → one real candidate (CandidateManifest)
 → real parser/compiler (P1.3 sandbox + P1.4 one adapter)
 → real simulation
 → normalized Observation (golden-log-tested normalizer)
 → failing mutant (one reviewed critical mutant)
 → Finding (FindingTransition chain)
 → repair (new candidate identity)
 → rerun (fresh Observation bound to the new candidate)
 → judge/replay (deterministic decision, check_records over the evidence bundle)
```

Planning principles for that slice:
- **Subsystems:** each one (P1.2 store, P1.3 sandbox, P1.4 gateway, P1.5 controller, P1.6 FIFO package, P1.7 judge) gets only the surface the slice needs: one tool, one configuration, one mutant.
- **Design decisions:** G-B, G-JS and G-S are resolved before the store persists the first record.
- **Breadth:** no new abstraction without a consumer in the slice (anti-skeleton). Breadth (more tools, configurations, families) comes after the slice runs end to end and replays.
- **Risk register:** table D is the slice's risk register; each row becomes a test in the task that first touches it.
- **Ordering:** the slice respects the existing order (P1.2 and P1.3/P1.4 after P1.1; P1.5 on fakes until P1.8). The coordinator still opens every packet.

## Scope (gate execution, once authorized)
- In scope:
  - checks A1–A12 with recorded evidence;
  - corrections B1–B5 as decided;
  - the JSON Schema exporter, checked-in schemas and drift guard;
  - the API inventory test;
  - the AST `assert` guard;
  - doc corrections;
  - the gate evidence packet.
- Allowed paths (proposed):
  - `src/sindri/schemas/observation.py` (`bound_met` only, B1);
  - `scripts/export_json_schemas.py` (new);
  - `schemas/json/v1/*.schema.json` (new, generated);
  - `tests/unit/test_no_runtime_asserts.py` (new);
  - `tests/contract/test_public_api.py` (new);
  - `tests/contract/test_json_schema_export.py` (new);
  - `tests/contract/_record_catalog.py` and `tests/contract/cross_record/_case.py` (B2 explicit raises only);
  - `docs/REPO_MAP.md`, `docs/implementation/CURRENT_PHASE.md`, `components/schemas.yaml`;
  - `docs/implementation/gates/P1.1-G.md` (new evidence packet);
  - this packet, `docs/handoffs/SIN-P1.1-010.md`, and the task-board status.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none touched.
- No change to: record fields or semantics, ID types or patterns (G-B is decided separately), `core/ids.py`, the canonical identity encoding, the §20 examples, or `cross_record.py` rules.
- No store, sandbox, adapter, controller, judge or FIFO package code.
- The agent never sets the gate to `APPROVED`, never edits `implementation/current.yaml` phase state, and never moves tasks to `closed`.

## Non-goals
- Executing the gate in this planning PR; starting P1.2 or any later subphase; marking anything READY.
- Changing ID patterns (G-B), JSON Schema enrichment (G-JS (b)) or the encoder float policy (G-F).
- Tool adapters, sandbox, store, controller, judge, FIFO assets: these belong to the post-gate vertical slice.

## Interfaces touched (gate execution)
- `FormalReport.bound_met`: same results for validated records; explicit error instead of `assert` for an impossible state (B1).
- New generated artifacts: `schemas/json/v1/*.schema.json`. No record, identity or API change otherwise.

## Acceptance criteria (gate execution)
- [ ] A1–A11 pass with recorded commands, results and CI runs; A12 passes after B1/B2.
- [ ] B1: no `assert` in `src/` (AST guard). The `-O` bypass test shows an explicit fail-closed error.
- [ ] B2: helper asserts are effective under `-O` (a planted always-false helper assertion fails).
- [ ] B3: no stale P1.1 status/doc claims; `components/schemas.yaml` lists the export and its fidelity status.
- [ ] B4: 9 record schemas exported; the drift guard passes; G6 gaps documented per G-JS.
- [ ] Decisions G-B, G-JS, G-F, G-R and G-O are recorded by the coordinator, or explicitly deferred to P1.2 entry with an owner.
- [ ] The evidence packet is prepared at `docs/implementation/gates/P1.1-G.md` with status `GATE_REVIEW`, decision `PENDING_HUMAN_APPROVAL`.
- [ ] The handoff is written; the report ends with "Awaiting coordinator assignment."

## Verification commands (gate execution)
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
uv run pytest -q tests/contract/cross_record
uv run python -O -m pytest -q
uv run python scripts/export_json_schemas.py --check
python3 scripts/show_ready_tasks.py --all
git diff --stat <gate-base> -- src/sindri/core src/sindri/schemas/cross_record.py tests/contract/examples   # must be empty
```

## Plan of record (gate execution)
1. Confirm A1 on the authorized gate base; record the CI run.
2. Land B1 and B2 (with guard tests), then B3 docs.
3. Add the API inventory test (A3), the exporter, checked-in schemas and drift guard (A4/B4), and the float-free hash-input sweep (A5).
4. Run A2 and A5–A12; record every result in `docs/implementation/gates/P1.1-G.md` using the gate template.
5. List open decisions (C) with owners; submit for coordinator decision.

## Status
`planned`; planning only, and the gate is not executed.

**Task ID.** The gate is registered on `implementation/task_board.yaml` as **`SIN-P1.1-010`** (title "P1.1-G — P1.1 foundation integration gate"). `tests/unit/test_governance.py` requires board IDs of the form `SIN-<phase>.<n>-<nnn>`, and requires every `docs/tasks/SIN-*.md` packet to be on the board, so `SIN-P1.1-G` cannot be a board ID. The gate's *decision* is still recorded like B0.G: a gate evidence packet (`docs/implementation/gates/P1.1-G.md`), with the coordinator updating phase state. This naming is for coordinator confirmation.

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
