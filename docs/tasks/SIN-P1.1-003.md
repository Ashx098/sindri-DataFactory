# SIN-P1.1-003 — EvaluationPolicy and requirement-obligation mapping

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`EvaluationPolicy` exists as a strict, versioned, immutable record that states exactly what must be
checked for one task: the per-candidate correctness checks and their exact configurations, formal
modes and tool-profile references, sourced environment assumptions, narrow not-applicable
exclusions, and the requirement → obligation mapping that ADR-0004 assigned to it. The judge (P1.7),
controller (P1.5) and Verification Forge (P4) can then consume one closed definition of "what must
pass" for a task.

## Why / architecture references
- Master architecture: §8.7 (EvaluationPolicy contents); §11.6 traceability; §11.10 assumptions need a Requirement/EvaluationPolicy source, covers demonstrate reachability; §11.14 finite parameter matrix with evidence per exact configuration; §14 J1 check order, J5 versioning; §14.7 judging vs release (clean replay and waivers are release concerns); Appendix A; §20.10 example.
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md`: 002 → **{003, 004}** → 005.
- ADRs/RFCs: ADR-0002 (statuses), **ADR-0004** (this record owns the obligation mapping and introduces `ObligationId`).

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash; DV/formal reviewer for check kinds and formal modes once assigned (role unassigned)

## Base
- Base branch: `main`
- Base commit: `main` when the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-003`

## Dependencies
- Required completed tasks: SIN-P1.1-002 (verified)
- Required schemas/contracts: `sindri.schemas._base` (`Record`, `StrictModel`, `ExactScalar`, `NonEmptyText`, version chain), `sindri.schemas.requirement.ParameterName` (import only), `sindri.core.ids`, `sindri.core.status`

## Coordinator decisions (PR #8, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| E1 | **Accepted.** The policy is task-scoped: it carries `task_id` and binds `contract_hash` (equality with the task's `approved_contract_hash` is checked in SIN-P1.1-009). |
| E2 | **Accepted.** Every check declares `visibility: development \| hidden`. The full policy is a judge-side protected record; a solver-safe projection comes later (P1.5/P5). |
| E3 | **Corrected.** Per-candidate check vocabulary only: `integrity_scan`, `parse_elaborate`, `lint`, `synthesis`, `directed_sim`, `random_sim`, `formal`, `equivalence`, `quality`. `mutation_qualification` belongs to evaluator/task qualification and `clean_replay` to the release/gate layer (master §14.7 separates judging from release replay), so neither is a per-candidate check. `quality` can never be mandatory for functional correctness. |
| E4 | **Corrected.** Profiles are referenced by `ToolProfileId`; contents are P1.4. Formal correctness modes are **`bmc` or `prove` only**. A cover demonstrates reachability/non-vacuity, does not prove a behavioural requirement, and belongs to formal/evaluator qualification, so it can never satisfy an obligation in this record. `bmc` requires `depth: StrictInt ≥ 1`; `prove` has no depth. |
| E5 | **Accepted, with `ConfigurationId`.** Configurations are explicit, each with a `ConfigurationId` (its first real consumer, so it is introduced here). Checks reference configurations **by ID, never by list index**, because evidence must be scoped to exact finite configurations (§11.14). |
| E6 | **Accepted.** One obligation → exactly one `RequirementId` → one or more checks of this policy. Cross-record completeness stays in SIN-P1.1-009. |
| E7 | **Corrected semantics.** A policy exception is a narrow **not-applicable exclusion** for specific (check, configuration) pairs. It never turns an executed FAIL into PASS. An alternative checker requires a new policy version. Release-level waivers stay a ReleaseManifest concern. |

### Delegated decisions (2026-10-04)
The coordinator delegated these two calls to the agent ("do what feels right and correct and why").
They are recorded as **agent decisions under explicit delegation**, take effect only when the
coordinator merges the PR that records them, and can be reversed by the coordinator at any time.

| ID | Decision | Rationale |
|---|---|---|
| E8 | **Adopted.** Every obligation includes at least one non-`quality` check. | Follows from E3 (quality is never correctness evidence); otherwise a requirement could be "satisfied" by an area report. |
| E9 | **Adopted.** An exception set may not exclude every configuration of a mandatory check. Removing or replacing a mandatory check requires a new policy version. | Enforces E7's own route (new policy version) and prevents silent weakening through exclusions. |

Both rules only restrict. Relaxing a schema later is backward compatible (stored records stay valid),
while tightening it later invalidates stored records, so foundation schemas start strict.

## Scope
- In scope:
  - `src/sindri/core/ids.py`, additive only:
    - `ObligationId` (from the master examples `sim_stall_01`, `sva_stall_stable`);
    - `CheckId` (`chk_…`), `ConfigurationId` (`cfg_…`), `ToolProfileId` (`tp_…`), `ExceptionId` (`ex_…`).
  - `src/sindri/schemas/policy.py`: `EvaluationPolicy` (`Record`):
    - Identity: `policy_id: PolicyId`, `policy_version` and `supersedes` (version chain as in 002), `task_id: TaskId`, `contract_hash: ContentId`.
    - `configurations`: non-empty. Each has a `configuration_id` and `assignments`, a non-empty tuple of `{name: ParameterName, value: ExactScalar}` with unique names. Configuration IDs are unique, and no two configurations may have the same assignment set.
    - `checks`: non-empty, unique `CheckId`. Each check has:
      - `kind: CheckKind` (E3), `mandatory: StrictBool` (no default), `visibility` (E2);
      - `tool_profile_id`;
      - `configuration_ids`: non-empty, unique, each resolving to a configuration in this policy;
      - for `formal` checks, `formal_mode: bmc | prove` and `depth`, per E4. Non-formal checks carry neither.
    - `environment_assumptions`: each with `text` and a required `source_ref`.
    - `obligations`: non-empty, unique `ObligationId`. Each has one `requirement_id` and non-empty, unique `check_ids` that resolve to checks in this policy.
    - `exceptions`: each with `exception_id`, `excludes` (a non-empty, unique tuple of `{check_id, configuration_id}` pairs, where the configuration must be one the check targets), `justification` and `approved_by` (non-blank). Meaning: the pair is not applicable (E7).
  - In-record invariants:
    - unique IDs throughout;
    - all references resolve inside the policy;
    - no mandatory `quality` check;
    - at least one mandatory non-`quality` check;
    - no quality-only obligation (E8);
    - formal-mode/depth pairing;
    - no all-configuration exclusion of a mandatory check (E9);
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.10 example fixture.
- Allowed paths: `src/sindri/schemas/policy.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-003.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created; fixtures use synthetic check names only.
- Other forbidden paths:
  - `src/sindri/schemas/{_base,task,requirement}.py` (verified; import only);
  - `src/sindri/schemas/candidate.py` (SIN-P1.1-004);
  - existing ID patterns in `core/ids.py`;
  - `core/status.py`.

## Non-goals
- No `mutation_qualification`, `clean_replay` or cover checks (E3/E4: qualification and release layers).
- No tool-profile contents (P1.4), no judge logic (P1.7), no solver projection (P1.5/P5), no release waivers (ReleaseManifest).
- No cross-record checks. These belong to SIN-P1.1-009:
  - `contract_hash` equals the task's `approved_contract_hash`;
  - obligation requirements exist on the task;
  - every approved mandatory requirement has at least one obligation;
  - configuration parameter names match the task's contract.
- No `VerificationPlan` (P4.1). No Observation, Finding or EpisodeState.

## Interfaces touched
- Schemas: new `EvaluationPolicy` v1.
- IDs: additive `ObligationId`, `CheckId`, `ConfigurationId`, `ToolProfileId`, `ExceptionId`.
- Tool APIs: none. DB/migrations: none. External dependencies: none new.

## Acceptance criteria
Positive:
- [ ] The adapted §20.10 example (per E1–E7) validates, round-trips and re-serializes to identical JSON.
- [ ] Development and hidden checks coexist; a `bmc` check with depth and a `prove` check without depth validate.
- [ ] One requirement covered by several obligations, and one obligation using several checks, validate.
- [ ] A narrow exception excluding one (check, configuration) pair of a multi-configuration mandatory check validates.

Negative (each a separate test):
- [ ] Every field required (no defaults), including `mandatory` and `visibility` on each check.
- [ ] Unknown fields rejected at every level.
- [ ] `mutation_qualification`, `clean_replay` or any unknown check kind → rejected (E3).
- [ ] `formal_mode: cover` → rejected (E4); `bmc` without depth, depth on `prove`, depth < 1, or formal fields on a non-formal check → rejected.
- [ ] A check referencing a configuration by index (an integer), or an unknown `ConfigurationId` → rejected (E5).
- [ ] Duplicate configuration IDs or duplicate assignment sets → rejected; duplicate parameter names within a configuration → rejected.
- [ ] Duplicate check, obligation or exception IDs → rejected.
- [ ] An obligation with no checks, an unknown check, or only `quality` checks → rejected.
- [ ] A mandatory `quality` check → rejected; a policy with no mandatory non-`quality` check → rejected.
- [ ] An exception excluding a pair whose configuration the check does not target, or naming an unknown check → rejected.
- [ ] Exceptions that together exclude every configuration of a mandatory check → rejected (E9).
- [ ] An environment assumption without `source_ref` → rejected.
- [ ] Version chain enforced; floats rejected at any depth; configuration values never coerced (`True` ≠ `1` ≠ `"1"`).
- [ ] The record is immutable.

Planted-bug checks (run, record in the handoff, revert):
- [ ] Defaulting `mandatory=True` on checks makes the suite fail.
- [ ] Removing the obligation→check resolution check makes the suite fail.
- [ ] Allowing `cover` as a formal mode makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [ ] `components/schemas.yaml` gains the policy invariants and the judge-side protection rule (E2); `docs/REPO_MAP.md` updated.
- [ ] Handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/policy.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_evaluation_policy.py`, `tests/contract/examples/evaluation_policy.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-004
- Shared files: `src/sindri/schemas/__init__.py` (exports), `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These are append-only edits; the integrator resolves ordering.
- `src/sindri/core/ids.py` is edited **only by this task**; 004 must not touch it.

## Status
`ready` (2026-10-04; coordinator decisions E1–E7 on PR #8, delegated decisions E8–E9; authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
