# SIN-P1.1-007 — EpisodeState

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`EpisodeState` exists as a strict, immutable **snapshot** of one solver episode's controller state:
where the episode is in its state machine (including WAITING and what it will resume), which exact
candidates are active and best, which asynchronous jobs are outstanding, how much of an immutable
budget has been spent and reserved, the last normalized failure signature, and a checkpoint
reference. It must be sufficient, together with the event log, CandidateManifests and pending job
IDs, to **recover after a crash without asking an LLM to reconstruct anything** (master §8.8).
Each transition writes a new snapshot; history is never overwritten.

## Why / architecture references
- Master architecture:
  - §8 F3 Controller: episode states, the budgets list, "never extend a budget mid-episode", "never let a model decide a task is done".
  - §8.8 Controller recovery: durable state recoverable from EpisodeState, event log, candidate manifests and pending job IDs; explicit WAITING with no tokens burned; retry distinguishes infrastructure from candidate failure.
  - §13.4–13.5 triage/repair: "Hash normalized failure signatures. If the same failure repeats across several repairs, switch hypothesis, roll back, escalate or stop"; preserve the best-known candidate.
  - §20.11 EpisodeState example (starting point only), §20.7 EpisodeRecord (a different, later record).
- Constitution §15: a **different** state list (see ED1).
- Coordinator decision D6 (SIN-P1.1-002): budgets are episode/experiment-scoped; "EpisodeState can record spent/remaining against a later immutable budget configuration".
- Phase/subphase: P1.1; order: 005 → **{006, 007}** → 008.
- ADRs/RFCs: ADR-0002, ADR-0005.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-007`

## Dependencies
- Required completed tasks: SIN-P1.1-005 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.observation` (`ObservationAction`; import only), `sindri.core.ids` (`EpisodeId`, `TaskId`, `CandidateId`, `PolicyId`, `ContentId`; plus new `JobId`)

## Open decisions (coordinator decides; the agent recommends)

| ID | Question | Agent recommendation |
|---|---|---|
| ED1 | **The state enum: the sources disagree.** Master F3: `PREPARE → PLAN → IMPLEMENT → DEV_CHECK → TRIAGE ⇄ REPAIR → SUBMIT → JUDGE → RECORD` (no WAITING). Master §8.8 adds WAITING. Constitution §15: `… SUBMIT → ACCEPTANCE → WAITING → REVIEW → RELEASE / STOP`. | Follow the **master** (it outranks the constitution for runtime semantics): `PREPARE, PLAN, IMPLEMENT, DEV_CHECK, TRIAGE, REPAIR, SUBMIT, JUDGE, RECORD`, plus **`WAITING`** (§8.8) and two terminal states: **`COMPLETED`** (after RECORD) and **`ABORTED`** (with a required `abort_reason`). The constitution's ACCEPTANCE/REVIEW/RELEASE are release-layer concepts (ReleaseManifest, §14.7), not solver-episode states. Because this resolves a conflict between two canonical documents, **record it as ADR-0006** if accepted. |
| ED2 | **WAITING resume.** | WAITING carries `resume_state` (the non-terminal state to return to; never WAITING itself) and requires ≥ 1 pending job. Every other state has `resume_state = None`. |
| ED3 | **Snapshots vs mutable rows.** | **Immutable snapshots**: `sequence ≥ 0`, contiguous; `previous_state_hash` = the previous snapshot's `content_id()` (None only for sequence 0). Every transition writes a new snapshot, and restart reads the newest *verified* chain head. A mutable row would let a crash mid-update overwrite the only copy of the state. |
| ED4 | **Candidate bindings.** | `CandidateBinding{candidate_id, candidate_manifest_hash}` for `active_candidate` and `best_candidate`, both nullable (PREPARE/PLAN have none). States from IMPLEMENT onwards require `active_candidate` (exception: ABORTED). `best_candidate` additionally records `best_reason` (a ContentId of its supporting Observation set, or `None` while no candidate has evidence), so "best" is evidence-backed, never asserted (§13.5, X4 rule). |
| ED5 | **Checkpoint and restart identity.** | `checkpoint_ref: ContentId` points to the durable trajectory-so-far blob (messages, tool calls, observation IDs), which the controller, not the model, writes. Together with the snapshot fields (ED12), the controller rebuilds model context from the checkpoint and resumes; no LLM reconstruction. |
| ED6 | **Budget configuration.** | A new immutable **`EpisodeBudget`** record (`Record`), the "later immutable budget configuration" of D6. It holds the limits per dimension (ED7). `EpisodeState` references it by `budget_hash` (its `content_id()`). Limits never appear inside snapshots, so they cannot drift between snapshots; "budget cannot increase mid-episode" becomes "`budget_hash` is constant across the chain" (009). |
| ED7 | **Exact integer units.** | One `BudgetVector` type with seven `StrictInt ≥ 0` fields: `tokens`, `tool_calls`, `candidate_versions`, `sim_jobs`, `formal_ms` (master F3 says "formal seconds"; milliseconds for consistency with `duration_ms`, D5), `repair_attempts`, `wall_clock_ms`. Used for limits, spent and reserved. |
| ED8 | **Spent / reserved / remaining.** | Store **`spent` and `reserved`** only; `remaining = limit − spent − reserved` is **derived** (a method that needs the `EpisodeBudget`). In-record: `spent` and `reserved` are non-negative. With the budget available, a validation helper checks `spent + reserved ≤ limit` per dimension (and remaining ≥ 0), but that is cross-record → 009. Storing `remaining` as well would add a third number that can disagree. *Alternative:* store all three and assert `spent + reserved + remaining == limit` in 009. |
| ED9 | **Pending jobs and `JobId`.** | **Introduce `JobId`** (`job_771`, from the master example; first consumer). `PendingJob{job_id, action: ObservationAction, candidate: CandidateBinding, reserved: BudgetVector}`. The reservation lets the snapshot account for in-flight cost, and `reserved` must equal the sum of pending-job reservations (in-record). |
| ED10 | **WAITING with several jobs.** | WAITING requires ≥ 1 pending job. Proposal for v1: **wait for all** pending jobs before resuming (deterministic and simple). An "any" policy (resume when the first job fails) is a P1.5 controller optimisation, not a schema field. Pending jobs may also exist in non-WAITING active states (dispatch then continue); terminal states require zero pending jobs. |
| ED11 | **`last_failure_signature`.** | `ContentId \| None`, computed over a canonical, normalized failure signature with domain tag `failure_signature_v1`. **The normalization itself belongs to triage (P1.5, §13.4)**; this record only stores the hash. Add `failure_repeat_count: StrictInt ≥ 0` (0 when the signature is None), so the stagnation rule ("same failure repeats → switch, roll back, escalate or stop") is visible without replaying history. |
| ED12 | **Schema vs controller validation.** | The **schema** validates one snapshot: state-specific field presence (ED2, ED4, ED10), the chain head (sequence 0 ⇔ no previous hash), non-negative vectors, `reserved == Σ pending reservations`, and the failure-repeat consistency. It also exports **`ALLOWED_EPISODE_TRANSITIONS` as data** (F3 edges + WAITING enter/resume + abort from any non-terminal state + RECORD → COMPLETED), so 009 and P1.5 share one table. **Cross-snapshot legality** (edge in table, monotonic `spent`, constant `budget_hash`, contiguous sequence) is 009/P1.5. |
| ED13 | **Crash/restart sufficiency** (coordinator item 12). | To recreate execution, the snapshot holds: `episode_id`, `task_id`, `policy_id`+`policy_hash` (the evaluation context), `budget_hash`, `solver_config_hash` (see ED14), `sequence` + `previous_state_hash`, `state` + `resume_state`, `active_candidate`/`best_candidate` bindings, `pending_jobs`, `spent`/`reserved`, `last_failure_signature` + `failure_repeat_count`, `checkpoint_ref`. With the event log (P1.2), the CandidateManifests and the pending job IDs (re-attach or re-dispatch), the controller can resume deterministically. A test asserts that every field the restart procedure reads is present and required. |
| ED14 | **Solver configuration** (derived; not in the coordinator's list). | The master compares solver modes A/B/C and model arms at matched budgets (§7.6, §17.4), so the episode must bind which solver configuration ran. Proposal: `solver_config_hash: ContentId`, a reference to an immutable solver configuration (model, version, sampling, mode). That record's schema is **deferred to P1.5/P5.1**; 007 only binds its hash. *Alternative:* embed the solver config in `EpisodeBudget`, rejected because it mixes "how much" with "who". |
| ED15 | **Episode identity** (derived). | `EpisodeId` (`e17`) is unique only within a task (as `R17` is for requirements, D3). An episode is identified by (`task_id`, `episode_id`), and 009 enforces uniqueness per task. |

## Scope (written for the recommended options; finalized after decisions)
- In scope:
  - `src/sindri/core/ids.py`, additive only: `JobId` (`job_771`).
  - `src/sindri/schemas/episode.py`:
    - `EpisodeStatus` enum (ED1) and `ALLOWED_EPISODE_TRANSITIONS` (data).
    - `AbortReason` enum: `budget_exhausted`, `infrastructure_failure`, `cancelled`, `stagnation`.
    - `BudgetVector`, `CandidateBinding`, `PendingJob`.
    - `EpisodeBudget` (`Record`): `budget_id` (content-addressed by its `content_id()`; no new ID type) and `limits: BudgetVector`, every dimension ≥ 1.
    - `EpisodeState` (`Record`, an immutable snapshot) with the ED13 fields, plus `abort_reason` (required iff ABORTED).
    - `failure_signature_hash(normalized: JSON-native) -> ContentId`, the `failure_signature_v1` construction, exposed for P1.5.
  - In-record invariants: listed in ED2, ED4, ED10, ED11 and ED12; floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.11 fixture (WAITING on two jobs, resume to DEV_CHECK).
- Allowed paths: `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive `JobId` only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-007.md`, `implementation/task_board.yaml` (status-only governance state), and `docs/adr/0006-*.md` **only if** the coordinator accepts ED1 as an ADR.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Verified records: import only. `core/status.py` unchanged.
- No controller, scheduler, job runner or store code (P1.2/P1.5).

## Non-goals
- No controller state machine execution, retry policy, job dispatch or event log (P1.5, P1.2).
- No failure normalization (triage, P1.5); only the hash construction and storage.
- No solver configuration schema (ED14: P1.5/P5.1). No `EpisodeRecord`/trajectory schema (§20.7; P5.5).
- No "wait for any" semantics (ED10).

## Cross-record invariants deferred to SIN-P1.1-009
- Snapshot chain:
  - `previous_state_hash` resolves to the previous snapshot of the same (`task_id`, `episode_id`);
  - `sequence` is contiguous;
  - the transition between consecutive snapshots is in `ALLOWED_EPISODE_TRANSITIONS`;
  - nothing follows COMPLETED/ABORTED.
- `budget_hash`, `policy_hash` and `solver_config_hash` are constant across the chain (the budget cannot increase mid-episode).
- `spent` is monotonically non-decreasing per dimension; `spent + reserved ≤ limits` per dimension against the `EpisodeBudget`.
- Candidate bindings resolve to CandidateManifests of the same task, whose producer role is `solver` with this `episode_id` (or `architecture_explorer` with this episode, per 004 F6).
- `best_reason` resolves to Observations of the best candidate.
- (`task_id`, `episode_id`) is unique across episodes; `JobId`s are unique within an episode.

## Interfaces touched
- Schemas: new `EpisodeState` v1, `EpisodeBudget` v1. IDs: additive `JobId`.
- Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The adapted §20.11 example validates and round-trips: WAITING on two jobs, resume to DEV_CHECK, active and best candidates bound by manifest hash, spent/reserved vectors.
- [ ] A sequence-0 PREPARE snapshot with no candidates validates; COMPLETED and ABORTED (with a reason) validate with zero pending jobs.
- [ ] `remaining()` computed against an `EpisodeBudget` equals limit − spent − reserved per dimension.
- [ ] `failure_signature_hash` matches an independent byte-level `hashlib` vector.

Negative:
- [ ] Every field required (no defaults); unknown fields rejected, including `budget_remaining` and `limits` on `EpisodeState` (ED6/ED8).
- [ ] WAITING without pending jobs, without `resume_state`, or with `resume_state = WAITING`/terminal → rejected; non-WAITING with `resume_state` → rejected.
- [ ] Terminal states with pending jobs → rejected; ABORTED without `abort_reason`, or a reason on a non-ABORTED state → rejected.
- [ ] IMPLEMENT-or-later (non-aborted) without `active_candidate` → rejected; a candidate binding without a manifest hash → rejected.
- [ ] `reserved` ≠ Σ pending-job reservations → rejected; any negative or float budget value → rejected.
- [ ] Sequence 0 with a previous hash, or sequence > 0 without one → rejected.
- [ ] `failure_repeat_count > 0` with no signature, or a signature with `failure_repeat_count = 0` → rejected (decide the exact rule in implementation per ED11: first occurrence counts as 1).
- [ ] `EpisodeBudget` with a zero or negative limit → rejected.
- [ ] Records are immutable.

Planted-bug checks (run, record in handoff, revert):
- [ ] Allowing WAITING with zero pending jobs makes the suite fail.
- [ ] Skipping the `reserved == Σ reservations` check makes the suite fail.
- [ ] Adding a mutable `limits` field to `EpisodeState` (budget drift) makes the suite fail.
- [ ] Dropping the domain tag from `failure_signature_hash` makes the suite fail.

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
`src/sindri/core/ids.py` (additive `JobId`), `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_episode_state.py`, `tests/contract/examples/{episode_state,episode_budget}.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-006
- Shared files: `src/sindri/schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These need a deliberate manual integration, never "accept both".
- This task alone edits `src/sindri/core/ids.py`.

## Status
`planned`. Draft for coordinator review; decisions ED1–ED15 open, including the ED1 source conflict (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
