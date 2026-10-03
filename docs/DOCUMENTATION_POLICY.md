# Documentation Policy and Update Matrix

Documentation is part of the implementation. Architecture-affecting changes do not merge with stale docs.

## Canonical documents
- `PRINCIPLES.md`: non-negotiable invariants; changes require architecture/security approval.
- `ARCHITECTURE_GUARDRAILS.md`: dependency and authority boundaries.
- `docs/adr/`: accepted durable decisions and rationale.
- `docs/rfcs/`: proposals under review.
- `components/*.yaml`: machine-readable component contracts.
- `docs/REPO_MAP.md`: current repository responsibility map.
- `docs/PROJECT_STATE.md`: current milestone/workstream state.
- `docs/tasks/`: scoped execution units.
- `docs/handoffs/`: temporary session continuity.

## Update matrix
| Change | Same-PR documentation/tests required |
|---|---|
| Add/rename/remove component | Repo map, component contract, owner, architecture diagram if affected, tests |
| Change public schema | Schema/version, examples, migration/compatibility note, contract tests |
| Change state machine | Controller docs/ADR if semantics changed, transition tests, replay tests |
| Add agent role | Agent card, prompt version, input/output permissions, qualification test |
| Change runtime prompt materially | Prompt version, agent card/changelog, qualification regression |
| Add/change tool adapter | Tool docs, capability matrix, golden logs, canary fixtures |
| Change evaluator/test/reference/assumption | Evaluation policy impact, requalification, evaluator certificate path |
| Change hidden-eval boundary | Security docs + ADR + leakage tests |
| Change dependency/framework | `THIRD_PARTY.md`, ADR if architectural, lockfile, compatibility tests |
| Change API/CLI | User/developer docs + tests |
| Fix production incident | Regression test + incident/postmortem if material |
| Complete milestone | Project state + roadmap status |

## Rule against documentation drift
If a code change makes a normative document false, the change is incomplete. If the intended behavior changed, update the normative document through the appropriate review mechanism rather than silently changing code.
