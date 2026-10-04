# SIN-P1.1-007 — EpisodeState

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`EpisodeState` exists as a strict, immutable, hash-chained **snapshot** of one solver episode's
controller state:
- where the episode is in the ADR-0006 lifecycle (including WAITING and what it resumes);
- which exact candidates are active and best;
- which asynchronous jobs, bound to exact requests, are outstanding;
- how much of an immutable `EpisodeBudget` has been spent and reserved, plus elapsed wall-clock;
- the last failure signature;
- an optional checkpoint.

Together with the event log, CandidateManifests and pending job IDs and request hashes, it is
sufficient to **recover after a crash without asking an LLM to reconstruct anything** (master §8.8).
Each transition writes a new snapshot; history is never overwritten.

## Why / architecture references
- Master architecture:
  - §8 F3 controller: states, budgets, "never extend a budget mid-episode";
  - §8.8 recovery and WAITING;
  - §13.4–13.5: normalized failure signatures and stagnation; preserving the best-known candidate;
  - §20.11 example (starting point only).
- **ADR-0006**: the episode lifecycle and transition table (reconciles master F3/§8.8 with constitution §15).
- Coordinator decision D6 (SIN-P1.1-002): budgets are episode-scoped and immutable.
- Phase/subphase: P1.1; order: 005 → **{006, 007}** → 008.

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged **and** marked ready on `main`
- Worktree: `../worktrees/SIN-P1.1-007`

## Dependencies
- Required completed tasks: SIN-P1.1-005 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.core.ids` (`EpisodeId`, `TaskId`, `CandidateId`, `PolicyId`, `ContentId`; plus new `JobId`)

## Coordinator decisions (PR #17, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| ED1 | **Accepted; ADR-0006 recorded.** States: `PREPARE, PLAN, IMPLEMENT, DEV_CHECK, TRIAGE, REPAIR, SUBMIT, JUDGE, RECORD, WAITING, COMPLETED, ABORTED`. COMPLETED follows RECORD; ABORTED is terminal with a reason. Constitution ACCEPTANCE/REVIEW/RELEASE are release-workflow concepts. Transitions follow the ADR-0006 table; missing edges are added only through an explicit controller/ADR review. |
| ED2 | **Accepted.** WAITING requires `resume_state` (never WAITING or terminal) and ≥ 1 pending job; other states carry no `resume_state`. |
| ED3 | **Accepted.** Immutable hash-chained snapshots: sequence 0 has no predecessor; later snapshots name the exact previous content hash. |
| ED4 | **Bindings accepted; state rules amended; `best_reason` dropped.**<br>• `active_candidate` is optional in PREPARE, PLAN and IMPLEMENT, since the first IMPLEMENT snapshot can precede the candidate's creation.<br>• It is required in DEV_CHECK, TRIAGE, REPAIR, SUBMIT, JUDGE, RECORD and COMPLETED, and in WAITING whenever its `resume_state` requires one.<br>• ABORTED may have one or not.<br>• `best_candidate` is optional; there is no opaque `best_reason`, because the event log records why "best" changed. |
| ED5 | **Accepted, clarified.** `checkpoint_ref` is a required key with value `ContentId \| None`; `None` means no durable model/context checkpoint exists yet. The event log is the authority; the checkpoint is a restart optimisation, not a second history database. |
| ED6 | **EpisodeBudget accepted; `budget_id` removed.** The budget's own `content_id()` is its identity; EpisodeState stores `budget_hash`. No self-referential ID field. |
| ED7 | **Accounting amended.** Wall-clock is not additive under concurrency, so it is not in the reservable vector.<br>• Additive `BudgetVector`: `tokens`, `tool_calls`, `candidate_versions`, `sim_jobs`, `formal_ms`, `repair_attempts`.<br>• `EpisodeBudget` holds `limits: BudgetVector` and `wall_clock_limit_ms`; `EpisodeState` holds `wall_clock_elapsed_ms`.<br>• All values are strict integers. **Additive limits may be zero** (zero disables a resource, e.g. `tokens=0` for a deterministic episode); **`wall_clock_limit_ms` must be > 0.** |
| ED8 | **Derived remaining accepted.** Additive remaining = `limit − spent − reserved`; wall-clock remaining = `wall_clock_limit_ms − wall_clock_elapsed_ms`. Neither is stored. |
| ED9 | **`JobId` and reservations accepted; `PendingJob.request_hash` added.** Recovery must bind a pending `JobId` to the exact immutable request it represents. Reservations use the additive `BudgetVector` only, and snapshot `reserved` equals the sum of pending-job reservations. |
| ED10 | **Accepted.** WAITING has ≥ 1 pending job; terminal states have 0. "Wait for all" is the initial P1.5 controller policy, not a schema field. |
| ED11 | **Storage accepted; hash function deferred.** `last_failure_signature: ContentId \| None` and `failure_repeat_count`: `None` ⇔ count 0; present ⇒ count ≥ 1. **No `failure_signature_hash` in 007.** P1.5 owns the normalization, the exact `failure_signature_v1` input schema and its domain-separated constructor (a generic JSON hash would reopen float/`Any`/normalization ambiguity). |
| ED12 | **Accepted.** The schema validates single snapshots and exports one transition table; cross-snapshot legality is 009/P1.5. |
| ED13 | **Accepted, adjusted.** Restart fields include `request_hash`, separate wall-clock elapsed and a nullable checkpoint, with no `best_reason`. Recovery uses EpisodeState + event log + CandidateManifests + pending JobIds/request hashes, never model memory. |
| ED14 | **Accepted.** Required `solver_config_hash: ContentId`; the solver-config record is first defined by P1.5/P5.1, kept separate from the budget. |
| ED15 | **Accepted.** Episode identity is (`task_id`, `episode_id`); 009 enforces uniqueness. |

### Consequences the agent derived while applying the decisions (for final review)
- **"Active" states** for entering WAITING are the non-terminal, non-WAITING states. `resume_state` must be one of them, so it can never be WAITING, COMPLETED or ABORTED.
- **WAITING's candidate requirement follows `resume_state`.** WAITING requires `active_candidate` if and only if its `resume_state` is in the candidate-required set (DEV_CHECK … RECORD); for PREPARE, PLAN or IMPLEMENT it is optional.
- **Aborting with jobs outstanding.** ABORTED is terminal and requires zero pending jobs, so the controller must cancel or censor outstanding jobs before writing the ABORTED snapshot. Whether a cancelled job's reservation becomes spent or is released is P1.5 accounting; the schema only requires `reserved == Σ pending reservations`, which is zero when ABORTED.

### Final coordinator corrections omitted before the invalid readiness transition
PR #17 coordinator comment `5981249383` was posted before readiness and was not applied by commit `1f50e904`. These rules are authoritative for implementation/review:
- **PendingJob candidate is required-but-nullable.** `candidate: CandidateBinding | None`; this permits candidate-less WAITING/PLAN/IMPLEMENT/model/diagnostic jobs while keeping the key explicit.
- **PendingJob carries no ObservationAction.** EpisodeState is generic controller state; `request_hash` is the exact immutable request identity. P1.5/P1.4 later resolves the typed operation and whether a candidate is required.
- **Budget helper binding.** `EpisodeBudget.remaining(state)` must reject a state whose `budget_hash != budget.content_id()` before calculating.
## Scope
- In scope:
  - `src/sindri/core/ids.py`, additive only: `JobId` (`job_771`).
  - `src/sindri/schemas/episode.py`:
    - `EpisodeStatus` and `ALLOWED_EPISODE_TRANSITIONS` (the ADR-0006 table as data, with WAITING enter/resume expressed generically).
    - `AbortReason`: `budget_exhausted`, `wall_clock_exhausted`, `infrastructure_failure`, `stagnation`, `cancelled`.
    - `BudgetVector` (6 additive fields, each `StrictInt ≥ 0`), `CandidateBinding{candidate_id, candidate_manifest_hash}`, `PendingJob{job_id, request_hash, candidate: CandidateBinding | None, reserved: BudgetVector}`. The `candidate` key is required even when null; there is no duplicated ObservationAction field.
    - `EpisodeBudget` (`Record`): `limits: BudgetVector` (zeros allowed) and `wall_clock_limit_ms ≥ 1`. No `budget_id`. A `remaining(state)` helper computes both remainders (ED8).
    - **`EpisodeState`** (`Record`, an immutable snapshot) with these fields:
      - identity: `episode_id`, `task_id`, `sequence ≥ 0`, `previous_state_hash`;
      - bindings: `policy_id` + `policy_hash`, `budget_hash`, `solver_config_hash`;
      - lifecycle: `state`, `resume_state`, `abort_reason`;
      - candidates: `active_candidate`, `best_candidate`;
      - jobs: `pending_jobs`;
      - accounting: `spent`, `reserved`, `wall_clock_elapsed_ms`;
      - failure memory: `last_failure_signature`, `failure_repeat_count`;
      - restart: `checkpoint_ref`.
  - In-record invariants:
    - WAITING / `resume_state` rules (ED2 and the derived rule above);
    - `abort_reason` present if and only if ABORTED;
    - terminal ⇒ no pending jobs;
    - the active-candidate state rules (ED4);
    - `reserved` == Σ pending reservations, and job IDs unique within the snapshot;
    - the failure-signature/count rule (ED11);
    - the chain head (sequence 0 ⇔ no previous hash);
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with adapted §20.11 fixtures: an `EpisodeBudget`, and an EpisodeState that is WAITING on two jobs, resuming to DEV_CHECK.
- Allowed paths: `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive `JobId` only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-007.md`, `implementation/task_board.yaml` (status-only governance state). ADR-0006 is recorded by this planning change, not by the implementation.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Verified records: import only. `core/status.py` unchanged.
- No controller, scheduler, job runner or store code (P1.2/P1.5).

## Non-goals
- No controller execution, retry or cancellation policy, job dispatch or event log (P1.5, P1.2).
- No failure normalization and **no failure-signature hash function** (ED11: P1.5).
- No solver-config schema (ED14: P1.5/P5.1); no `EpisodeRecord`/trajectory schema (§20.7: P5.5); no typed best-decision record (ED4).
- No "wait for any" semantics (ED10).

## Cross-record invariants deferred to SIN-P1.1-009
- Snapshot chain:
  - `previous_state_hash` resolves to the previous snapshot of the same (`task_id`, `episode_id`);
  - `sequence` is contiguous;
  - consecutive states form an edge of the ADR-0006 table, and WAITING returns only to its recorded `resume_state`;
  - nothing follows COMPLETED or ABORTED.
- `budget_hash`, `policy_hash` and `solver_config_hash` are constant across the chain (the budget cannot increase mid-episode).
- Accounting over the chain:
  - `spent` and `wall_clock_elapsed_ms` never decrease;
  - against the `EpisodeBudget`, `spent + reserved ≤ limits` per dimension and `wall_clock_elapsed_ms ≤ wall_clock_limit_ms`, except at an ABORTED snapshot whose reason is `budget_exhausted` or `wall_clock_exhausted`.
- Candidate bindings resolve to CandidateManifests of the same task, produced by `solver` with this `episode_id` or by a solver-side `architecture_explorer` with it (004 F6).
- `request_hash` resolves to the immutable job request recorded in the event log (P1.2); P1.5/P1.4 verifies whether that request requires a candidate and, if so, that the nullable binding is correct. `JobId`s are unique within an episode.
- (`task_id`, `episode_id`) is unique.

## Interfaces touched
- Schemas: new `EpisodeState` v1, `EpisodeBudget` v1. IDs: additive `JobId`.
- Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The adapted §20.11 example validates and round-trips: WAITING on two jobs with request hashes, resuming to DEV_CHECK, active and best candidates bound by manifest hash, spent/reserved vectors, elapsed wall-clock.
- [ ] WAITING resuming to PLAN with `active_candidate = None` and a pending job whose required `candidate` key is `None` validates.
- [ ] Sequence-0 PREPARE with no candidates validates.
- [ ] The first IMPLEMENT snapshot without an `active_candidate` validates.
- [ ] WAITING resuming to PLAN without a candidate validates.
- [ ] COMPLETED, and ABORTED (with and without a candidate, with a reason), validate with zero pending jobs.
- [ ] `EpisodeBudget` with zero additive limits (e.g. `tokens=0`, `formal_ms=0`) validates.
- [ ] `remaining()` equals limit − spent − reserved per additive dimension, and wall-clock limit − elapsed.
- [ ] `checkpoint_ref = None` validates.

Negative:
- [ ] Every field required (no defaults); unknown fields rejected, including `budget_id`, `best_reason`, `budget_remaining`, `limits`, and `wall_clock_ms` inside `BudgetVector` (ED7).
- [ ] WAITING with no pending jobs, with no `resume_state`, or with `resume_state` WAITING/COMPLETED/ABORTED → rejected; a non-WAITING state with `resume_state` → rejected.
- [ ] DEV_CHECK…COMPLETED without `active_candidate` → rejected; WAITING resuming to DEV_CHECK without one → rejected.
- [ ] Terminal states with pending jobs → rejected; ABORTED without `abort_reason`, or a reason on non-ABORTED → rejected.
- [ ] A `PendingJob` without `request_hash` or without the required `candidate` key → rejected; `candidate: None` is valid; a non-null candidate binding without a manifest hash → rejected; duplicate job IDs → rejected; an `action` field is rejected.
- [ ] `reserved` ≠ Σ pending reservations → rejected; negative or float values → rejected.
- [ ] `EpisodeBudget` with `wall_clock_limit_ms = 0` → rejected.
- [ ] A failure signature with count 0, or a count ≥ 1 without a signature → rejected.
- [ ] Sequence 0 with a previous hash, or sequence > 0 without one → rejected.
- [ ] Records are immutable.

Planted-bug checks (run, record in handoff, revert):
- [ ] Allowing WAITING with zero pending jobs makes the suite fail.
- [ ] Skipping the `reserved == Σ reservations` check makes the suite fail.
- [ ] Making `PendingJob.request_hash` optional makes the suite fail.
- [ ] Requiring a non-null PendingJob candidate, or reintroducing an ObservationAction field, makes the suite fail.
- [ ] Requiring `active_candidate` in IMPLEMENT makes the suite fail (the first-IMPLEMENT positive test).
- [ ] Rejecting zero additive limits makes the suite fail.

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
`src/sindri/core/ids.py` (additive `JobId`), `src/sindri/schemas/episode.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_episode_state.py`, `tests/contract/examples/{episode_state,episode_budget}.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-006
- Shared files: `src/sindri/schemas/__init__.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These need a deliberate manual integration, never "accept both".
- This task alone edits `src/sindri/core/ids.py`.

## Status
`blocked` (coordinator correction, 2026-10-05). PR #17 commit `1f50e904` recorded readiness even though final coordinator comment `5981249383` explicitly required additional fixes before merge/READY. Existing implementation work is accepted for review only; PR #19 must implement the final corrections above before merge (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed: `src/sindri/core/ids.py` (additive `JobId`; only docstring lines edited), `src/sindri/schemas/episode.py` (new), `src/sindri/schemas/__init__.py` (exports), `tests/contract/test_episode_state.py` and `tests/contract/examples/{episode_state,episode_budget}.json` (new), `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff.
- Tests run/results: `ruff` clean; `mypy --strict` clean (17 files); `pytest`: 691 passed, 8 skipped (86 EpisodeState tests, 3 new ID tests).
- Acceptance evidence:
  - The adapted §20.11 snapshot validates and re-serializes to identical JSON: WAITING on two jobs with request hashes, resuming to DEV_CHECK, `reserved` = their sum, spent/elapsed, failure signature with count 2.
  - `remaining()` is derived from the bound budget, including reservations. It refuses a snapshot bound to another budget.
  - A test asserts that every ED13 restart field is required.
  - Planted bugs, each caught and the source restored:
    - WAITING with zero jobs → 1 failure;
    - reserved-sum check skipped → 3;
    - `request_hash` optional → 1;
    - candidate required in IMPLEMENT → 1 (the first-IMPLEMENT positive test);
    - zero additive limits rejected → 1.
- Implementation interpretations for coordinator review:
  1. **The transition table** has the explicit ADR-0006 lifecycle edges, `active → WAITING`, `WAITING → active`, and `non-terminal → ABORTED`. "WAITING returns only to its recorded `resume_state`" needs two snapshots → 009/P1.5.
  2. **Pending jobs** are allowed in active non-WAITING states (ED10: dispatch then continue).
  3. **`BudgetRemaining`** is a plain frozen dataclass and may hold negative values, so an overrun is representable rather than raising.
  4. **`remaining()`** raises if the snapshot's `budget_hash` is not this budget's `content_id()`.
  5. **Pending jobs need not bind the active candidate** (jobs may run against the best or an earlier candidate). Whether that is allowed per state is a P1.5 controller rule.
- Known limitations: cross-snapshot rules (edge legality, resume-to-recorded-state, monotonic spent/elapsed, constant budget/policy/solver hashes, budget ceilings) are SIN-P1.1-009. Failure-signature normalization and hashing are P1.5 (ED11).
- Handoff/next action: `docs/handoffs/SIN-P1.1-007.md`.
