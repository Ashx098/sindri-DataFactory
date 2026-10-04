# SIN-P1.1-006 — Finding

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`Finding` exists as a strict, immutable record of **one structured claim about one exact candidate**:
which requirement it concerns, what is claimed, the author's initial uncertainty, the initial
evidence, and who produced it. Its lifecycle (hypothesis → check_proposed → confirmed / refuted,
or dropped) lives in separate immutable `FindingTransition` records. The transition into
`check_proposed` carries the proposed check, and confirm/refute transitions cite the deciding
Observations. Agents coordinate through findings instead of chat (master F4), and a tool observation,
not an argument, decides (§18.6).

## Why / architecture references
- Master architecture:
  - §8 F4 Blackboard: requirement, artifact and evidence named; hypothesis → check-proposed → confirmed/refuted by a tool; only the controller changes status, and only from tool observations; prose-only findings with no executable check are dropped after one triage pass.
  - §8.7 Finding definition; §8.8 findings stay attached to the exact candidate inspected; §13.4 triage; §18.5–18.6; §20.6 example (starting point only).
- Phase/subphase: P1.1; order: 005 → **{006, 007}** → 008.
- ADRs/RFCs: ADR-0002, ADR-0004, **ADR-0005** (supporting evidence never substitutes for candidate-correctness Observations).

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-006`

## Dependencies
- Required completed tasks: SIN-P1.1-005 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.observation` (`ObservationAction`; import only), `sindri.schemas.policy`, `sindri.core.ids` (`FindingId`, `ObservationId`, `CandidateId`, `RequirementId`, `TaskId`, `CheckId`, `ConfigurationId`, `TestId`, `PropertyId`, `ContentId`)

## Coordinator decisions (PR #17, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| FD1 | **Accepted, with a placement correction.** `Finding` is immutable; lifecycle lives in separate immutable `FindingTransition` records. The initial status is implicitly `hypothesis`, and the current status is derived from the transition chain. No `status` field on Finding. |
| FD2 | **Graph accepted; `actor` dropped.** Allowed edges: `hypothesis → check_proposed`, `check_proposed → confirmed`, `check_proposed → refuted`, `{hypothesis, check_proposed} → dropped`. There is no `hypothesis → confirmed` shortcut; confirmed, refuted and dropped are terminal. The edge table is exported as data. **No `actor: controller` field**: a self-attested constant adds no authority (same reasoning as O13). Controller-only transition authority is the store/controller permission boundary (P1.2/P1.5). |
| FD3 | **Accepted.** Exact binding: `task_id` + `candidate_id` + `candidate_manifest_hash`. |
| FD4 | **Accepted.** Correctness citation `{observation_id, observation_hash}`; 009 verifies the pair. |
| FD5 | **Accepted.** Supporting artifacts may support a hypothesis but never substitute for Observation correctness evidence. No `DiagnosticResult` until its real consumer exists. |
| FD6 | **Accepted.** One Finding names exactly one `RequirementId`. |
| FD7 | **Ordinal uncertainty accepted; `rank` dropped.** `uncertainty: low \| medium \| high` is the author's *initial* uncertainty. Rank depends on a changing sibling set without a typed triage-batch identity, so it is not stable claim identity. Ranked ordering belongs to P1.5 triage state/output. |
| FD8 | **Decided: no EvaluationPolicy version per ad-hoc probe.** Two proposal forms: **`ExistingPolicyCheck`**, which may produce an Observation directly; and **`DevelopmentProbeRequest`**, which is *not* an executable correctness check. A probe's result is triage/supporting evidence under ADR-0005 and cannot by itself confirm or refute. If a probe must become correctness-bearing, the Verification Forge/controller explicitly promotes it into a declared development policy check through a new policy version and the requalification path. No lightweight policy section inside 006. |
| FD9 | **Terminal evidence accepted; `direction` dropped.** `to_status = confirmed` already means the deciding evidence supports the claim, and `refuted` that it contradicts it. A second field could contradict the transition. Confirm/refute need a non-empty Observation citation set; 009 verifies that those Observations are PASS/FAIL and bound to the exact candidate. Dropped keeps the typed reason / `superseded_by` rule. |
| FD10 | **Accepted.** A changed claim, requirement, candidate or uncertainty is a new Finding, optionally `derived_from`. The old Finding may be dropped as `superseded`. |
| FD11 | **Provenance at source accepted; shape amended.** Closed discriminated `producer` (no `Any`) with common `role`, `provenance_ref` and a never-defaulted `training_allowed`:<br>• `ModelProducer` additionally requires `model` + `model_version`;<br>• `ComponentProducer` requires `component` + `component_version` + `component_hash`;<br>• `HumanProducer` requires `reviewer_ref`. |
| FD12 | **Accepted.** 006 covers candidate-correctness Findings only. Forks, InterrogationAnswers, Resolutions and Requirement updates stay separate oracle-side record types. |
| ProposedCheck placement | **The proposed check belongs to the transition, not the Finding.** F4 lets a prose hypothesis exist for one triage pass and be dropped if no executable check can be proposed; with an immutable Finding, a check found later could not be added. Therefore:<br>• `Finding` holds the immutable claim and initial evidence, with **no** authoritative `proposed_check`;<br>• the `hypothesis → check_proposed` transition carries **exactly one** `ProposedCheck` (`ExistingPolicyCheck \| DevelopmentProbeRequest`);<br>• confirmed/refuted transitions cite the deciding Observations; when the earlier proposal was an `ExistingPolicyCheck`, 009 verifies that the deciding Observation matches it;<br>• promoting a probe to correctness policy is a later P1.5/P4 event, and the probe result stays supporting evidence. A new or superseding Finding may follow the promotion rather than the old claim being mutated. |

### Consequences the agent derived while applying the decisions (for final review)
- **A Finding confirmed after a probe.** If the transition into `check_proposed` carried a `DevelopmentProbeRequest`, the same Finding can only reach `confirmed`/`refuted` by citing an Observation of a *declared* check. In practice that means a policy check promoted later and executed. Otherwise the Finding is dropped or superseded. The schema allows `check_proposed → confirmed` with any Observation citation; *which* Observations are admissible after a probe is a 009/P1.5 rule (listed below).

## Scope
- In scope:
  - `src/sindri/schemas/finding.py`:
    - `FindingStatus`, `Uncertainty`, `ProducerRole` (`solver`, `critic`, `triage`, `reviewer`), `DropReason` (`no_executable_check`, `superseded`, `duplicate`, `candidate_invalidated`, `budget_exhausted`), and `ALLOWED_FINDING_TRANSITIONS` (data).
    - `ObservationCitation{observation_id, observation_hash}`.
    - `SupportingArtifact{kind: trace | waveform_window | log_excerpt | reproducer, hash, cycle_window: {start, end} | None}`, where the cycle window has integer bounds and start ≤ end.
    - `ModelProducer | ComponentProducer | HumanProducer`, discriminated on `kind` (FD11).
    - `ExistingPolicyCheck{policy_hash, check_id, configuration_id}` and `DevelopmentProbeRequest{action: ObservationAction, configuration_id, test_ids, property_ids, rationale}` (at least one of test/property IDs non-empty; never executable correctness evidence).
    - **`Finding`** (`Record`, immutable): `finding_id`, `task_id`, `candidate_id`, `candidate_manifest_hash`, `requirement_id`, `claim` (non-blank, ≤ 500 characters), `uncertainty`, `producer`, `correctness_citations`, `supporting_evidence`, `derived_from: FindingId | None`.
    - **`FindingTransition`** (`Record`, immutable): `finding_id`, `finding_hash`, `sequence ≥ 1`, `previous_transition_hash | None`, `from_status`, `to_status`, `proposed_check | None`, `deciding_citations`, `drop_reason | None`, `superseded_by: FindingId | None`.
  - In-record invariants:
    - **Finding:** at least one of `correctness_citations` / `supporting_evidence` is non-empty (F4: names its evidence); `derived_from ≠ finding_id`.
    - **FindingTransition:**
      - the edge is in the table;
      - `proposed_check` is present if and only if `to_status = check_proposed`;
      - confirmed/refuted need a non-empty `deciding_citations` and carry no `drop_reason`;
      - dropped needs `drop_reason`, with empty `deciding_citations`;
      - `superseded_by` is present if and only if the reason is `superseded`;
      - the chain head is sequence 1 with no previous hash; later sequences need one.
    - Floats rejected (inherited).
  - Tests under `tests/contract/`, with adapted §20.6 fixtures (a Finding; a `check_proposed` transition carrying `DevelopmentProbeRequest` for `stall_stability_004`; a `confirmed` transition citing an Observation).
- Allowed paths: `src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py` (exports only), `tests/contract/`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-006.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none; fixtures synthetic.
- `src/sindri/core/ids.py` is owned by SIN-P1.1-007 in this pair; 006 needs no new IDs. If it turns out to need one, stop and ask.
- Verified records: import only.

## Non-goals
- No blackboard store, controller transition logic, triage ranking or permission enforcement (P1.2/P1.5).
- No `DiagnosticResult` citations; no probe promotion or policy versioning (FD8: P1.5/P4).
- No oracle-side blackboard records (FD12).

## Cross-record invariants deferred to SIN-P1.1-009
- `candidate_manifest_hash` equals the manifest of `candidate_id`, whose `task_id` equals the Finding's; `requirement_id` exists on that task.
- Each `ObservationCitation` identifies one stored Observation by id + hash, bound to the Finding's exact `candidate_manifest_hash`.
- `deciding_citations` of confirm/refute reference Observations with status PASS or FAIL.
- If the `check_proposed` transition carried an `ExistingPolicyCheck`, the deciding Observation matches its `policy_hash`/`check_id`/`configuration_id`. If it carried a `DevelopmentProbeRequest`, deciding Observations must be of a *declared* (promoted) check, never the probe's own supporting result.
- `ExistingPolicyCheck` resolves in the policy with `policy_hash`, and the pair is not excluded.
- Transition chains:
  - `finding_hash` matches the Finding;
  - contiguous sequences;
  - `previous_transition_hash` links;
  - `from_status` equals the previous `to_status` (the first transition's `from_status` is `hypothesis`);
  - nothing follows a terminal status;
  - `superseded_by` and `derived_from` resolve.

## Interfaces touched
- Schemas: new `Finding` v1, `FindingTransition` v1. IDs: none new. Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [x] The adapted §20.6 Finding validates and round-trips. Each FD11 producer kind validates.
- [x] A Finding with only supporting evidence validates (an implicit hypothesis).
- [x] `hypothesis → check_proposed` validates with an `ExistingPolicyCheck` and with a `DevelopmentProbeRequest`.
- [x] `check_proposed → confirmed` and `→ refuted` validate with deciding Observation citations.
- [x] `hypothesis → dropped (no_executable_check)` and `check_proposed → dropped (superseded, superseded_by)` validate.

Negative:
- [x] Every field required (no defaults); unknown fields rejected at every level, including `status`, `proposed_check`, `rank` on Finding and `actor`, `direction` on FindingTransition.
- [x] A Finding with neither citations nor supporting evidence → rejected; `derived_from` equal to itself → rejected.
- [x] Edges outside the table (`hypothesis → confirmed`, `confirmed → refuted`, `refuted → check_proposed`, `dropped → hypothesis`) → rejected.
- [x] `check_proposed` without a `proposed_check`, or `proposed_check` on any other transition → rejected.
- [x] Confirmed/refuted with empty `deciding_citations` → rejected. There is no supporting-evidence field on transitions, so a probe or artifact cannot decide (ADR-0005, FD8).
- [x] Dropped without a reason, with deciding citations, or with `superseded_by` on a non-superseded reason → rejected.
- [x] A citation without `observation_hash` → rejected.
- [x] A model producer without `model`/`model_version`, a component producer without `component_hash`, a human producer without `reviewer_ref`, or `training_allowed` missing or non-bool → rejected.
- [x] A `DevelopmentProbeRequest` with neither tests nor properties → rejected; a cycle window with start > end → rejected.
- [x] Unknown uncertainty or float values; a blank or over-long claim → rejected.
- [x] Sequence 1 with a previous hash, or sequence > 1 without one → rejected.
- [x] Records are immutable.

Planted-bug checks (run, record in handoff, revert):
- [x] Allowing `hypothesis → confirmed` makes the suite fail.
- [x] Allowing confirm/refute with empty `deciding_citations` makes the suite fail.
- [x] Making `proposed_check` optional on `check_proposed` makes the suite fail.
- [x] Defaulting `training_allowed=True` on producers makes the suite fail.

General:
- [x] `ruff`, `mypy --strict`, full `pytest` green; boundary test covers `schemas`.
- [x] `components/schemas.yaml` and `docs/REPO_MAP.md` updated; handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_finding.py`, `tests/contract/examples/{finding,finding_transition_check_proposed,finding_transition_confirmed}.json`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-007
- Shared files: `src/sindri/schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These need a deliberate manual integration, never "accept both".
- `src/sindri/core/ids.py` is edited only by SIN-P1.1-007.

## Status
`review` (authoritative status: `implementation/task_board.yaml`). Decisions FD1–FD12 and the ProposedCheck placement implemented as written.

## Completion evidence
- Files changed: `src/sindri/schemas/finding.py` (new), `src/sindri/schemas/__init__.py` (exports), `tests/contract/test_finding.py` and `tests/contract/examples/{finding,finding_transition_check_proposed,finding_transition_confirmed}.json` (new), `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff. `core/ids.py` untouched (owned by 007).
- Tests run/results: `ruff` clean; `mypy --strict` clean (17 files); `pytest`: 690 passed, 8 skipped (88 Finding tests).
- Acceptance evidence:
  - The adapted §20.6 Finding (supporting trace, cycles 40–48), a `check_proposed` transition carrying a `DevelopmentProbeRequest` for `stall_stability_004`, and a `confirmed` transition validate and re-serialize to identical JSON.
  - Rejection reasons spot-checked: probe without targets, probe action outside `ObservationAction`, sequence 0, two requirements, model producer without a version.
  - Planted bugs, each caught and the source restored:
    - `hypothesis → confirmed` allowed → 2 failures;
    - confirm with empty citations → 2;
    - `proposed_check` optional on `check_proposed` → 1;
    - `training_allowed=True` default → 1.
- Implementation interpretations for coordinator review:
  1. **A first transition (sequence 1) must start from `hypothesis`.** This is checked in-record, because it needs only the one record; the packet listed it under 009.
  2. **Duplicate Observation citations** (by `observation_id`) are rejected in both `correctness_citations` and `deciding_citations`.
  3. **Deciding citations appear only on confirm/refute**, so `check_proposed` and `dropped` transitions must have none.
  4. **`DevelopmentProbeRequest.action` is `ObservationAction`**, as the packet specified, so a probe cannot request `inspect_waveform`. Waveform/coverage probes wait for the ADR-0005 diagnostic result type.
  5. `superseded_by` may not equal the Finding itself.
- Known limitations: cross-record rules (exact-candidate citation binding, PASS/FAIL deciding Observations, probe-then-confirm only via a declared check, chain linkage) are SIN-P1.1-009.
- Handoff/next action: `docs/handoffs/SIN-P1.1-006.md`.
