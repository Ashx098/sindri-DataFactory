# SIN-P1.1-009 — Cross-record invariant tests

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
Given a deliberately assembled, **closed validation bundle** of already-valid P1.1 records, one
pure, deterministic function reports every violation of the cross-record rules deferred by
SIN-P1.1-002…008. The rules cover:
- hashes resolve to the exact records they name;
- revision chains keep their identity;
- the policy enforces every approved mandatory requirement in every configuration where it applies;
- Observations, Findings and FindingTransitions bind to the exact candidate, policy and check;
- EpisodeState chains are continuous, legal and monotonic.

Rules that need store or event-log authority, or record types that do not exist yet, are listed
with their owner rather than approximated.

## Why / architecture references
- Master architecture:
  - §4 principle 8: split assigned at family level.
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
  - 004 Non-goals and F4/F6;
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
- Required schemas/contracts: all of `sindri.schemas` and `sindri.core.ids`; read-only use. No schema change.

## Facts established by read-only probes on `main` `c1025af` (before drafting)
| # | Observation | Consequence |
|---|---|---|
| Q1 | The adapted §20 example files are **not mutually consistent**. Of 17 cross-links probed, 9 fail: `policy.task_id ≠ task`; obligation requirements R01/R02 ∉ task R03/R17; candidate files fall outside the edit scope; `observation.candidate_manifest_hash`/`policy_hash`/`policy_id`, the Finding's candidate hash and citation, and `episode_state.policy_hash` do not match the example records. | 009 **builds a coherent bundle by construction** from a typed spec. The example files stay unchanged; 002–008 tests depend on them byte for byte. |
| Q2 | `CandidateManifest` binds `task_id` only; `EvaluationPolicy` binds `task_id` + `contract_hash` only; `Finding` binds a logical `requirement_id` only. | Exact *historical* revision bindings are not representable (L1–L3); 009 checks current-bundle consistency. |
| Q3 | References by **ID only** (`parent_candidate_id`, `MutationSource.parent_task_id`, `derived_from`, `superseded_by`, `Finding.requirement_id`, `policy.task_id`, `candidate.task_id`) can form cycles and can dangle; references by **hash** cannot form cycles. | Closed-world resolution (X4) and explicit acyclicity rules (XR-K5, XR-C8, XR-F11). |
| Q4 | **37** `ContentId` fields across the P1.1 schemas (introspection); several name artifacts with **no P1.1 record type**. | Each is classified exactly once (CT-1); unresolvable ones are owned later (table D). |
| Q5 | No record defines a contract parameter vocabulary. | N1: in-bundle substitute only (XR-P8, XR-P5); contract validation stays D6. |

## Coordinator decisions (PR #26 comment `5988242704`, 2026-10-05; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| X1 | **Product code accepted.** Pure validator in `src/sindri/schemas/cross_record.py`: no I/O, clock, store or mutation of inputs. To avoid package cycles it imports the concrete schema modules directly (`sindri.schemas.task`, …), never record classes back through `sindri.schemas`. `schemas/__init__.py` may export the public API after the module is defined. P1.2/P1.5/P1.7 consume this one implementation. |
| X2 | **Accepted, with boundary clarification.** `check_records(records: Iterable[Record]) -> tuple[Violation, ...]`; no bundle record. `Violation{code, subject, detail}` is a frozen strict value object, **not a `Record`**. `InvariantCode` is a `StrEnum` of runtime codes only. Non-`Record` values **and unsupported `Record` subclasses** raise `TypeError`; nothing is silently ignored. `subject` and `detail` are deterministic strings built from IDs, hashes and sorted values, never object reprs. |
| X3 | **Aggregate, no cascades, with explicit blockers.** Exact duplicates collapse by (concrete type, `content_id()`). A conflicting logical key (XR-B1) is **ambiguous authority**: downstream rules that would have to choose among the conflicting records skip that key. A broken H1 reference emits exactly **one XR-B2 per reference occurrence/path**, and rules depending on it skip it. Results sort by (`code.value`, `subject`, `detail`). Full ordering: "Dependency ordering" below. |
| X4 | **Closed world accepted.** `check_records` validates a deliberately assembled closed validation bundle, **not an arbitrary partial store query**. Every reference to a P1.1 record type must resolve inside it. A *set head* is a record that nothing in the set supersedes. P1.2 may use the function only after gathering the required closure; global completeness and current-head authority stay with the store (D1). |
| X5 | **Accepted.** Stable across TaskManifest revisions: `task_id`, `family_id`, `lineage_id`, `variant_id`, `split`, `contract_id`, `task_type`, `authority_mode`, `source`. May change by revision: `approved_contract_hash`, `golden_hash`, `rights`, `allowed_edit_paths`, `requirement_ids`. |
| X6 | **Exact-type applicability accepted, amended with a policy vocabulary.** Within one policy, every Configuration carries the **same set of assignment names** (all empty is valid for a zero-parameter task): XR-P8. A `parameter_scope` requirement may name only parameters in that common vocabulary (XR-P5). It applies iff every named value matches under exact-type equality (`true ≠ 1 ≠ "1"`). A missing scoped name is a violation, never "not applicable". This is in-bundle consistency only and does **not** replace D6. |
| X7 | **Accepted.** Exact path or POSIX segment prefix (`entry + "/"`) only; no raw prefix and no globbing. |
| X8 | **Accepted as a current-bundle rule.** XR-K2/K3 use the set-head TaskManifest. This validates a candidate against the bundle's *current* task authority, not the revision in force when the candidate was created (L1). No field is added in 009. |
| X9 | **Accepted.** Entering WAITING records the state actually paused: `cur.resume_state == prev.state`. WAITING exits only to that state or to ABORTED. |
| X10 | **Per-dimension exemptions accepted, plus truthful abort reasons.** `budget_exhausted` exempts only additive-limit overflow; `wall_clock_exhausted` exempts only wall-clock overflow. `infrastructure_failure`, `stagnation` and `cancelled` exempt nothing. Additionally (XR-E11): for mixed zero/positive additive limits, `budget_exhausted` is truthful only when ≥ 1 **positive-limit** dimension has `spent + reserved ≥ limit`; zero-limit dimensions are disabled and do not trigger it. If **all** additive limits are zero, `budget_exhausted` is valid at zero usage because no additive budget is available. `wall_clock_exhausted` requires `wall_clock_elapsed_ms ≥ wall_clock_limit_ms`. |
| X11 | **Head coverage accepted; historical matching amended.** A head policy matches the head task's `approved_contract_hash` (XR-P2B), and XR-P3/P6/P7 use the head task and head requirements. A **non-head** policy is not bound to an invented "highest matching revision". Instead: (a) its `contract_hash` appears on ≥ 1 revision of its task (XR-P2A); (b) each obligation requirement appears in ≥ 1 revision of that task carrying that contract hash (XR-P3, historical form). Exact historical policy→manifest binding is not representable (L2). |
| X12 | **Accepted.** An approved mandatory requirement applying to zero configurations of a head policy is a violation (XR-P7). |
| X13 | **Accepted for definite solver provenance.** A Finding with `producer.role == solver` cites no `hidden` Observation, in correctness or deciding citations (XR-F9). Provenance that cannot be classified as solver-side or judge-side from the record is **not guessed**; it is a P1.5 solver-safe-projection follow-up (D19). |
| OQ1 | **Mutation lineage enforced.** `MutationSource.parent_task_id` resolves; a mutation child keeps the parent's `family_id` and `lineage_id`, so split equality follows from XR-C6. Mutation ancestry is acyclic. (XR-C7, XR-C8) |
| OQ2 | **Dependency bundle is task-consistent in v1.** All CandidateManifests of one `task_id` carry the same `dependency_hash`, including `None` (F4: `None` means *this task* has no external bundle). (XR-K6) Resolution of a non-null bundle stays D8. |
| OQ3 | **ExistingPolicyCheck relevance enforced.** In the proposal's exact policy, the proposed `check_id` occurs in ≥ 1 obligation whose `requirement_id == Finding.requirement_id`. (XR-F10) A DevelopmentProbeRequest stays supporting-only, with no obligation requirement. |
| OQ4 | **Configuration parameter-name sets: yes.** This is the X6 vocabulary rule (XR-P8): an exact-configuration matrix rule, not a substitute for the future Contract record. |
| R1 | Catalogue corrections: C1 checks only same type and v − 1; logical identity is owned by C3/C4/C5. **XR-C2 dropped** as a runtime code: a fork is structurally implied by B1 + C1, and a derived one-head test remains (CT-2). **XR-B3 is a contract test** (CT-1), not a runtime code. Explicit no-cascade ownership. E9 relaxed to a same-task, same-or-no-episode rule. Finding-lineage acyclicity added. Historical-binding limitations recorded. |

## Dependency ordering (no-cascade ownership; tested once)
A rule runs on a record or pair only when the authority it needs is unambiguous and resolved;
otherwise it skips silently, and the owning rule reports.
1. **XR-B1** ambiguous key → every rule that would select by that key skips it.
2. **XR-B2** unresolved H1 reference (per occurrence) → every rule that reads through that reference skips it.
3. ID-only resolution owners skip their dependants:

   | When this owner fails… | …these rules skip |
   |---|---|
   | XR-P1 (policy → task) | P2–P8 for that policy |
   | XR-K1 (candidate → task) | K2/K3/K6 for that candidate |
   | XR-K4 (parent) | K5 on that edge |
   | XR-C7 (mutation parent unresolved) | C8 on that edge |
   | XR-F8 (unresolved link) | F11 on that edge |
   | XR-P4 (missing requirement head) | P5–P7 for that requirement |
4. **Policy shape:**
   - XR-P8 failing for a policy → P5–P7 skip that policy;
   - XR-P5 failing for a (requirement, policy) → P6/P7 skip that pair;
   - XR-P2A failing → P3 skips that policy;
   - XR-P2B failing → P3, P6 and P7 for that head policy skip; currency failed, so coverage would be judged against the wrong task revision.
5. **Findings:**
   - XR-F4 owns "deciding status ∈ {PASS, FAIL}", and XR-F5 inspects only verdict-bearing citations;
   - XR-F6 failing for a proposal → F5 and F10 skip it.
6. **Transitions:**
   - XR-T2 owns gaps, and XR-T3 compares predecessor hashes only across contiguous sequence pairs;
   - XR-T5 owns "nothing after terminal", and XR-T4 skips a pair whose previous `to_status` is terminal.
7. **Episodes:**
   - XR-E1 owns gaps and predecessor hashes;
   - XR-E4 owns "nothing after terminal", and XR-E2/E3 skip a pair whose previous state is terminal;
   - XR-E6 failing (budget unresolved) → E8/E11 skip that state.

## Invariant catalogue: runtime rules enforceable over the bundle in 009
Conventions:
- **Positive fixture:** the coherent bundle (see Test design), which must produce `()`.
- **Negative mutation:** a spec edit **before sealing**, so every dependent hash is recomputed and only the targeted rule fails. The test asserts the exact code set `{code}` **and** the documented cardinality.
- Hash tampering (XR-B2) is applied after sealing.
- **Planted bug:** the automated rule-removal harness is the exhaustive proof for every runtime code. The manual source plant listed per row is a representative subset, run and recorded.
- **Report:** what one violation is counted against. All rules aggregate (X3).

### B — Bundle structure and hash resolution
| ID | Input records | Pass condition (deterministic) | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-B1 | all | Each logical key names one content. Keys: Task (`task_id`, `manifest_version`); Requirement (`task_id`, `requirement_id`, `requirement_version`); Policy (`policy_id`, `policy_version`); Candidate `candidate_id`; Observation `observation_id`; Finding `finding_id`; Transition (`finding_id`, `sequence`); EpisodeState (`task_id`, `episode_id`, `sequence`). Exact duplicates collapse first. | Two Observations with the same id and different `summary` | Key compared by content_id instead of logical key | 1 per conflicting key |
| XR-B2 | all | Every H1 reference occurrence resolves to exactly one record of the declared type with `content_id() == hash`. Where an ID travels with the hash (candidate, policy, observation, finding), the resolved record's ID equals it. | (a) `observation_hash` → unknown hash; (b) right hash, wrong `observation_id`; (c) `policy_hash` → a Candidate's content_id (type confusion) | Resolve by ID, ignoring the hash | 1 per reference occurrence (path) |

**H1 — resolved by XR-B2:**
- `TaskManifest.supersedes`, `Requirement.supersedes` and `EvaluationPolicy.supersedes`;
- `Observation.candidate_manifest_hash` (+`candidate_id`) and `Observation.policy_hash` (+`policy_id`);
- `ObservationCitation.observation_hash` (+`observation_id`), in Finding correctness citations and transition deciding citations;
- `FindingTransition.finding_hash` (+`finding_id`) and `previous_transition_hash`;
- `ExistingPolicyCheck.policy_hash` and `DevelopmentProbeRequest.policy_hash`;
- `Finding.candidate_manifest_hash` (+`candidate_id`);
- `EpisodeState.previous_state_hash`, `policy_hash` (+`policy_id`) and `budget_hash`;
- `CandidateBinding.candidate_manifest_hash` (+`candidate_id`), in the active and best candidate and in pending jobs.

**H2 — deferred (table D):** `approved_contract_hash`, `contract_hash`, `golden_hash`, `patch_hash`, `CandidateFile.hash`, `CandidateManifest.dependency_hash` (compared by XR-K6, resolved in D8), `tool_profile_hash`, `tool_image_digest`, `adapter_hash`, `evaluator_bundle_hash`, `log_ref`, `EvidenceRef.hash`, `SupportingArtifact.hash`, `ComponentProducer.component_hash`, `PendingJob.request_hash`, `solver_config_hash`, `checkpoint_ref`, `last_failure_signature`.

**H3 — computed or compared, not resolved:**
- self/computed and already checked in-record: `CandidateManifest.source_hash` and `Observation.execution_key`;
- compared with the resolved manifest by XR-O1: `Observation.source_hash` and `Observation.dependency_hash`.

H1 + H2 + H3 = all 37 fields at `c1025af`.

### C — Domain revision chains and task lineage
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-C1 | Task, Requirement, Policy | A version-*v* record's `supersedes` resolves (B2) to a record of the **same type** with version **v − 1**. No logical-key equality here. | Revision 3 superseding revision 1 | `supersedes` resolution only, v − 1 unchecked | 1 per link |
| XR-C3 | Task chain | Every X5-stable field (incl. `task_id`) is equal across each link. | Revision 2 changes `split` (and separately `family_id`, `variant_id`, `contract_id`, `source`) | Compare only `task_id` | 1 per (link, field) |
| XR-C4 | Requirement chain | (`task_id`, `requirement_id`) is equal across each link (C5). | Revision 2 superseding R03 v1 carries `requirement_id` R17 | `task_id` compared, `requirement_id` not | 1 per (link, field) |
| XR-C5 | Policy chain | `policy_id` and `task_id` are equal across each link. | Policy revision 2 bound to another `task_id` | `task_id` not compared | 1 per (link, field) |
| XR-C6 | Tasks | All TaskManifests sharing a `family_id` in the set carry the same `split` (set-local; global P2.6). | Sibling variant in the same family with `split = dev` vs `train` | Split compared per lineage instead of per family | 1 per family |
| XR-C7 | Task (mutation source), parent Task | `MutationSource.parent_task_id` names a TaskManifest in the set, and the child (each revision) has the parent head's `family_id` and `lineage_id` (OQ1). | (a) Parent absent; (b) child invents another `family_id` | `lineage_id` not compared | 1 per (task revision, failure) |
| XR-C8 | Tasks | Mutation ancestry (`task_id → parent_task_id` over set heads) is acyclic. | T1 mutates T2 and T2 mutates T1 (same family/lineage) | Detects only self-parent | 1 per cycle, at its smallest `task_id` |

**CT-2 (contract test, not a runtime code):** in every valid chain, B1 + C1 imply exactly one set head per chain key. A fork mutation necessarily trips B1 or C1. Global no-fork and current head are D1.

### P — Task ↔ Requirement ↔ Policy (incl. mandatory coverage)
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-P1 | Policy, Task | `policy.task_id` names a TaskManifest in the set. | Policy for an absent task | — (harness) | 1 per policy |
| XR-P2A | Policy, Task chain | `policy.contract_hash` equals `approved_contract_hash` of ≥ 1 revision of `policy.task_id`. | Unknown `contract_hash` | Compared against any task's revisions | 1 per policy |
| XR-P2B | Head policy, head Task | Each head policy's `contract_hash == ` head task `approved_contract_hash` (currency). | Head policy still on revision 1's contract after revision 2 changed it | Currency checked against any revision | 1 per head policy |
| XR-P3 | Policy, Task chain | **Head policy:** every `obligation.requirement_id ∈` head task `requirement_ids`. **Non-head policy:** each obligation requirement appears in ≥ 1 revision of the task with `approved_contract_hash == policy.contract_hash` (X11). | Obligation for R99 (head); non-head obligation requirement listed only by a revision with another contract hash | Non-head checked against the union of all revisions | 1 per (policy, requirement) |
| XR-P4 | Task head, Requirement heads, Requirements | Each `requirement_id` of the head task has exactly one head Requirement with that (`task_id`, `requirement_id`). Every Requirement's (`task_id`, `requirement_id`) is listed by ≥ 1 revision of its task. | (a) Task lists R17 with no Requirement; (b) orphan Requirement R42 | — (harness) | 1 per missing/orphan |
| XR-P8 | Policy | All configurations of a policy carry the same set of assignment names (empty everywhere is valid) (X6/OQ4). | One configuration omits `DEPTH` | Names compared on the first two configurations only | 1 per policy |
| XR-P5 | Requirement heads, head policies of the task | Every `parameter_scope` name of a head requirement belongs to each head policy's common vocabulary (XR-P8). | Scope names `WIDTHX` | Missing name treated as "not applicable" | 1 per (requirement, policy, name) |
| XR-P6 | Task head, Requirement heads, head policy | **PR #9 coverage.** For each head requirement listed by the head task with `disposition = approved` and `mandatory = true`, and each configuration *cfg* of the head policy where it applies (X6), there must exist an obligation *ob* with `ob.requirement_id = id` and a `check ∈ ob.check_ids` such that: `check.mandatory`, `check.kind ≠ quality`, `cfg ∈ check.configuration_ids`, and (`check_id`, `cfg`) is not excluded by any exception. | (a) The only covering check excluded on one configuration; (b) the only applicable check made optional; (c) only `quality` checks apply; (d) the check targets other configurations only; (e) applicability `1` vs `true` | (i) Exceptions ignored; (ii) the `mandatory` test dropped; (iii) applicability compared with `==` | 1 per (policy, requirement, configuration) gap |
| XR-P7 | same | An approved mandatory head requirement applies to ≥ 1 configuration of each head policy of its task (X12). | `parameter_scope` value set matching no configuration | Empty applicable set treated as satisfied | 1 per (policy, requirement) |

### K — CandidateManifest ↔ Task / parent
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-K1 | Candidate, Task | `candidate.task_id` names a TaskManifest in the set. | Candidate for an absent task | — (harness) | 1 per candidate |
| XR-K2 | Candidate, Task head | The head task's `task_type` is not read-only (`comprehension`, `spec_task`) (X8, current authority). | Candidate for a `comprehension` task | Read-only set incomplete | 1 per candidate |
| XR-K3 | Candidate, Task head | Every `files[].path` is inside the head's `allowed_edit_paths` (X7, X8). | (a) `tb/x.sv` outside scope; (b) `rtl/fifo_old.sv` against entry `rtl/fifo` | Raw `startswith` without the segment separator | 1 per file |
| XR-K4 | Candidate, parent Candidate | `parent_candidate_id` names a Candidate in the set with the same `task_id`. | (a) Parent absent; (b) parent from another task | `task_id` not compared | 1 per candidate |
| XR-K5 | Candidates | Parent ancestry is acyclic. | A→B→A | Detects only self-parent | 1 per cycle, at its smallest `candidate_id` |
| XR-K6 | Candidates of a task | All CandidateManifests of one `task_id` carry the same `dependency_hash`, including `None` (OQ2). | One candidate `None`, another a bundle hash | `None` excluded from the comparison | 1 per task |

### O — Observation ↔ exact candidate, policy, check and configuration
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-O1 | Observation, Candidate | Resolved manifest (B2): `source_hash` and `dependency_hash` equal the Observation's. | `dependency_hash` differs (re-keyed, so the in-record execution key holds) | `dependency_hash` not compared (`None` vs value) | 1 per (observation, field) |
| XR-O2 | Observation, Policy, Candidate | `policy.task_id == candidate.task_id` for the resolved policy and manifest. | Observation against a policy of another task | Task compared via `policy_id` prefix | 1 per observation |
| XR-O3 | Observation, Policy | `check_id` exists in the policy; `configuration_id ∈ check.configuration_ids`; (`check_id`, `configuration_id`) not excluded. | (a) Unknown check; (b) untargeted configuration; (c) excluded pair | Exceptions ignored | 1 per observation |
| XR-O4 | Observation, Policy check | `check_kind == check.kind`; `visibility == check.visibility`; `tool_profile_id == check.tool_profile_id`; `formal_mode == check.formal_mode`; `formal_depth == check.depth`. Skips if O3 failed. | (a) `visibility` development vs hidden check; (b) formal depth 20 vs policy 24 | `visibility` omitted | 1 per (observation, field) |

### F — Finding ↔ candidate, requirement, policy and Observations
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-F1 | Finding, Candidate | `manifest.task_id == finding.task_id` for the resolved manifest. | Finding's `task_id` differs from its candidate's | `task_id` not compared | 1 per finding |
| XR-F2 | Finding, Task head | `requirement_id ∈` head task `requirement_ids` (current authority; L3). | Finding for R99 | Checked against Requirement records only | 1 per finding |
| XR-F3 | Finding/Transition, Observations | Every resolved citation's Observation has `candidate_manifest_hash` equal to the Finding's (FD4). | Deciding citation of a PASS on the parent candidate | Compared by `candidate_id`, not manifest hash | 1 per citation |
| XR-F4 | Transition, Observations | Deciding citations reference Observations with status `PASS` or `FAIL` (FD9). Owner of this check. | Confirm citing a `TIMEOUT` | `is_label` replaced by "≠ TOOL_ERROR" | 1 per citation |
| XR-F5 | Transition chain, Observations | If the chain's `check_proposed` transition carries `ExistingPolicyCheck` *e*, every **verdict-bearing** deciding Observation matches *e*'s `policy_hash`, `check_id` and `configuration_id`. For `confirmed`, statuses equal `e.confirming_status`; for `refuted`, they equal `e.refuting_status`. Mixed PASS/FAIL fails. | (a) Deciding Observation of another configuration; (b) confirmed with FAIL where `confirming_status = PASS`; (c) PASS + FAIL mixed | Refuted compared with `confirming_status` | 1 per citation |
| XR-F6 | Transition, Policy | `ExistingPolicyCheck`: `check_id` in the resolved policy; configuration targeted and not excluded; `policy.task_id == finding.task_id`. `DevelopmentProbeRequest`: `configuration_id` in the resolved policy; same task. | (a) Proposal of an excluded pair; (b) probe configuration absent from its policy | Exclusion not checked for proposals | 1 per proposal |
| XR-F10 | Transition, Policy, Finding | For an `ExistingPolicyCheck`, the proposed `check_id` occurs in ≥ 1 obligation of that exact policy whose `requirement_id == Finding.requirement_id` (OQ3). | Finding about R17 proposing a check obligated only for R03 | Obligation scan over all policies | 1 per proposal |
| XR-F7 | Transition chain | If the `check_proposed` transition carries a `DevelopmentProbeRequest`, no transition of that Finding reaches `confirmed`/`refuted` (PR #18 fix 3). | Probe-proposed Finding confirmed with valid PASS citations | Checks only the immediately next transition | 1 per finding |
| XR-F8 | Finding, Findings, Transitions | `Finding.derived_from` and `FindingTransition.superseded_by` name Findings in the set with the same `task_id`. | (a) `superseded_by` → absent Finding; (b) `derived_from` → Finding of another task | Same-task check omitted | 1 per reference |
| XR-F11 | Findings, Transitions | The `derived_from` graph and the `superseded_by` graph are each acyclic (the schemas reject only self-links). | (a) `derived_from` A→B→A; (b) superseded-by A→B→A | Detects only 1-cycles | 1 per (graph, cycle), at its smallest `finding_id` |
| XR-F9 | Finding, Observations | A Finding with `producer.role == solver` cites (correctness or deciding) no Observation with `visibility = hidden` (X13). | Solver Finding citing a hidden-check Observation | Only deciding citations checked | 1 per citation |

### T — FindingTransition chains
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-T1 | Transitions of a Finding | All transitions of one `finding_id` carry the same `finding_hash` (resolution itself is B2). | Transition 2 bound to a different Finding content with the same id | Only the first transition compared | 1 per transition |
| XR-T2 | Transitions of a Finding | Sequences are exactly 1…n (no gaps; duplicates are B1). Owner of gaps. | Sequences 1, 3 | Monotonic, not contiguous | 1 per finding |
| XR-T3 | contiguous pair | `previous_transition_hash == content_id(transition n−1)`. | Points at a non-adjacent transition | Compared with `finding_hash` | 1 per transition |
| XR-T4 | contiguous pair, previous non-terminal | `from_status == previous.to_status`. | `confirmed` from `hypothesis` after a `hypothesis → check_proposed` | — (harness) | 1 per transition |
| XR-T5 | chain | No transition follows a terminal `to_status` (confirmed, refuted, dropped). Owner of this check. | Transition after `dropped` | Terminal set from the wrong constant | 1 per finding |

### E — EpisodeState chains
| ID | Input records | Pass condition | Negative mutation | Planted bug | Report |
|---|---|---|---|---|---|
| XR-E1 | States of (`task_id`, `episode_id`) | Sequences exactly 0…n; `previous_state_hash == content_id(state n−1)`. One chain per pair (a second sequence 0 is B1). | (a) Sequence gap; (b) predecessor hash of state n−2 | Chain starts at 1 | 1 per episode |
| XR-E2 | pair, previous non-terminal | (`prev.state`, `cur.state`) ∈ `ALLOWED_EPISODE_TRANSITIONS` (ADR-0006). | `PLAN → SUBMIT` | Lifecycle-only subset used | 1 per pair |
| XR-E3 | pair, previous non-terminal | (a) If `prev.state = WAITING`, `cur.state ∈ {prev.resume_state, ABORTED}`. (b) If `cur.state = WAITING`, `cur.resume_state == prev.state` (X9). | (a) WAITING(resume = DEV_CHECK) → TRIAGE; (b) IMPLEMENT → WAITING(resume = PLAN) | ABORTED out of WAITING rejected (false positive) | 1 per pair |
| XR-E4 | chain | Nothing follows COMPLETED or ABORTED. Owner of this check. | Snapshot after COMPLETED | — (harness) | 1 per episode |
| XR-E5 | chain | `policy_id`, `policy_hash`, `budget_hash` and `solver_config_hash` are constant. | `budget_hash` → a larger budget at sequence 3 | `solver_config_hash` omitted | 1 per (episode, field) |
| XR-E6 | State, Policy | `policy.task_id == state.task_id` for the resolved policy (resolution and `policy_id` are B2). | Policy of another task | Policy resolved by id | 1 per state |
| XR-E7 | consecutive pair | `spent` (each dimension) and `wall_clock_elapsed_ms` never decrease. | `tool_calls` 7 → 6 | Only the vector sum compared | 1 per (pair, dimension) |
| XR-E8 | State, Budget | Per dimension, `spent + reserved ≤ limits`, and `wall_clock_elapsed_ms ≤ wall_clock_limit_ms`, except the per-dimension ABORTED exemptions (X10). | (a) `sim_jobs` overspend at TRIAGE; (b) additive overspend at ABORTED(`wall_clock_exhausted`) | `<` vs `≤`; exemption applied to all dimensions | 1 per (state, dimension) |
| XR-E11 | ABORTED State, Budget | `budget_exhausted` ⇒ if any additive limit is > 0, at least one **positive-limit** dimension has `spent + reserved ≥ limit`; if all additive limits are 0, the reason is valid at zero usage because no additive budget exists. `wall_clock_exhausted` ⇒ `wall_clock_elapsed_ms ≥ wall_clock_limit_ms` (X10/N3). | (a) Mixed zero/positive budget where only a zero-limit dimension is at limit and every positive-limit dimension is under; (b) `wall_clock_exhausted` below the wall limit | Zero-limit disabled dimensions incorrectly count as exhaustion in a mixed budget | 1 per state |
| XR-E9 | State, Candidates | Every non-null `CandidateBinding` (active, best, pending) has `manifest.task_id == state.task_id` and, if `manifest.episode_id` is not `None`, `manifest.episode_id == state.episode_id`. Resolution is B2. A reconstructor/oracle-side seed candidate is valid; CandidateManifest's own F6 rule fixes solver vs reconstructor episodes. | (a) Solver candidate of another episode as `best_candidate`; (b) pending job bound to another task's candidate | Requires an episode on every candidate (false positive on a reconstructor seed) | 1 per binding |
| XR-E10 | chain | A `JobId` keeps the same (`request_hash`, `candidate`, `reserved`) in every snapshot that lists it; once absent from a later snapshot it never reappears in that chain. | (a) Same `JobId`, new `request_hash`; (b) job reappears after removal | Reappearance not checked | 1 per (episode, job) |

### Contract tests (not runtime codes; outside `InvariantCode` and the rule harness)
- **CT-1** (formerly XR-B3): every `ContentId`-typed field, including optional, nested and tuple-item fields, in every P1.1 schema is classified exactly once as H1, H2 or H3. A test-local subclass with an unclassified field fails. Planted: drop one map entry.
- **CT-2:** the one-set-head consequence (C section).
- **CT-3:** the dependency-ordering table above. A mutation set that breaks an owner yields only the owner's code.

## Deferred and known limitations (table D)
None of these is approximated in 009. "New record?" marks a rule impossible without a record type that does not exist; it is **surfaced, not invented**.

| # | Invariant (source) | Why not in 009 | Owner | New record? |
|---|---|---|---|---|
| D1 | A cited Observation is *stored*; chains are *complete*; a set head is the *global* head; no fork ever exists (006, 007) | Store-wide authority | P1.2 | no |
| D2 | (`task_id`, `episode_id`) globally unique; `JobId` never reused within an episode (007 ED15) | Global part needs the store; the set-local part is XR-B1/E1/E10 | P1.2 / P1.5 | no |
| D3 | `PendingJob.request_hash` resolves to the immutable job request; whether that request needs a candidate (007) | Event log; no job-request record | P1.2 / P1.4 / P1.5 | **yes** (job request) |
| D4 | `evaluator_bundle_hash` matches the task evaluator's bundle; expected inventories equal the bundle's; equivalence commits to `golden_hash` (005 R5) | No evaluator-bundle manifest | P1.4 / P1.6 | **yes** (evaluator-bundle manifest) |
| D5 | `tool_profile_hash` resolves to the profile `tool_profile_id`; image and adapter digests | No ToolProfile record | P1.4 | **yes** (tool profile) |
| D6 | Contract hashes resolve; configuration parameter names belong to the contract vocabulary (003, Q5, N1) | No Contract record | P1.6 / P3 | **yes** (contract) |
| D7 | `golden_hash`, `patch_hash`, file, log, evidence, supporting-artifact and checkpoint blobs exist and match bytes | Blob store | P1.2 | no |
| D8 | Non-null `dependency_hash` resolves to a dependency bundle (004 F4, §8.10) | Dependency-bundle definition | P1.5 | **yes** (dependency bundle) |
| D9 | `solver_config_hash` resolves (007 ED14) | Solver-config record | P1.5 / P5.1 | **yes** (solver config) |
| D10 | Probe promotion: a later policy version, with the decided Finding as a new `derived_from` Finding (006) | Promotion event/relation; 009 enforces only the prohibition (XR-F7) | P1.5 / P4 | event, not record |
| D11 | Accounting truth: `spent` equals recorded consumption; cancelled-reservation handling (007) | Event log, controller | P1.5 | no |
| D12 | Failure-signature progression (007 ED11) | `failure_signature_v1` is P1.5's | P1.5 | no |
| D13 | `component_hash` resolves to a registered component build | Component registry | P1.2 / P5 | no |
| D14 | Requalification: evidence against a superseded policy, requirement or contract is invalidated | Event-driven invalidation | P1.5 / P4 | no |
| D15 | `disposition = ambiguous` blocks qualification | Qualification workflow | P4 | no |
| D16 / L1 | Exact historical candidate → TaskManifest revision binding (X8, N2) | `CandidateManifest` has no manifest hash/version | schema change, coordinator | field, not record |
| D17 / L2 | Exact historical policy → TaskManifest revision binding (X11) | `EvaluationPolicy` has `task_id` + `contract_hash` only | schema change, coordinator | field, not record |
| D18 / L3 | Exact historical requirement semantics of a Finding | `Finding` carries a logical `requirement_id`, no Requirement content/version hash; invalidation of old Findings is D14 | schema change, coordinator / P1.5 / P4 | field, not record |
| D19 | Hidden-evidence leakage by Findings whose provenance cannot be classified as solver-side vs judge-side. `Finding.producer.role` ∈ {solver, critic, triage, reviewer}; critic/triage/reviewer do not by themselves say which side produced the Finding. (X13/N4) | Needs the P1.5 solver-safe projection/context provenance | P1.5 | no |

### Surfaced for coordinator review (not invented)
- **N1:** contract parameter vocabulary needs a Contract record (D6). XR-P8/XR-P5 are in-bundle consistency only.
- **N2:** `CandidateManifest` does not pin the task revision (L1). Neither does `EvaluationPolicy` (L2) or `Finding` → Requirement (L3). No fields are added in 009.
- **N3 — decided by coordinator in final PR #26 review.** Zero-valued additive dimensions are disabled and do not prove `budget_exhausted` when any additive dimension has a positive limit. In that mixed case, at least one positive-limit dimension must have `spent + reserved ≥ limit`. If **all** additive limits are zero, `budget_exhausted` is valid at zero usage because the episode has no additive budget available at all. XR-E11 tests both cases.
- **N4 — clarified by coordinator, no rule change.** `Finding.producer.role` is `solver | critic | triage | reviewer`; `architecture_explorer` is a CandidateManifest producer role and is unrelated to Finding provenance. D19 covers the ambiguity of critic/triage/reviewer; XR-F9 remains limited to `role == solver`.

## Test design
- **Coherent bundle builder** (`tests/contract/cross_record/_bundle.py`):
  - built from a typed spec;
  - `seal()` constructs records in dependency order, computing every H1 hash from the record it names;
  - mutations are spec edits before sealing, plus post-seal tamper helpers for B2.
- **Positive scenarios.** One FIFO family, all clean:
  - task revisions 1→2 (contract revision; stable X5 fields);
  - a mutation-derived sibling task in the same family and lineage;
  - requirements R03 (`all_supported_configs`) and R17 (`parameter_scope`, revised);
  - policy revisions 1→2: revision 1 is a non-head policy bound to revision 1's contract hash; both have a common vocabulary, an exception and a quality check;
  - candidates: first, child, oracle-side explorer, solver-side explorer, and a reconstructor seed; all with the same `dependency_hash`;
  - Observations PASS/FAIL/TIMEOUT across checks and configurations, including a hidden-check Observation cited only by a reviewer Finding;
  - Finding A: proposes an existing obligated check → confirmed;
  - Finding B: probe → dropped(`no_executable_check`);
  - Finding C: superseded by D (`derived_from` C);
  - Episode 1: PREPARE…COMPLETED from a reconstructor seed, including a WAITING excursion and exact-limit spending;
  - Episode 2: ABORTED(`budget_exhausted`) with a truthful, exempt additive overspend.
- **Exact assertions:** every negative test asserts `{v.code for v in check_records(...)} == {target}` **and** the documented cardinality, including multi-field mutations of one rule.
- **Rule-removal harness:** CI runs it as a test, and it is the exhaustive load-bearing proof. For every runtime `InvariantCode`, running with exactly that rule removed must:
  - make at least one of its isolated negative fixtures clean;
  - leave the positive bundle clean.
- **Properties (hypothesis):**
  - shuffled and duplicated input gives an identical result (order independence and idempotence);
  - a non-`Record` value or an unsupported `Record` subclass raises `TypeError`.
- **Manual planted bugs:** a representative subset, run with counts recorded and source restored byte-identically: P6 (i)–(iii), K3, C1, E1, E3, E8, E9, B2, F5, T2.

## Scope
- In scope: the runtime rules above as pure functions; CT-1…CT-3; the coherent bundle builder; positive, negative, property and planted-bug tests; docs.
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
  - existing schema modules (`task.py` … `episode.py`, `_base.py`) and `sindri.core`: **no schema, ID or encoding change**;
  - the §20 example files under `tests/contract/examples/`;
  - any store, event log, controller or judge code.

## Non-goals
- No new record type, field or schema change (L1–L3 and N1–N2 are surfaced only; N3/N4 are decided without schema changes).
- No store, persistence, event log, ingest boundary, query layer or global uniqueness (D1, D2).
- No controller transition logic, requalification or invalidation (D14), no judge verdicts, and no accounting truth (D11).
- No evaluator-bundle, tool-profile, contract, dependency-bundle, job-request or solver-config records (D3–D9).
- No automatic repair or normalisation of a bundle; the validator only reports.
- P1.1-G work: JSON Schema export, and the integration sweep.

## Interfaces touched
- Schemas: none changed. New public API: `check_records`, `Violation`, `InvariantCode` (X1/X2).
- Tool APIs, DB/migrations, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The coherent bundle (all positive scenarios) yields `()`.
- [ ] The result is independent of input order and of duplicate identical records (property test).

Negative:
- [ ] Every negative mutation yields exactly `{its code}` with the documented cardinality.
- [ ] An unresolved reference yields one XR-B2 per occurrence and no cascade. Dependency ordering is tested (CT-3).
- [ ] XR-P6 fails for each of: exception exclusion, an optional-only check, a quality-only check, an untargeted configuration, and `1` vs `true` applicability.
- [ ] A non-`Record` value and an unsupported `Record` subclass each raise `TypeError`.

Tests:
- [ ] The rule-removal harness covers every runtime `InvariantCode`; `InvariantCode` contains runtime codes only (no XR-B3/C2).
- [ ] CT-1: all `ContentId` fields are classified exactly once; an unclassified field fails.
- [ ] Manual planted bugs recorded with counts; source restored byte-identically.

Documentation:
- [ ] `components/schemas.yaml`: cross-record invariants, closed-bundle semantics (X4) and the public API.
- [ ] `docs/REPO_MAP.md` updated.
- [ ] Packet completion evidence and handoff written, with table D owners and L1–L3, N1–N4 decisions/limitations.

Boundaries:
- [ ] `cross_record.py` imports concrete schema modules, not `sindri.schemas`; no I/O, clock or input mutation.
- [ ] No existing schema module, `sindri.core` or example file changed; no store, controller or judge code.

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
uv run pytest -q tests/contract/cross_record
git diff --stat origin/main -- src/sindri/schemas/_base.py src/sindri/schemas/task.py src/sindri/schemas/requirement.py src/sindri/schemas/policy.py src/sindri/schemas/candidate.py src/sindri/schemas/observation.py src/sindri/schemas/finding.py src/sindri/schemas/episode.py src/sindri/core tests/contract/examples   # must be empty
grep -n "from sindri.schemas import\|import sindri.schemas$" src/sindri/schemas/cross_record.py   # must be empty
```

## Plan of record
- `src/sindri/schemas/cross_record.py`: `InvariantCode` (runtime codes only), `Violation`, `check_records`, and one private rule function per code, registered in a table, with resolution and dependency ordering as above.
- `src/sindri/schemas/__init__.py`: export the three public names.
- `tests/contract/cross_record/`, one module per group:
  - `_bundle.py`;
  - `test_bundle_integrity.py` (B, CT-3);
  - `test_revision_chains.py` (C, CT-2);
  - `test_policy_coverage.py` (P);
  - `test_candidate_bindings.py` (K);
  - `test_observation_bindings.py` (O);
  - `test_finding_bindings.py` (F, T);
  - `test_episode_chains.py` (E);
  - `test_rule_harness.py`;
  - `test_hash_inventory.py` (CT-1).
- `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-009.md`, and the task board.

## Status
`ready` (coordinator, 2026-10-05). PR #26 merged to `main` as `d48d6ad`; merged-main CI run `37265160756` passed. Coordinator decisions X1–X13, OQ1–OQ4, N3 and N4 are final. Implementation is authorized only after this governance readiness PR itself is merged to `main` (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
