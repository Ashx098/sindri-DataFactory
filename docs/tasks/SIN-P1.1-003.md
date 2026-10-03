# SIN-P1.1-003 — EvaluationPolicy and requirement-obligation mapping

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`EvaluationPolicy` exists as a strict, versioned, immutable record that states exactly what must be
checked for a task: the required checks and their configurations, proof modes and tool-profile
references, the supported parameter matrix, sourced environment assumptions, approved exceptions,
and the requirement → obligation mapping that ADR-0004 assigned to it. The judge (P1.7), controller
(P1.5) and Verification Forge (P4) can then consume one closed definition of "what acceptance
means" for a task.

## Why / architecture references
- Master architecture: §8.7 ("EvaluationPolicy: required check IDs, configurations, proof modes, tool profiles, parameter matrix, assumptions and approved exceptions"); §11.6 requirement → obligation traceability; §11.10 assumptions need a Requirement/EvaluationPolicy source; §11.14 finite parameter matrix; §14 J1 check order, J5 versioning; §14.7 waivers; Appendix A acceptance policy; §20.10 example.
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md`: 002 → **{003, 004}** → 005.
- ADRs/RFCs: ADR-0002 (statuses), **ADR-0004** (this record owns the obligation mapping and introduces `ObligationId`).

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash; DV/formal reviewer for check kinds and proof modes once assigned (role unassigned)

## Base
- Base branch: `main`
- Base commit: `main` when the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-003`

## Dependencies
- Required completed tasks: SIN-P1.1-002 (verified)
- Required schemas/contracts: `sindri.schemas._base` (`Record`, `StrictModel`, `ExactScalar`, `NonEmptyText`, version chain), `sindri.core.ids`, `sindri.core.status`

## Decisions needed before READY
The master architecture underdetermines these. The agent recommends an option for each; **the coordinator decides**.

| ID | Question | Agent recommendation |
|---|---|---|
| E1 | **Policy scope.** §20.10 has `policy_id: ep_fifo_004` and `contract_hash`, but no `task_id`. Yet ADR-0004 obligations reference (`task_id`, `requirement_id`). Is a policy per task, or shared per contract/family? | **Per task.** Add `task_id` and bind `contract_hash` (it must equal the task's `approved_contract_hash`, checked in 009). Obligations then cover that task's requirements. Family-level sharing can be a later template mechanism, not a shared authoritative record. |
| E2 | **Hidden checks.** §20.10 lists `hidden_check_ids`, but the solver must never see hidden tests (§8.9, J4). | Every check declares `visibility: development \| hidden`. The whole `EvaluationPolicy` is a **judge-side protected record**; a solver-visible projection is a later concern (P1.5/P5). This task only models the classification and records the protection rule in the component contract. |
| E3 | **Check vocabulary.** §20.10 uses `parse, directed, random, formal_core, critical_mutation, synth`; Appendix A uses `parse_elaborate, directed_regression, …`. | A `CheckKind` enum from J1 plus Appendix A: `integrity_scan`, `parse_elaborate`, `lint`, `synthesis`, `directed_sim`, `random_sim`, `formal`, `equivalence`, `mutation_qualification`, `clean_replay`, `quality`. Each check has its own `CheckId` (`chk_…`). `quality` checks can never be mandatory (correctness-first, principle 7). Certificate-validity items (`spec_certificate_valid`, `evaluator_certificate_valid`, `contract_approved`) are qualification-gate preconditions (P1.7/G1), not checks in this record. |
| E4 | **Formal/tool profiles.** §20.10 shows `formal_profiles: {...}`; tool profiles do not exist until P1.4. | Reference profiles by ID (`ToolProfileId` `tp_…`); do not model profile contents. Formal checks carry `proof_mode: bmc \| prove \| cover` and, for `bmc`, a required `depth: StrictInt ≥ 1`. Profile contents are P1.4. |
| E5 | **Parameter matrix.** §20.10 `{WIDTH: [1,8,32], DEPTH: [1,2,3,8]}`: a cross product, or explicit configurations? | **Explicit configurations** (`tuple[Configuration, …]`, each a full parameter assignment with `ExactScalar` values), because §11.14 records evidence per configuration and some combinations may be unsupported. Reuse the 002 strict-scalar rules. A check may target a subset of configurations by index or ID. |
| E6 | **Obligation shape.** | `Obligation`: `obligation_id: ObligationId`, `requirement_id: RequirementId` (exactly one; §11.6 "every requirement produces one or more obligations"), and `check_ids: tuple[CheckId, …]` (non-empty, each must exist in this policy). |
| E7 | **Approved exceptions / waivers** (§14.7: narrow, justified, versioned). | `ApprovedException`: `exception_id`, `scope` (the check IDs and configurations it covers), `justification`, `approved_by`, `expires` (an explicit date or `null`). A waiver never turns a failed mandatory check into a pass for dataset labelling (recorded as an invariant; enforced in the judge, P1.7). |

## Scope (written for the recommended options; finalized after decisions)
- In scope:
  - `src/sindri/core/ids.py`, additive only: `ObligationId` (pattern from the master examples `sim_stall_01`, `sva_stall_stable`), `CheckId` (`chk_…`), `ToolProfileId` (`tp_…`), `ExceptionId` (`ex_…`).
  - `src/sindri/schemas/policy.py`: `EvaluationPolicy` (`Record`):
    - `policy_id: PolicyId`, `policy_version` and `supersedes` (version chain as in 002), `task_id`, `contract_hash: ContentId`;
    - `configurations` (non-empty, unique, explicit);
    - `checks` (non-empty, unique `CheckId`): each with `kind`, `mandatory: StrictBool` (no default), `visibility`, `tool_profile_id`, the `configurations` it applies to, and formal fields per E4;
    - `environment_assumptions` (each with `text` and a required `source_ref`);
    - `obligations` (non-empty, unique `ObligationId`);
    - `approved_exceptions`.
  - In-record invariants:
    - unique IDs throughout;
    - every obligation's `check_ids` and every check's configuration references resolve inside the policy;
    - no `quality` check is mandatory;
    - at least one mandatory correctness check exists;
    - BMC checks have `depth`, non-BMC checks do not;
    - exceptions only reference existing checks;
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.10 example fixture.
- Allowed paths: `src/sindri/schemas/policy.py`, `src/sindri/schemas/__init__.py` (exports only), `src/sindri/core/ids.py` (additive only), `tests/contract/`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-003.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none may be created; fixtures use synthetic check names only.
- Other forbidden paths: `src/sindri/schemas/{_base,task,requirement}.py` (verified in 002; any needed change goes back to the coordinator), `src/sindri/schemas/candidate.py` (SIN-P1.1-004), existing ID patterns, `core/status.py`.

## Non-goals
- No tool-profile contents (P1.4), no judge logic, no waiver application (P1.7), no solver projection of the policy (P1.5/P5).
- No cross-record checks. These belong to SIN-P1.1-009:
  - the policy's `contract_hash` equals the task's `approved_contract_hash`;
  - every obligation's requirement exists on the task;
  - every approved mandatory requirement has at least one obligation (ADR-0004 completeness).
- No `VerificationPlan` (P4.1). No Observation, Finding or EpisodeState.

## Interfaces touched
- Schemas: new `EvaluationPolicy` v1. IDs: additive `ObligationId`, `CheckId`, `ToolProfileId`, `ExceptionId`.
- Tool APIs: none. DB/migrations: none. External dependencies: none new.

## Acceptance criteria
Positive:
- [ ] The adapted §20.10 example (per E1–E7) validates, round-trips and re-serializes to identical JSON.
- [ ] Development and hidden checks coexist; a BMC check with depth and a prove/cover check without depth validate.
- [ ] One requirement covered by several obligations, and one obligation using several checks, validate.

Negative (each a separate test):
- [ ] Every field required (no defaults), including `mandatory` and `visibility` on each check.
- [ ] Unknown fields rejected at every level.
- [ ] Duplicate check, obligation, configuration or exception IDs → rejected.
- [ ] An obligation referencing a check not in the policy → rejected; an obligation with no checks → rejected.
- [ ] A check referencing a configuration not in the policy → rejected.
- [ ] A mandatory `quality` check → rejected; a policy with no mandatory correctness check → rejected.
- [ ] BMC without depth, depth on prove/cover, or depth < 1 → rejected.
- [ ] An environment assumption without `source_ref` → rejected.
- [ ] An exception referencing an unknown check → rejected.
- [ ] Version chain enforced; floats rejected at any depth; configuration values never coerced (`True` ≠ `1` ≠ `"1"`).
- [ ] The record is immutable.

Planted-bug checks (run, record in the handoff, revert):
- [ ] Defaulting `mandatory=True` on checks makes the suite fail.
- [ ] Removing the obligation→check resolution check makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [ ] `components/schemas.yaml` gains the policy invariants and the "judge-side protected record" rule (E2); `docs/REPO_MAP.md` updated.
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
- Shared files: `src/sindri/schemas/__init__.py` (exports), `components/schemas.yaml`, `docs/REPO_MAP.md`. These are append-only edits that merge trivially; the integrator resolves ordering.
- `src/sindri/core/ids.py` is edited **only by this task**; 004 must not touch it.

## Status
`planned`. Draft for coordinator review; decisions E1–E7 open (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
