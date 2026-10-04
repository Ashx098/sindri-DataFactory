# SIN-P1.1-006 — Finding

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`Finding` exists as a strict, immutable record of **one structured claim about one exact candidate**:
which requirement it concerns, what is claimed, how uncertain it is, what supports it, and which
executable check would decide it. Its lifecycle (hypothesis → check proposed → confirmed / refuted /
dropped) is recorded so that only the controller moves it, and only on admissible evidence. Agents
then coordinate through findings instead of chat (blackboard, master F4), and nobody "wins an
argument": a tool observation decides (§18.6).

## Why / architecture references
- Master architecture:
  - §8 F4 Blackboard: every finding names requirement, artifact and evidence; status hypothesis → check-proposed → confirmed/refuted *by a tool*; only the controller changes status, only from tool observations; prose-only findings with no executable check are dropped after one triage pass.
  - §8.7: "Finding: Requirement + candidate + observation references, hypothesis, uncertainty and proposed discriminating check".
  - §8.8: "Findings remain attached to the exact candidate that was inspected".
  - §13.4 triage: ranked hypotheses with uncertainty, a proposed discriminating check.
  - §18.5–18.6: finding example and "what a good disagreement looks like"; §20.6 example (starting point only).
- Phase/subphase: P1.1; order: 005 → **{006, 007}** → 008.
- ADRs/RFCs: ADR-0002, ADR-0004, **ADR-0005** (diagnostic and qualification results never substitute for candidate-correctness Observations).

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-006`

## Dependencies
- Required completed tasks: SIN-P1.1-005 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.observation` (`ObservationAction`; import only), `sindri.schemas.policy`, `sindri.core.ids` (`FindingId`, `ObservationId`, `CandidateId`, `RequirementId`, `TaskId`, `CheckId`, `ConfigurationId`, `TestId`, `PropertyId`, `ContentId`)

## Open decisions (coordinator decides; the agent recommends)

| ID | Question | Agent recommendation |
|---|---|---|
| FD1 | **Identity vs lifecycle.** §20.6 puts `status` inside the Finding, yet records are immutable, and status changes over time. | Apply the **D1 precedent** (lifecycle state is not part of the identity record). `Finding` is immutable and holds the claim. Status changes are separate immutable **`FindingTransition`** records, issued by the controller, each citing the evidence that justified it. Current status is derived from the transition chain. *Alternative:* a versioned Finding with `supersedes`, where every transition is a new version. Rejected as the recommendation because it re-copies the claim on every status change and blurs who changed what. |
| FD2 | **Transition graph and authority.** | Allowed edges: `hypothesis → check_proposed`, `check_proposed → confirmed`, `check_proposed → refuted`, and `{hypothesis, check_proposed} → dropped`. Confirmed, refuted and dropped are terminal. There is no `hypothesis → confirmed` shortcut: an executable check must be on record first. Every `FindingTransition` carries `actor: controller` as a typed constant. Real write authority is the evidence store's permission model (P1.2/P1.5), exactly as O13 decided for Observation; the field documents intent and does not authenticate. The schema provides the edge table as data; enforcing a chain needs ≥ 2 records → 009/P1.5. |
| FD3 | **Exact artifact binding** (§8.8). | `task_id` + `candidate_id` + `candidate_manifest_hash`, as in Observation O2. A loose `CandidateId` is never enough. |
| FD4 | **Correctness citations.** | `ObservationCitation{observation_id, observation_hash}` (`observation_hash` = the Observation's `content_id()`); both are required. Agreement with the stored Observation is checked in 009. |
| FD5 | **ADR-0005: diagnostic and qualification results.** | Two evidence classes: (a) **correctness citations**, which are Observations only; (b) **supporting evidence**, meaning content-addressed artifacts (`SupportingArtifact{kind: trace \| waveform_window \| log_excerpt \| reproducer, hash, cycle_window?}`). The `DiagnosticResult` type does not exist yet (ADR-0005), so citations of it are added when it does. **Confirm/refute transitions require ≥ 1 correctness citation; supporting evidence alone can never confirm or refute.** |
| FD6 | **Requirement cardinality.** §20.6 shows one `requirement`. | **Exactly one `requirement_id`**, which matches F4 ("names the requirement") and keeps the discriminating check focused. A claim touching several requirements is split into several findings. *Alternative:* a non-empty tuple, rejected because confirm/refute would become ambiguous per requirement. |
| FD7 | **Uncertainty without floats** (D5). | A coarse ordinal `Uncertainty: low \| medium \| high` plus an integer `rank ≥ 1` among the hypotheses that triage emits for the same failure (§13.4 "ranked hypotheses"). No probabilities: model confidences are uncalibrated, and a scaled integer would imply false precision. *Alternative:* `confidence_permille: 0..1000`. |
| FD8 | **`proposed_check`.** §20.6 proposes `{tool: run_sim, test: stall_stability_004}`, a *test*, not a policy `CheckId`. But Observation (005) binds a declared policy check, so only a declared check can produce correctness evidence. | A discriminated union: (a) **`ExistingPolicyCheck{policy_hash, check_id, configuration_id}`**, which can confirm/refute once executed; (b) **`NewDevelopmentCheck{action, configuration_id, test_ids \| property_ids, rationale}`**, a request that the controller/Verification Forge must turn into a development-visibility check in a **new policy version** before it can be executed as an Observation. This makes the tension explicit: a newly proposed test cannot confirm anything until it is declared. **Open question for the coordinator:** is a policy-version bump per new discriminating test acceptable in P1, or should P1.5 introduce a lighter "development probe" policy section? Either way, this record only records the request. |
| FD9 | **Evidence required per terminal transition.** | **confirmed / refuted:** ≥ 1 `ObservationCitation` whose Observation has a verdict-bearing status (PASS or FAIL); non-verdict statuses cannot decide (checked in 009 against the Observation), and the transition states `direction: supports \| contradicts`. **dropped:** a `DropReason` enum (`no_executable_check` (F4's one-triage-pass rule), `superseded`, `duplicate`, `candidate_invalidated`, `budget_exhausted`), plus `superseded_by: FindingId` when superseded. No observation required. |
| FD10 | **Claim immutability.** | The claim text, requirement, candidate binding and uncertainty never change. A changed claim is a **new Finding** with optional `derived_from: FindingId`, and the old one is dropped with `superseded`. |
| FD11 | **Authorship and provenance** (derived; not in the coordinator's list). | Findings are agent output and may become training data (debug and diagnosis streams). Proposal: `author{role, model, model_version, provenance_ref, training_allowed}`, reusing the 004 F7 provenance rule ("recorded at the source"). Roles: `solver`, `critic`, `triage`, `reviewer`. |
| FD12 | **Scope** (derived). | 006 covers **candidate-correctness findings** only (solver-side triage, critics). Oracle-side blackboard records listed in F4 (Forks, Interrogation answers, Resolutions, Requirement updates) are separate records for P3/P4 and are not Findings. |

## Scope (written for the recommended options; finalized after decisions)
- In scope:
  - `src/sindri/schemas/finding.py`:
    - **`Finding`** (`Record`, immutable). Binding: `finding_id`, `task_id`, `candidate_id`, `candidate_manifest_hash`, `requirement_id`. Claim: `claim` (non-blank, ≤ 500 characters), `uncertainty`, `rank`, `author`. Evidence: `correctness_citations` (Observations), `supporting_evidence`, `proposed_check`. Lineage: `derived_from`.
    - **`FindingTransition`** (`Record`, immutable). `finding_id`, `finding_hash` (the Finding's `content_id()`), `sequence ≥ 1`, `previous_transition_hash | None`, `from_status`, `to_status`, `actor: controller`, `correctness_citations`, `direction`, `drop_reason`, `superseded_by`.
    - `FindingStatus` and the `ALLOWED_FINDING_TRANSITIONS` table (FD2) as data.
  - In-record invariants:
    - **Finding:** at least one of `correctness_citations` / `supporting_evidence` is non-empty, since F4 requires every finding to name its evidence; `proposed_check` is required for a Finding to ever reach `check_proposed` (enforced on the transition, below).
    - **FindingTransition:**
      - the edge is in the table;
      - confirmed/refuted need ≥ 1 correctness citation and a `direction`, and carry no `drop_reason`;
      - dropped needs a `drop_reason` and carries no citations or `direction`;
      - `superseded_by` is present iff the reason is `superseded`;
      - the sequence/previous-hash chain starts with sequence 1 and `None`.
    - Floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.6 fixture.
- Allowed paths: `src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py` (exports only), `tests/contract/`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-006.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none; fixtures synthetic.
- **`src/sindri/core/ids.py` is owned by SIN-P1.1-007 in this pair** (it adds `JobId`). 006 needs no new ID types; if implementation finds one is needed, stop and ask the coordinator.
- Verified records (`_base`, `task`, `requirement`, `policy`, `candidate`, `observation`): import only.

## Non-goals
- No blackboard store, no controller transition logic, no triage, no permission enforcement (P1.2/P1.5).
- No `DiagnosticResult` citations (the type does not exist; ADR-0005).
- No policy-versioning mechanism for new development checks (FD8 open question; P1.5/P4).
- No oracle-side blackboard records (FD12).

## Cross-record invariants deferred to SIN-P1.1-009
- `candidate_manifest_hash` equals the manifest of `candidate_id`, and that manifest's `task_id` equals the Finding's `task_id`; `requirement_id` exists on that task.
- Each `ObservationCitation`'s `observation_id` and `observation_hash` identify one stored Observation, and that Observation's `candidate_manifest_hash` equals the Finding's (findings stay attached to the exact candidate inspected).
- Confirm/refute citations reference Observations with status PASS or FAIL.
- `ExistingPolicyCheck` resolves (`check_id` and configuration in the policy with `policy_hash`; the pair is not excluded).
- Transition chains: `finding_hash` matches the Finding; sequences are contiguous; `previous_transition_hash` links; `from_status` equals the previous `to_status`; nothing follows a terminal status; `superseded_by` and `derived_from` resolve.
- `check_proposed` is reachable only for Findings that carry a `proposed_check`.

## Interfaces touched
- Schemas: new `Finding` v1 and `FindingTransition` v1. IDs: none new. Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The adapted §20.6 example (claim, one requirement, Observation citation, `NewDevelopmentCheck` for `stall_stability_004`) validates and round-trips.
- [ ] A Finding with only supporting evidence (no correctness citation) validates as a hypothesis.
- [ ] Each allowed transition validates with its required evidence; a dropped transition with `superseded_by` validates.

Negative:
- [ ] Every field required (no defaults); unknown fields rejected at every level, including `status` on `Finding` (FD1).
- [ ] A Finding with neither correctness citations nor supporting evidence → rejected.
- [ ] Any edge outside the table (e.g. `hypothesis → confirmed`, `confirmed → refuted`, `refuted → check_proposed`) → rejected.
- [ ] Confirmed/refuted with no Observation citation, or with only supporting evidence → rejected (ADR-0005).
- [ ] Dropped without a reason, with citations, or with `superseded_by` on a non-superseded reason → rejected.
- [ ] An Observation citation missing `observation_hash` → rejected.
- [ ] Uncertainty as a float or an unknown level; `rank < 1` → rejected.
- [ ] Claim blank or over 500 characters; `actor` other than `controller` → rejected.
- [ ] Sequence 1 with a previous hash, or sequence > 1 without one → rejected.
- [ ] Records are immutable.

Planted-bug checks (run, record in handoff, revert):
- [ ] Allowing `hypothesis → confirmed` makes the suite fail.
- [ ] Allowing confirm with supporting evidence only makes the suite fail.
- [ ] Dropping `observation_hash` from citations makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; boundary test covers `schemas`.
- [ ] `components/schemas.yaml` and `docs/REPO_MAP.md` updated; handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/schemas/finding.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_finding.py`, `tests/contract/examples/{finding,finding_transition}.json`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-007
- Shared files: `src/sindri/schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These need a deliberate manual integration, never "accept both" (lesson from 003/004).
- `src/sindri/core/ids.py` is edited only by SIN-P1.1-007.

## Status
`planned`. Draft for coordinator review; decisions FD1–FD12 open, including the FD8 open question (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
