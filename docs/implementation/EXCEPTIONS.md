# Governance Exceptions Register

Every deviation from `AGENTS.md`, `CONTRIBUTING.md` or the implementation plan is recorded here
with its scope and expiry. **An exception is never precedent.** Future agents must not cite one to
justify the same deviation; a new deviation needs a new entry approved by the coordinator.

| ID | Rule deviated from | What happened | Why | Scope / expiry | Approved by |
|---|---|---|---|---|---|
| B0-E001 | No direct pushes to `main`; one branch/worktree + PR per task | Initial commit `0743238` was created on and pushed directly to `main` | The repository, branch policy, CI and PR templates did not exist before the bootstrap commit created them | One-time. Expired at `0743238`. Every later change uses a task branch/worktree and a PR unless a documented emergency process applies | pending coordinator (B0.G) |
| B0-E002 | One bounded task per subphase | `SIN-B0.1-001` delivered B0.1–B0.5 in one packet | The task-packet and phase machinery did not exist until that task created it | One-time, bootstrap only. From P1: one task, one bounded outcome, one primary component boundary, one acceptance contract | pending coordinator (B0.G) |
| B0-E003 | Agents do not accept their own decisions | ADR-0001/0002/0003 were first committed with status `accepted` by the authoring agent | Implementer error, caught in review | Corrected in `SIN-B0.1-002` (statuses now `proposed`); recorded as a lesson, not a permitted practice | n/a (correction) |
