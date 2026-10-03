# Architecture Guardrails

## Canonical shape
Sindri Factory is a modular monolith with explicit authority boundaries:

`Task Forge -> Spec Forge -> Verification Forge -> Qualification -> Solver -> Trusted Judge -> Data/Training`

The foundation underneath provides schemas, identity/hashing, evidence storage, controller, model gateway, tool gateway, sandbox, context/retrieval, workers, and observability.

## Dependency direction
The following is the intended dependency direction. Reverse imports require an ADR.

- `core`: IDs, hashes, statuses, errors, permissions. Depends on no project package.
- `schemas`: versioned boundary records. Depends on `core` and Pydantic only.
- `evidence`: artifact/event/provenance interfaces. Depends on `core`, `schemas`.
- `models`: model-gateway interfaces and role metadata. No dependency on judge/evaluator internals.
- `tools`: typed tool contracts/adapters. No dependency on solver policy.
- `context`: repository intelligence and role projections. Cannot expose forbidden scopes.
- `controller`: state machine, budgets, invalidation, scheduling. Owns workflow transitions.
- `agents`: thin runtime and role adapters. Uses schemas/model/tool interfaces, not authoritative hidden state.
- `task_forge`, `spec_forge`, `verification_forge`: produce task/oracle artifacts through published interfaces.
- `qualification`: consumes frozen task/evaluator artifacts and emits admission decisions/certificates.
- `solver`: sees public task/repo/dev tools only. Must not import `judge.hidden` or final evaluator content.
- `judge`: consumes frozen submission and protected evaluation policy. Must not ask solver to change itself.
- `data`: consumes immutable episode/evidence records and enforces rights/lineage/split policy.
- `training`: consumes exported qualified datasets/environments; never imports final-evaluation artifacts.

## Framework rule
Generic agent frameworks are adapters, never architectural owners. Pi/OpenCode/OpenHands/SWE-ReX/LangGraph/etc. may be evaluated behind `AgentRuntime`, `WorkspaceRunner`, or UI interfaces. They may not become the source of truth for workflow state, evidence, permissions, task identity, or acceptance.

## Database and artifact authority
- PostgreSQL: authoritative metadata and append-only events.
- S3/MinIO or content-addressed filesystem: immutable raw artifacts.
- Git: candidate/source evolution, diffs, worktrees; not the sole system database.
- Parquet: exported analytical/training datasets, not runtime authority.

## Golden/reference authority modes
Every task declares one authority mode:
- `REFERENCE_BEHAVIOR`: reproduce the trusted reference behavior; quirks are target behavior if explicitly admitted.
- `ENGINEERING_INTENT`: approved product/engineering contract outranks an implementation. Conflicts between intent/docs/reference are quarantined until resolved.
- `CORRECT_BY_CONSTRUCTION`: a human-reviewed generator plus its reference defines the intended family (Task Forge T3). A generator or reference bug invalidates every descendant task until fixed. *(Restored from master architecture §4/§9.1 by ADR-0003.)*

Code uses `sindri.core.status.AuthorityMode` (ADR-0002); there are no ad-hoc authority strings.

Never silently turn an engineering-intent task into a reference-copy task.

## Enforcement
`tests/architecture/test_import_boundaries.py` enforces the table below. Changing a row requires an ADR and the matching test change in the same PR. The package list is fixed there, so a package cannot appear without first being added to this document.

| Package | Must not import |
|---|---|
| `core` | any other `sindri` package |
| `schemas` | `judge`, `solver`, `triage`, forges |
| `evidence` | `agents`, `models`, `solver` |
| `controller` | `models`, `agents` (no model reasoning in workflow transitions) |
| `models`, `context`, `agents`, `training` | `judge` |
| `tools` | `solver` |
| forges | `solver` |
| `solver` | `judge` |
| `judge` | `solver`, `triage` |
| `data` | `judge`, `solver` |
