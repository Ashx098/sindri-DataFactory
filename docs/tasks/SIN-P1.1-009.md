# SIN-P1.1-009 — Cross-record invariant tests

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
Given an in-memory set of already-valid P1.1 records, one pure, deterministic check reports every
violation of the cross-record rules deferred by SIN-P1.1-002…008. The rules cover:
- hashes resolve to the exact records they name;
- revision chains keep their identity;
- the policy enforces every approved mandatory requirement in every configuration where it applies;
- Observations, Findings and FindingTransitions bind to the exact candidate, policy and check;
- EpisodeState chains are continuous, legal and monotonic.

Rules that need store or event-log authority, or record types that do not exist yet, are listed
with their owner rather than approximated.

## Why / architecture references
- Master architecture:
  - §4 principle 9: results bind to exact artifacts.
  - §8 F2: store by content hash; history is never edited.
  - §8.7: authority records; claims of pass/fail reference Observation IDs.
  - §14 J1: check order.
  - §20 record examples.
- P1.1 breakdown (`CURRENT_PHASE.md`), SIN-P1.1-009:
  - claims of pass/fail reference Observation IDs;
  - IDs resolve across records;
  - task/family/lineage/split identity cannot change across manifest versions, and (`task_id`, `requirement_id`) is stable across requirement versions (coordinator C5);
  - every approved mandatory requirement is enforced in every configuration where it applies, after exceptions (PR #9 review).
- Deferred-rule sources (every rule below cites one):
  - 002 Non-goals and C5;
  - 003 Non-goals, E1 and E6;
  - 004 Non-goals;
  - 005 "Cross-record invariants deferred to SIN-P1.1-009";
  - 006 "Cross-record invariants deferred…", FD4, FD9, the PR #17 corrections and PR #18 fix 3;
  - 007 "Cross-record invariants deferred…", ED2, ED3, ED12 and ED15;
  - 008 "Single-record (008) vs cross-record (009)".
- ADRs: ADR-0002 (statuses), ADR-0004 (requirement → obligation ownership), ADR-0005, ADR-0006 (episode lifecycle).
- Phase/subphase: P1.1; order: 008 → **009** → P1.1-G.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-009`

## Dependencies
- Required completed tasks: SIN-P1.1-001…008 (verified).
- Required schemas/contracts: all of `sindri.schemas` and `sindri.core.ids`; read-only use. No schema change is proposed.

## Facts established by read-only probes on `main` `c1025af` (before drafting)
| # | Observation | Consequence |
|---|---|---|
| Q1 | The adapted §20 example files are **not mutually consistent**. Of 17 cross-links probed, 9 fail: `policy.task_id ≠ task`; obligation requirements R01/R02 ∉ task R03/R17; candidate files fall outside the edit scope; `observation.candidate_manifest_hash`/`policy_hash`/`policy_id`, the Finding's candidate hash and citation, and `episode_state.policy_hash` do not match the example records. | 009 cannot reuse the examples as a bundle. It **builds a coherent bundle by construction**, computing every hash from the records it names. The example files stay unchanged; 002–008 tests depend on them byte for byte. |
| Q2 | `CandidateManifest` binds `task_id` only, with no task-manifest revision hash. | Edit-scope and read-only checks must choose a task revision (X8). |
| Q3 | References by **ID only** (`parent_candidate_id`, `derived_from`, `superseded_by`, `Finding.requirement_id`, `policy.task_id`, `candidate.task_id`) can form cycles and can dangle; references by **hash** cannot form cycles. | Closed-world resolution (X4) and an explicit acyclicity rule (XR-K5). |
| Q4 | Several `ContentId` fields name artifacts with **no P1.1 record type**: contract, golden, tool profile, image, adapter, evaluator bundle, solver config, job request, patch, blobs, checkpoint, failure signature. | Their resolution is owned later (table D). A locked inventory makes every hash field classified exactly once (XR-B3). |
| Q5 | `EvaluationPolicy` refers to a parameter vocabulary that no record defines. ("Configuration parameter names match the task's contract", 003, needs a Contract record.) | Surfaced as N1, with an in-bundle substitute (XR-P5). |

## Decisions requested from the coordinator
Recommendations are the agent's proposals. Nothing below is decided until the coordinator rules.

| ID | Question | Recommendation |
|---|---|---|
| X1 | Where do the invariants live? | **Product code**: `src/sindri/schemas/cross_record.py`, holding pure functions with no I/O, store or clock. These rules are part of the record contract; P1.2 ingest, the P1.5 controller and the P1.7 judge are named consumers and must not each re-implement them. Tests-only would leave the rules unexecutable outside CI. This is not a skeleton: every function is used by 009's tests and enforces a recorded rule. |
| X2 | Input and result types | `check_records(records: Iterable[Record]) -> tuple[Violation, ...]`. **No bundle record type**: the function groups its input by class. The one new type is a **result value**, `Violation{code: InvariantCode, subject: str, detail: str}`, with `subject` like `"Observation:obs_…"`. It is a frozen `StrictModel`, **not a `Record`**: no `schema_version`, no `content_id`, and not persisted in P1.1. `InvariantCode` is a `StrEnum` of the XR-* IDs below. Surfaced per the "no new record types" rule. |
| X3 | One error or aggregate? | **Aggregate**: return every violation, sorted by (`code`, `subject`, `detail`). No early exit, and **never raise** on an inconsistent bundle; a non-`Record` input raises `TypeError`. **No cascades:** an unresolved reference yields one XR-B2 violation, and checks that depend on that resolution are skipped for that record. The function is order-independent, and exact duplicate records collapse (idempotent input). |
| X4 | World model | **Closed world**: the input set is the universe. Every reference to a P1.1 record type must resolve inside it. A *head* is a record that no record in the set supersedes. Whether a set head is the *global* head, and whether a chain is complete, are store questions (D-rows). |
| X5 | Fields that stay constant across a TaskManifest revision chain | **Stable:** `task_id` (chain key), `family_id`, `lineage_id`, `variant_id`, `split` (C5), `contract_id`, `task_type`, `authority_mode`, `source`. **May change:** `approved_contract_hash` (a new contract version triggers requalification), `golden_hash`, `rights`, `allowed_edit_paths`, `requirement_ids`. |
| X6 | Applicability of a Requirement to a Configuration | `all_supported_configs` applies everywhere. `parameter_scope` applies iff, for **every** named parameter, the configuration assigns that name **and** the value is a member of `values` under **exact-type** equality (`true ≠ 1 ≠ "1"`, per 008 ExactScalar). A configuration that does not assign a scoped name is **unresolvable** (XR-P5), never silently "not applicable". |
| X7 | When is a candidate file "inside" `allowed_edit_paths`? | The path equals an allowed entry, or has it as a **segment prefix** (`entry + "/"`). `rtl/fifo` covers `rtl/fifo/a.sv` but not `rtl/fifo_old.sv`. No globbing. |
| X8 | Which task revision applies to candidate edit-scope and read-only checks? (Q2) | The **set head** revision, recorded as a known limitation. Exact pinning would need a `task_manifest_hash` field on `CandidateManifest`. That is a schema change, outside this tests-and-invariants task; surfaced, not proposed. |
| X9 | WAITING entry: what may `resume_state` be? | **`resume_state == previous.state`** (return to where it paused). The alternative is "previous state or a lifecycle successor of it", which would allow, for example, `DEV_CHECK → WAITING(resume=TRIAGE)`. The strict rule is simplest; relaxing it later is backward compatible. |
| X10 | Exemptions from the limit rule at ABORTED (007 deferred list) | **Per dimension:** `abort_reason = budget_exhausted` exempts only the additive `spent + reserved ≤ limits` rule; `wall_clock_exhausted` exempts only `wall_clock_elapsed_ms ≤ wall_clock_limit_ms`. No other reason exempts anything. |
| X11 | Policy/task currency and coverage scope | Coverage (XR-P6/P7) and currency (XR-P2b) are evaluated for each **head policy** against the **head task revision** and the **head requirement revisions**. A non-head policy is checked only for binding (XR-P1, XR-P2a, XR-P3 against its matched revision). Historical requalification is P1.5/P4. |
| X12 | An approved mandatory requirement that applies to **zero** configurations of a head policy | **Violation (XR-P7).** Otherwise coverage is vacuously satisfied, and the requirement is never enforced. |
| X13 | Hidden-check leakage via Findings (new candidate rule, security-relevant) | A Finding whose `producer.role` is `solver` must not cite (correctness or deciding) an Observation with `visibility = hidden`, under O14 (hidden Observations never reach solver context). Proposed as **XR-F9**. This rule was not in 002–008, so the coordinator decides whether to add it or defer it. |

## Invariant catalogue: enforceable over an in-memory bundle in 009
Conventions:
- **Positive fixture:** the coherent bundle built by `tests/contract/cross_record/_bundle.py` (scenario list below), which must produce zero violations.
- **Negative mutation:** applied to the builder's spec **before sealing**, so every dependent hash is recomputed and only the targeted rule fails. The test asserts the exact violation set, `{code}` (cardinality given in "Report").
- Hash-tampering mutations (XR-B2) are applied after sealing.
- **Planted bug:** a temporary source edit, restored byte-identically, plus the automated rule-removal harness (see Test design).
- **Report:** what one violation is counted against. Every rule aggregates (X3).

### B — Bundle structure and hash resolution
| ID | Input records | Pass condition (deterministic) | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-B1 | all | Each record key names one content. Keys: Task (`task_id`, `manifest_version`); Requirement (`task_id`, `requirement_id`, `requirement_version`); Policy (`policy_id`, `policy_version`); Candidate `candidate_id`; Observation `observation_id`; Finding `finding_id`; Transition (`finding_id`, `sequence`); EpisodeState (`task_id`, `episode_id`, `sequence`). Identical duplicates collapse. | Two Observations with the same id and different `summary` | Key compared by content_id instead of key | 1 per conflicting key |
| XR-B2 | all | Every reference in inventory **H1** resolves to exactly one record of the declared type with `content_id() == hash`. Where an ID travels with the hash (candidate, policy, observation, finding), the resolved record's ID equals it. | (a) `observation_hash` → unknown hash; (b) right hash, wrong `observation_id`; (c) `policy_hash` pointing at a Candidate's content_id (type confusion) | Resolve by ID, ignoring the hash | 1 per unresolved reference |
| XR-B3 | schemas (introspection) | Every `ContentId`-typed field (incl. `| None`, nested, tuple items) in every P1.1 schema is classified exactly once: H1 (resolved here), H2 (deferred, owner named) or H3 (self/computed). | Add an unclassified field to a test-local subclass | Drop one entry from the classification map | test-level (no runtime code) |

**H1 — resolved in 009:**
- `TaskManifest.supersedes`, `Requirement.supersedes` and `EvaluationPolicy.supersedes`;
- `Observation.candidate_manifest_hash` (+`candidate_id`) and `Observation.policy_hash` (+`policy_id`);
- `ObservationCitation.observation_hash` (+`observation_id`), in Finding correctness citations and transition deciding citations;
- `FindingTransition.finding_hash` (+`finding_id`) and `previous_transition_hash`;
- `ExistingPolicyCheck.policy_hash` and `DevelopmentProbeRequest.policy_hash`;
- `Finding.candidate_manifest_hash` (+`candidate_id`);
- `EpisodeState.previous_state_hash`, `policy_hash` (+`policy_id`) and `budget_hash`;
- `CandidateBinding.candidate_manifest_hash` (+`candidate_id`), in the active and best candidate and in pending jobs.

**H2 — deferred (see table D):** `approved_contract_hash`, `contract_hash`, `golden_hash`, `patch_hash`, `CandidateFile.hash`, `CandidateManifest.dependency_hash`, `tool_profile_hash`, `tool_image_digest`, `adapter_hash`, `evaluator_bundle_hash`, `log_ref`, `EvidenceRef.hash`, `SupportingArtifact.hash`, `ComponentProducer.component_hash`, `PendingJob.request_hash`, `solver_config_hash`, `checkpoint_ref`, `last_failure_signature`.

**H3 — computed or compared, not resolved:**
- self/computed and already checked in-record: `CandidateManifest.source_hash` and `Observation.execution_key`;
- compared for equality with the resolved manifest by XR-O1: `Observation.source_hash` and `Observation.dependency_hash` (resolution of their contents is D7/D8).

The inventory at `c1025af` has **37** `ContentId` fields, enumerated by introspection; all 37 appear in H1–H3.

### C — Domain revision chains (`supersedes`)
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-C1 | Task, Requirement, Policy | A version-*v* record's `supersedes` resolves (B2) to a record with the **same chain key** and version **v − 1**. Chain keys: Task `task_id`; Requirement (`task_id`, `requirement_id`); Policy `policy_id`. | Revision 3 superseding revision 1 | Check only that `supersedes` resolves, not v − 1 | 1 per bad link |
| XR-C2 | same | At most one record in the set supersedes a given record (no fork in the set); one head per chain key. | Two revision-2 policies superseding the same revision 1 | Count heads per type, not per chain key | 1 per forked record |
| XR-C3 | Task chain | Every X5-stable field is equal along the chain. | Revision 2 changes `split` (and separately `family_id`, `lineage_id`, `variant_id`, `contract_id`) | Compare only `task_id` | 1 per (link, field) |
| XR-C4 | Requirement chain | (`task_id`, `requirement_id`) is equal along the chain (C5). | Revision 2 of R03 carrying `requirement_id` R17 while superseding R03 v1 | Chain key built from `requirement_id` only | 1 per bad link |
| XR-C5 | Policy chain | `policy_id` and `task_id` are equal along the chain. | Policy revision 2 bound to another `task_id` | `task_id` not compared | 1 per (link, field) |
| XR-C6 | Tasks | All TaskManifests sharing a `family_id` in the set carry the same `split` (family-level split, master §4 p8; set-local only). | Sibling variant in the same family with `split = dev` vs `train` | Split compared per lineage instead of per family | 1 per family |

### P — Task ↔ Requirement ↔ Policy (incl. mandatory coverage)
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-P1 | Policy, Task | `policy.task_id` names a TaskManifest in the set. | Policy for an absent task | — (covered by harness) | 1 per policy |
| XR-P2 | Policy, Task chain | (a) Some revision of the task has `approved_contract_hash == policy.contract_hash`; its *matched revision* is the highest such `manifest_version`. (b) Each head policy matches the **head** task revision (currency, X11). | (a) Unknown `contract_hash`; (b) head policy bound to revision 1's contract after revision 2 changed it | Currency checked against any revision | 1 per policy |
| XR-P3 | Policy, matched Task revision | Every `obligation.requirement_id` ∈ the matched revision's `requirement_ids`. | Obligation for R99 | Checked against the union of all revisions | 1 per (obligation, requirement) |
| XR-P4 | Task head, Requirement heads | Each `requirement_id` in the head task has exactly one head Requirement with that (`task_id`, `requirement_id`). Every Requirement's (`task_id`, `requirement_id`) is listed by some revision of its task. | (a) Task lists R17 with no Requirement; (b) orphan Requirement R42 | — (harness) | 1 per missing/orphan |
| XR-P5 | Requirement heads, head policies | For every `parameter_scope` parameter of a head requirement, **every** configuration of each head policy of that task assigns that name (X6 resolvability; substitute for N1). | Scope names `WIDTH`; one configuration omits `WIDTH` | Missing name treated as "not applicable" | 1 per (requirement, policy, configuration, name) |
| XR-P6 | Task head, Requirement heads, head policy | **PR #9 coverage.** For each head requirement with `disposition = approved` and `mandatory = true`, and each configuration *cfg* of the head policy where it applies (X6), there must exist an obligation *ob* with `ob.requirement_id = id` and a `check ∈ ob.check_ids` such that: `check.mandatory`, `check.kind ≠ quality`, `cfg ∈ check.configuration_ids`, and (`check_id`, `cfg`) is not excluded by any exception. | (a) The only covering check excluded on one configuration by an exception; (b) the obligation's only applicable check made optional; (c) only applicable checks are `quality`; (d) the check targets other configurations only | (i) Exceptions ignored; (ii) the `mandatory` test dropped; (iii) applicability computed with `==` (so `1 == true`) | 1 per (policy, requirement, configuration) gap |
| XR-P7 | same | An approved mandatory head requirement applies to **≥ 1** configuration of each head policy of its task (X12). | `parameter_scope` value set matching no configuration | Empty applicable set treated as satisfied | 1 per (policy, requirement) |

### K — CandidateManifest ↔ Task / parent
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-K1 | Candidate, Task | `candidate.task_id` names a TaskManifest in the set. | Candidate for an absent task | — (harness) | 1 per candidate |
| XR-K2 | Candidate, Task head | The head task's `task_type` is not read-only (`comprehension`, `spec_task`). | Candidate for a `comprehension` task | Read-only set imported incompletely | 1 per candidate |
| XR-K3 | Candidate, Task head | Every `files[].path` is inside the head's `allowed_edit_paths` (X7). | (a) `tb/x.sv` outside scope; (b) `rtl/fifo_old.sv` against entry `rtl/fifo` | Raw `startswith` without the segment separator | 1 per file |
| XR-K4 | Candidate, parent Candidate | `parent_candidate_id` names a Candidate in the set with the same `task_id`. | (a) Parent absent; (b) parent from another task | `task_id` not compared | 1 per candidate |
| XR-K5 | Candidates | Parent ancestry is acyclic. | A→B→A (two candidates whose parents name each other) | Cycle detection limited to self-parent | 1 per cycle (reported at its lexicographically smallest member) |

### O — Observation ↔ exact candidate, policy, check and configuration
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-O1 | Observation, Candidate | Resolved manifest (B2): `candidate_id`, `source_hash`, `dependency_hash` all equal the Observation's. | `dependency_hash` differs (re-keyed so the in-record execution key still holds) | `dependency_hash` not compared (`None` vs value) | 1 per (observation, field) |
| XR-O2 | Observation, Policy, Candidate | Resolved policy: `policy_id` equal; `policy.task_id == candidate.task_id`. | Observation against a policy of another task | Task compared via `policy_id` prefix | 1 per observation |
| XR-O3 | Observation, Policy | `check_id` exists in the policy; `configuration_id ∈ check.configuration_ids`; (`check_id`, `configuration_id`) not excluded. | (a) Unknown check; (b) untargeted configuration; (c) excluded pair | Exceptions ignored | 1 per observation |
| XR-O4 | Observation, Policy check | `check_kind == check.kind`; `visibility == check.visibility`; `tool_profile_id == check.tool_profile_id`; `formal_mode == check.formal_mode`; `formal_depth == check.depth`. | (a) `visibility` development vs hidden check; (b) formal depth 20 vs policy 24 | `visibility` omitted from the comparison | 1 per (observation, field) |

### F — Finding ↔ candidate, requirement and Observations
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-F1 | Finding, Candidate | Resolved manifest: `candidate_id` equal; `manifest.task_id == finding.task_id`. | Finding's `task_id` differs from its candidate's | `task_id` not compared | 1 per finding |
| XR-F2 | Finding, Task head | `requirement_id ∈` head task `requirement_ids`. | Finding for R99 | Checked against Requirement records only | 1 per finding |
| XR-F3 | Finding/Transition, Observations | Every citation (correctness and deciding) resolves (B2), and the Observation's `candidate_manifest_hash` equals the Finding's (FD4). | Deciding citation of a PASS on the parent candidate | Candidate compared by `candidate_id`, not manifest hash | 1 per citation |
| XR-F4 | Transition, Observations | Deciding citations reference Observations with status `PASS` or `FAIL` (FD9). | Confirm citing a `TIMEOUT` | `is_label` replaced by "≠ TOOL_ERROR" | 1 per citation |
| XR-F5 | Transition chain, Observations | If the chain's `check_proposed` transition carries `ExistingPolicyCheck` *e*, every deciding Observation matches *e*'s `policy_hash`, `check_id` and `configuration_id`. For `confirmed`, all statuses equal `e.confirming_status`; for `refuted`, all equal `e.refuting_status`. Mixed PASS/FAIL therefore fails. | (a) Deciding Observation of another configuration; (b) confirmed with FAIL where `confirming_status = PASS`; (c) PASS + FAIL mixed | Refuted compared to `confirming_status` | 1 per citation |
| XR-F6 | Transition, Policy | `ExistingPolicyCheck`: `policy_hash` resolves; `check_id` in it; configuration targeted and not excluded; `policy.task_id == finding.task_id`. `DevelopmentProbeRequest`: `policy_hash` resolves; `configuration_id` in that policy; same task. | (a) Proposal of an excluded pair; (b) probe configuration absent from its policy | Exclusion not checked for proposals | 1 per proposal |
| XR-F7 | Transition chain | If the `check_proposed` transition carries a `DevelopmentProbeRequest`, no transition of that Finding reaches `confirmed`/`refuted` (PR #18 fix 3). | Probe-proposed Finding confirmed with valid PASS citations | Rule checks only the immediately next transition | 1 per finding |
| XR-F8 | Finding, Findings, Transitions | `Finding.derived_from` and `FindingTransition.superseded_by` name Findings in the set with the same `task_id`. | `superseded_by` → absent Finding | Same-task check omitted | 1 per reference |
| XR-F9 *(X13, if accepted)* | Finding, Observations | Producer role `solver` cites no `hidden` Observation. | Solver Finding citing a hidden-check Observation | Role check omitted | 1 per citation |

### T — FindingTransition chains
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-T1 | Transition, Finding | `finding_hash` resolves (B2) to the Finding with `finding_id`; all transitions of one `finding_id` carry the same `finding_hash`. | Transition 2 bound to a different Finding revision of the same id | Only the first transition checked | 1 per transition |
| XR-T2 | Transitions of a Finding | Sequences are exactly 1…n (no gaps; duplicates are B1). | Sequences 1, 3 | Only monotonic, not contiguous | 1 per finding |
| XR-T3 | consecutive pair | `previous_transition_hash == content_id(transition n−1)`. | Points at a non-adjacent transition | Compared to `finding_hash` | 1 per transition |
| XR-T4 | consecutive pair | `from_status == previous.to_status`. | `check_proposed → confirmed` following a `hypothesis → dropped` | — (harness) | 1 per transition |
| XR-T5 | chain | No transition follows a terminal `to_status` (confirmed, refuted, dropped). | Transition after `dropped` | Terminal set taken from the wrong constant | 1 per finding |

T4 and T5 overlap through the edge table, by design. T5 stays a separate defence if the table is ever edited.

### E — EpisodeState chains
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-E1 | States of (`task_id`, `episode_id`) | Sequences exactly 0…n; `previous_state_hash == content_id(state n−1)`. One chain per pair (a second sequence-0 is B1). | (a) Sequence gap; (b) predecessor hash of state n−2 | Off-by-one: chain starts at 1 | 1 per episode |
| XR-E2 | consecutive pair | (`prev.state`, `cur.state`) ∈ `ALLOWED_EPISODE_TRANSITIONS` (ADR-0006). | `PLAN → SUBMIT` | Table imported from the lifecycle-only subset | 1 per pair |
| XR-E3 | consecutive pair | (a) If `prev.state = WAITING`, `cur.state ∈ {prev.resume_state, ABORTED}`. (b) If `cur.state = WAITING`, `cur.resume_state == prev.state` (X9). | (a) WAITING(resume = DEV_CHECK) → TRIAGE; (b) IMPLEMENT → WAITING(resume = PLAN) | ABORTED not allowed out of WAITING (false positive) | 1 per pair |
| XR-E4 | chain | Nothing follows COMPLETED or ABORTED. | Snapshot after COMPLETED | — (harness) | 1 per episode |
| XR-E5 | chain | `policy_id`, `policy_hash`, `budget_hash` and `solver_config_hash` are constant (the budget cannot change mid-episode). | `budget_hash` → a larger budget at sequence 3 | `solver_config_hash` omitted | 1 per (episode, field) |
| XR-E6 | State, Policy, Budget | `policy_hash` resolves (B2) with equal `policy_id` and `policy.task_id == state.task_id`; `budget_hash` resolves to an EpisodeBudget. | Policy of another task | Policy resolved by id | 1 per state |
| XR-E7 | consecutive pair | `spent` (each dimension) and `wall_clock_elapsed_ms` never decrease. | `tool_calls` 7 → 6 | Only the vector sum compared | 1 per (pair, dimension) |
| XR-E8 | State, Budget | Per dimension, `spent + reserved ≤ limits`, and `wall_clock_elapsed_ms ≤ wall_clock_limit_ms`, except the per-dimension ABORTED exemptions in X10. | (a) Overspend in `sim_jobs` at TRIAGE; (b) overspend at ABORTED(`wall_clock_exhausted`), where the additive rule is not exempt | `<` vs `≤` (exact-limit false positive); exemption applied to all dimensions | 1 per (state, dimension) |
| XR-E9 | State, Candidates | Every `CandidateBinding` (active, best, pending) resolves (B2); `manifest.task_id == state.task_id`; producer is `solver` or `architecture_explorer` with `episode_id == state.episode_id` (004 F6). | (a) Reconstructor candidate as active; (b) solver candidate of another episode | Explorer branch not checked against `episode_id` | 1 per binding |
| XR-E10 | chain | A `JobId` keeps the same (`request_hash`, `candidate`, `reserved`) in every snapshot that lists it. Once absent from a later snapshot, it never reappears in that chain (no reuse within the set). | (a) Same `JobId`, new `request_hash`; (b) job reappears after removal | Reappearance check omitted | 1 per (episode, job) |

## Deferred: invariants needing store/event-log authority or non-existent records (table D)
None of these is approximated in 009. "New record?" marks cases that are impossible without a record type that does not exist; they are **surfaced, not invented**.

| # | Invariant (source) | Why not in 009 | Owner | New record? |
|---|---|---|---|---|
| D1 | A cited Observation is *stored*; chains are *complete* (no hidden later transition or snapshot); a set head is the *global* head; no fork ever exists (006, 007, C2) | Needs store-wide authority, not a set | P1.2 | no |
| D2 | (`task_id`, `episode_id`) globally unique; `JobId` never reused within an episode (007 ED15) | Set-local part is XR-B1/E1/E10; global part needs the store | P1.2 / P1.5 | no |
| D3 | `PendingJob.request_hash` resolves to the immutable job request in the event log; whether the request requires a candidate (007) | No job-request record; event log | P1.2 / P1.4 / P1.5 | **yes** (job request) |
| D4 | `evaluator_bundle_hash` matches the task evaluator's bundle; expected test/property inventories equal the bundle's; equivalence commits to `golden_hash` (005, R5) | No evaluator-bundle manifest | P1.4 / P1.6 | **yes** (evaluator-bundle manifest) |
| D5 | `tool_profile_hash` resolves to the profile named by `tool_profile_id`; image and adapter digests | No ToolProfile record; images and adapters are P1.3/P1.4 | P1.4 | **yes** (tool profile) |
| D6 | `approved_contract_hash`/`contract_hash` resolve to the contract artifact; configuration parameter names belong to the contract's parameter vocabulary (003, Q5) | No Contract record; parameter vocabulary undefined | P1.6 (FIFO authority) / P3 | **yes** (contract; see N1) |
| D7 | `golden_hash`, `patch_hash`, `CandidateFile.hash`, `log_ref`, evidence, supporting artifact, `checkpoint_ref` blobs exist and match bytes | Content-addressed blob store | P1.2 | no (blobs) |
| D8 | `dependency_hash` resolves to a dependency bundle (004 F4, §8.10) | Dependency-bundle definition | P1.5 | **yes** (dependency bundle) |
| D9 | `solver_config_hash` resolves (007 ED14) | Solver-config record | P1.5 / P5.1 | **yes** (solver config) |
| D10 | Probe promotion: a promoted check is created as a later policy version, and the decided Finding is a new `derived_from` Finding (006) | Needs a promotion event or relation; 009 enforces only the prohibition (XR-F7) | P1.5 / P4 | event, not record |
| D11 | Accounting truth: `spent` equals the resources consumed by recorded jobs, Observations and tokens; cancelled-job reservation spent vs released (007) | Event log and controller accounting | P1.5 | no |
| D12 | Failure-signature progression (`failure_repeat_count` vs signature changes) (007 ED11) | `failure_signature_v1` is P1.5's | P1.5 | no |
| D13 | `ComponentProducer.component_hash` resolves to a registered component build | Component registry | P1.2 / P5 | no |
| D14 | Requalification: Observations or Findings against a superseded policy, requirement or contract are invalidated (§8, AGENTS §3) | Event-driven invalidation | P1.5 / P4 | no |
| D15 | `Requirement.disposition = ambiguous` blocks qualification | Qualification workflow | P4 | no |

### Surfaced for coordinator review (not invented)
- **N1:** "configuration parameter names match the task's contract" (003) is impossible without a contract record or parameter vocabulary. 009 offers XR-P5 (requirement scopes resolve against every configuration) as the in-bundle substitute. The rule itself stays D6.
- **N2:** `CandidateManifest` does not pin the task revision (Q2, X8).
- **Open questions:** each would be a new rule, so none is enforced unless the coordinator adds it.
  - Must a `MutationSource.parent_task_id` task share the child's `family_id` and `split`?
  - Must all candidates of one task agree on whether `dependency_hash` is `None` (F4: "this task explicitly has no dependency bundle")?
  - Must an `ExistingPolicyCheck` belong to an obligation of the Finding's `requirement_id`?
  - Must all configurations of one policy assign the same parameter names?

## Test design
- **Coherent bundle builder** (`tests/contract/cross_record/_bundle.py`):
  - built from a typed spec;
  - `seal()` constructs records in dependency order, computing every H1 hash from the record it names;
  - mutations are spec edits before sealing, plus post-seal tamper helpers for B2.
- **Positive scenarios.** One FIFO task family, all clean:
  - task revisions 1→2 (contract revision);
  - requirements R03 and R17, with R17 revised;
  - policy revisions 1→2, with an exception, a quality check, and an `all_supported_configs` plus a `parameter_scope` requirement;
  - candidates: first, child, oracle-side explorer, solver-side explorer;
  - Observations PASS/FAIL/TIMEOUT across checks and configurations;
  - Finding A: proposes an existing check → confirmed;
  - Finding B: probe → dropped(`no_executable_check`);
  - Finding C: superseded by D (`derived_from`);
  - Episode 1: PREPARE…COMPLETED, including a WAITING excursion and exact-limit spending;
  - Episode 2: ABORTED(`budget_exhausted`) with exempt overspend.
- **Exact-set assertions:** every negative test asserts `{v.code for v in check_records(...)} == {target}` and the documented cardinality.
- **Rule-removal harness:** CI runs it as a test. Rules are registered one function per `InvariantCode`. For each code, the test runs the validator with that rule removed and asserts:
  - the code's negative fixtures yield **no** violation, so the rule is load-bearing and isolated;
  - the positive bundle is unchanged.
- **Properties (hypothesis):**
  - shuffled and duplicated input yields an identical result (order independence and idempotence);
  - the positive bundle stays clean under any input permutation.
- **Manual planted bugs:** the "Planted bug" column above. At minimum P6 (i)–(iii), K3, E1, E3, E8, B2, F5 and T2 are run and recorded with counts. Source is restored byte-identically.

## Scope
- In scope: the B/C/P/K/O/F/T/E invariants above as pure functions, the coherent bundle builder, positive/negative/property/planted-bug tests, and docs.
- Allowed paths:
  - `src/sindri/schemas/cross_record.py` (new; X1);
  - `src/sindri/schemas/__init__.py` (exports only);
  - `tests/contract/cross_record/` (new);
  - `components/schemas.yaml` (cross-record invariants, public API);
  - `docs/REPO_MAP.md`;
  - this packet, the handoff, and the task-board status.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none touched. Hidden-visibility data is test fixture data only.
- Other forbidden paths:
  - existing schema modules (`task.py` … `episode.py`, `_base.py`) and `core/ids.py`: **no schema change**;
  - the §20 example files under `tests/contract/examples/`;
  - any store, event log, controller or judge code.

## Non-goals
- No new record type, field or schema change (Q2/N1/N2 are surfaced only).
- No store, persistence, event log, ingest boundary, query layer or global uniqueness (D1, D2).
- No controller transition logic, requalification or invalidation (D14), no judge verdicts, and no accounting truth (D11).
- No evaluator-bundle, tool-profile, contract, dependency-bundle, job-request or solver-config records (D3–D9).
- No automatic repair or normalisation of a bundle; the validator only reports.
- P1.1-G work: JSON Schema export, and the integration sweep.

## Interfaces touched
- Schemas: none changed. New: the `check_records`, `Violation` and `InvariantCode` public API (X1/X2).
- Tool APIs, DB/migrations, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The coherent bundle (all positive scenarios) yields `()`.
- [ ] The result is independent of input order and of duplicate identical records (property test).

Negative:
- [ ] Every negative mutation in the catalogue yields exactly `{its code}` with the documented cardinality.
- [ ] An unresolved reference yields one XR-B2 violation and no cascade.
- [ ] Mandatory coverage (XR-P6) fails for each of: exception exclusion, an optional-only check, a quality-only check, an untargeted configuration, and `1` vs `true` applicability.

Tests:
- [ ] The rule-removal harness proves every registered rule is load-bearing and isolated.
- [ ] XR-B3: every `ContentId` field in the P1.1 schemas is classified exactly once (H1/H2/H3); adding an unclassified field fails.
- [ ] Planted bugs recorded with counts; source restored byte-identically.

Documentation:
- [ ] `components/schemas.yaml`: cross-record invariants plus the public API.
- [ ] `docs/REPO_MAP.md` updated.
- [ ] Packet completion evidence and handoff written, including table D owners and the surfaced N1/N2/open questions.

Boundaries:
- [ ] No existing schema module, `core/ids.py` or example file changed.
- [ ] No store, controller or judge code.

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
uv run pytest -q tests/contract/cross_record
git diff --stat origin/main -- src/sindri/schemas/_base.py src/sindri/schemas/task.py src/sindri/schemas/requirement.py src/sindri/schemas/policy.py src/sindri/schemas/candidate.py src/sindri/schemas/observation.py src/sindri/schemas/finding.py src/sindri/schemas/episode.py src/sindri/core tests/contract/examples   # must be empty
```

## Plan of record
- `src/sindri/schemas/cross_record.py`: `InvariantCode`, `Violation`, `check_records`, plus one private rule function per code, registered in a table.
- `src/sindri/schemas/__init__.py`: export the three public names.
- `tests/contract/cross_record/`, one module per group:
  - `_bundle.py`;
  - `test_bundle_integrity.py` (B);
  - `test_revision_chains.py` (C);
  - `test_policy_coverage.py` (P);
  - `test_candidate_bindings.py` (K);
  - `test_observation_bindings.py` (O);
  - `test_finding_bindings.py` (F, T);
  - `test_episode_chains.py` (E);
  - `test_rule_harness.py`;
  - `test_hash_inventory.py` (B3).
- `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-009.md`, and the task board.

If X1 is decided as tests-only, the same rules live under `tests/contract/cross_record/_rules.py`, and the `src/` rows drop out.

## Status
`planned` (authoritative status: `implementation/task_board.yaml`). Open decisions X1–X13, plus N1, N2 and the open questions.

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
