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
- B0.G approved 2026-10-04 with exception B0-E004: `main` branch protection must be enabled before
  SIN-P1.1-001's PR merges.
- **Only** `SIN-P1.1-001` is authorized. No other P1 task (P1.2 evidence store, P1.3 sandbox, P1.4 tool
  gateway, P1.6 FIFO, ...) may start until the coordinator opens it.

## Planned P1.1 breakdown (coordinator opens packets one at a time)
Records are separate tasks so no agent is handed "all schemas". 002–007 may run in parallel only
after 001 has merged and its primitives are frozen.

| Task | Outcome | Evidence beyond "the class exists" |
|---|---|---|
| SIN-P1.1-001 | Base IDs, content hashing, enums, status taxonomy | byte-change → new ID; infra statuses never coerce to PASS/FAIL |
| SIN-P1.1-002 | TaskManifest + Requirement | authority_mode, family/lineage and split mandatory; unknown fields rejected |
| SIN-P1.1-003 | EvaluationPolicy | mandatory checks and parameter matrix explicit; assumptions carry a source |
| SIN-P1.1-004 | CandidateManifest | parent ancestry; frozen candidate immutable; author model/seed recorded |
| SIN-P1.1-005 | Observation | candidate hash + tool image digest mandatory; PASS requires a declared executed check; TOOL_ERROR distinct; unknown status rejected |
| SIN-P1.1-006 | Finding | status only via defined transitions; requirement, artifact and evidence references required |
| SIN-P1.1-007 | EpisodeState | budgets spent/remaining consistent; WAITING representable; pending jobs recorded |
| SIN-P1.1-008 | Serialization and schema-versioning tests | round-trip of every master §20 example; schema_version stored; old versions never silently reinterpreted |
| SIN-P1.1-009 | Cross-record invariant tests | claims of pass/fail reference Observation IDs (master §8.7); IDs resolve across records |
| SIN-P1.1-G | Subphase integration verification | all P1.1 tasks verified on main; exported JSON Schemas match models |

## Rule
Only tasks with status `ready` on the task board may be assigned to coding agents.
