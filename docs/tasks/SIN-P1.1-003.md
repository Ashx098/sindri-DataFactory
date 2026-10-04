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
| E7a | **Clarified (PR #9 review): no wall-clock expiry.** A PolicyException means "(check X, configuration Y) is semantically not applicable under this exact policy version". It has no expiry, because an immutable policy must not behave differently depending on the day it runs. Temporary, contextual waivers of failures are release waivers and live in the release layer (ReleaseManifest). |
| E5a | **Corrected (PR #9 review): zero-parameter designs.** `EvaluationPolicy.configurations` must contain ≥ 1 configuration, but `Configuration.assignments` **may be empty**. A design with no parameters has one explicit default configuration, e.g. `{"configuration_id": "cfg_default", "assignments": []}`. Two configurations with the same assignment set (including two empty ones) are still rejected. |

### Delegated decisions (2026-10-04), approved by the coordinator on PR #9
The coordinator delegated these two calls to the agent ("do what feels right and correct and why").
The agent decided them; the coordinator then **approved E8 and E9** in the PR #9 review.

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
    - `configurations`: non-empty. Each has a `configuration_id` and `assignments`, a tuple of `{name: ParameterName, value: ExactScalar}` with unique names. The tuple is empty for a no-parameter design (E5a). Configuration IDs are unique, and no two configurations may have the same assignment set; two empty sets count as the same.
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
  - every approved mandatory requirement is **enforced** (strengthened in the PR #9 review): for each configuration where it applies, after exceptions are applied, some obligation for it contains at least one **mandatory, non-quality check that applies to that configuration**. Merely having an obligation is not enough, because an obligation that uses only optional checks would let the judge accept without enforcing the requirement;
  - configuration parameter names match the task's contract.
- No `VerificationPlan` (P4.1). No Observation, Finding or EpisodeState.

## Interfaces touched
- Schemas: new `EvaluationPolicy` v1.
- IDs: additive `ObligationId`, `CheckId`, `ConfigurationId`, `ToolProfileId`, `ExceptionId`.
- Tool APIs: none. DB/migrations: none. External dependencies: none new.

## Acceptance criteria
Positive:
- [x] The adapted §20.10 example (per E1–E7) validates, round-trips and re-serializes to identical JSON.
- [x] Development and hidden checks coexist; a `bmc` check with depth and a `prove` check without depth validate.
- [x] One requirement covered by several obligations, and one obligation using several checks, validate.
- [x] A narrow exception excluding one (check, configuration) pair of a multi-configuration mandatory check validates.

Negative (each a separate test):
- [x] Every field required (no defaults), including `mandatory` and `visibility` on each check.
- [x] Unknown fields rejected at every level.
- [x] `mutation_qualification`, `clean_replay` or any unknown check kind → rejected (E3).
- [x] `formal_mode: cover` → rejected (E4); `bmc` without depth, depth on `prove`, depth < 1, or formal fields on a non-formal check → rejected.
- [x] A check referencing a configuration by index (an integer), or an unknown `ConfigurationId` → rejected (E5).
- [x] Duplicate configuration IDs or duplicate assignment sets → rejected; duplicate parameter names within a configuration → rejected.
- [x] A zero-parameter design validates with one explicit `cfg_default` configuration with empty assignments; two empty configurations are rejected as the same assignment set; an empty `configurations` list is rejected (E5a, PR #10 review).
- [x] Duplicate check, obligation or exception IDs → rejected.
- [x] An obligation with no checks, an unknown check, or only `quality` checks → rejected.
- [x] A mandatory `quality` check → rejected; a policy with no mandatory non-`quality` check → rejected.
- [x] An exception excluding a pair whose configuration the check does not target, or naming an unknown check → rejected.
- [x] Exceptions that together exclude every configuration of a mandatory check → rejected (E9).
- [x] An environment assumption without `source_ref` → rejected.
- [x] Version chain enforced; floats rejected at any depth; configuration values never coerced (`True` ≠ `1` ≠ `"1"`).
- [x] The record is immutable.

Planted-bug checks (run, record in the handoff, revert):
- [x] Defaulting `mandatory=True` on checks makes the suite fail.
- [x] Removing the obligation→check resolution check makes the suite fail.
- [x] Allowing `cover` as a formal mode makes the suite fail.

General:
- [x] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [x] `components/schemas.yaml` gains the policy invariants and the judge-side protection rule (E2); `docs/REPO_MAP.md` updated.
- [x] Handoff written; report ends with "Awaiting coordinator assignment."

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
`review` (authoritative status: `implementation/task_board.yaml`). Decisions E1–E9 implemented as written.

## Completion evidence
- Files changed: `src/sindri/core/ids.py` (additive: `ObligationId`, `CheckId`, `ConfigurationId`, `ToolProfileId`, `ExceptionId`; existing patterns untouched, only docstring lines edited), `src/sindri/schemas/policy.py` (new), `src/sindri/schemas/__init__.py` (exports), `tests/contract/test_evaluation_policy.py` and `tests/contract/examples/evaluation_policy.json` (new), `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff.
- Tests run/results (after PR #10 review fixes): `ruff` clean; `mypy --strict` clean (14 files); `pytest`: 359 passed, 8 skipped (83 EvaluationPolicy contract tests, 12 new ID tests).
- Acceptance evidence:
  - The adapted §20.10 example (4 explicit configurations, 6 checks across development/hidden, `bmc` depth 24, one quality check, 3 obligations over 2 requirements, one narrow formal exclusion) validates and re-serializes to identical JSON.
  - Rejection reasons spot-checked:
    - `cover` → enum error;
    - depth 0 → bound;
    - integer configuration index → type error;
    - empty obligation → length;
    - `r01` → ID pattern;
    - empty exclusion → length.
  - Planted bugs, each caught and reverted:
    - `mandatory` default → 1 failure;
    - obligation→check resolution removed → 1;
    - `cover` allowed → 1.
  - **mypy found a real bug during implementation:** a variable reused for configuration IDs and check IDs. The distinct ID types made the type checker reject the mix.
- Review fixes (PR #10):
  - **E5a:** `Configuration.assignments` may be empty. The new test fails with the original `min_length=1` restored (1 failure) and passes with the fix.
  - **E7a:** exceptions carry no expiry by design (semantic not-applicability); temporary waivers are release-layer.
  - **009:** the strengthened coverage rule (a mandatory, non-quality, applicable check per configuration after exceptions) is recorded in Non-goals and `CURRENT_PHASE.md`; it is not checked here because 003 cannot see `Requirement.mandatory` or applicability.
- Known limitations: the solver-safe projection (E2) is not built (P1.5/P5); its rule is recorded as INV-EP-001. Cross-record checks are SIN-P1.1-009.
- Handoff/next action: `docs/handoffs/SIN-P1.1-003.md`.
