# Current Phase

> The active phase, phase states and gates live **only** in `implementation/current.yaml`; task
> status lives **only** in `implementation/task_board.yaml` (ADR-0003). This file carries the
> narrative that does not fit there. Do not copy state values into it.

Quick view:
```bash
cat implementation/current.yaml
python scripts/show_ready_tasks.py --all
```

## Notes for the active phase
- `SIN-P1.1-001` verified (coordinator, 2026-10-04). Kept at `verified`, not `closed`, until the
  float/identity follow-up is carried forward (SIN-P1.1-002 decision D5, P1.1-G).
- `SIN-P1.1-002` verified (coordinator, 2026-10-04). PR #6 merged as `4377df5`; merged-main CI `37154049449` passed.
- `SIN-P1.1-003` verified (coordinator, 2026-10-04). PR #10 merged as `3a51766`; merged-main CI `37183976957` passed.
- `SIN-P1.1-004` verified (coordinator, 2026-10-04). PR #11 merged as `d465850`; merged-main CI `37184201021` passed after the deliberate 003+004 integration.
- `SIN-P1.1-005 — Observation` verified (coordinator, 2026-10-04). PR #15 merged as `7f16bf3`; merged-main CI `37204008101` passed.
- `SIN-P1.1-006 — Finding` verified (coordinator, 2026-10-05). PR #18 merged as `0d19b0f`; merged-main CI `37244343777` passed.
- `SIN-P1.1-007 — EpisodeState` verified (coordinator, 2026-10-05). PR #19 merged as `b6ced72`; merged-main CI `37256889064` passed on the deliberately integrated 006+007 state.
- The PR #17 readiness deviation is resolved: PRs #18/#19 applied the omitted final coordinator rules before verification.
- `SIN-P1.1-008 — Serialization and schema-versioning tests` verified (coordinator, 2026-10-05). PR #24 merged as `23983db`; merged-main CI `37262833634` passed. Scope remained tests/docs only.
- `SIN-P1.1-009 — Cross-record invariant tests` verified (coordinator, 2026-10-05). PR #28 merged as `a8b38c5`; merged-main CI `37269979595` passed. XR-T1 is a derived CT-4 property; the runtime validator carries 54 independently load-bearing codes with no-cascade ownership.
- No task is currently READY. **P1.1-G** gate packet is **drafted for coordinator review** (`planned`; `docs/tasks/SIN-P1.1-G.md`). Probes on `main` `efe9ccb` found: one runtime `assert` in `FormalReport.bound_met` (G-A); test-helper asserts that `python -O` would skip; exported JSON Schemas looser than the models (G-JS); and digits-only `EpisodeId`/`FindingId` patterns that cannot hold collision-resistant IDs (G-B, decided before P1.2). Gate execution and P1.2 remain unauthorized.
- Process deviation (recorded at the coordinator's request, not precedent): implementation of 003 and 004 began from the **unmerged** readiness commit `62a7834`, under delegation. The coordinator accepted that work for review, but READY was not yet authoritative on `main`. Future implementation waits until readiness is merged.

## P1.1 order (coordinator sequencing refinement, 2026-10-04; not an ADR change)
```
001 primitives (verified)
 └─ 002 TaskManifest + Requirement
     ├─ 003 EvaluationPolicy ─┐   (003 and 004 may run in parallel)
     └─ 004 CandidateManifest ┘
          └─ 005 Observation
              ├─ 006 Finding ─┐   (006 and 007 may run in parallel)
              └─ 007 EpisodeState ┘
                  └─ 008 serialization/versioning
                      └─ 009 cross-record invariants
                          └─ P1.1-G
```
Rationale: EvaluationPolicy references RequirementId; CandidateManifest references the task; Observation
needs stable candidate/policy/check references; Finding points to real Observations; 008/009 test the
network of records, not isolated classes. The coordinator still opens each packet; this order only
says which may be opened.

## Planned P1.1 breakdown (coordinator opens packets one at a time)

| Task | Outcome | Evidence beyond "the class exists" |
|---|---|---|
| SIN-P1.1-001 | Base IDs, content hashing, enums, status taxonomy | byte-change → new ID; infra statuses never coerce to PASS/FAIL |
| SIN-P1.1-002 | TaskManifest + Requirement | versioned immutable records; authority/split/lineage/rights never defaulted; structured rights; task-type edit scope; no floats or `Any`; no obligations on Requirement (ADR-0004) |
| SIN-P1.1-003 | EvaluationPolicy | mandatory checks and parameter matrix explicit; assumptions carry a source; **owns the requirement → obligation mapping and introduces `ObligationId` (ADR-0004)**; every approved mandatory requirement maps to ≥ 1 obligation |
| SIN-P1.1-004 | CandidateManifest | parent ancestry; frozen candidate immutable; author model/seed recorded |
| SIN-P1.1-005 | Observation | candidate hash + tool image digest mandatory; PASS requires a declared executed check; TOOL_ERROR distinct; unknown status rejected |
| SIN-P1.1-006 | Finding | status only via defined transitions; requirement, artifact and evidence references required |
| SIN-P1.1-007 | EpisodeState | budgets spent/remaining consistent; WAITING representable; pending jobs recorded |
| SIN-P1.1-008 | Serialization and schema-versioning tests | round-trip of every master §20 example; schema_version stored; old versions never silently reinterpreted |
| SIN-P1.1-009 | Cross-record invariant tests | claims of pass/fail reference Observation IDs (master §8.7); IDs resolve across records; **task/family/lineage/split identity cannot change across manifest versions** and (`task_id`, `requirement_id`) is stable across requirement versions (coordinator C5); **every approved mandatory requirement is enforced in every configuration where it applies, after policy exceptions: some obligation for it contains a mandatory, non-quality check that applies to that configuration** (PR #9 review) |
| SIN-P1.1-G | Subphase integration verification | all P1.1 tasks verified on main; exported JSON Schemas match models; float/identity rule (SIN-P1.1-001 follow-up) applied consistently across records |

## Rule
Only tasks with status `ready` on the task board may be assigned to coding agents.
