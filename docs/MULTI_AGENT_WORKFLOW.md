# Multi-Agent and Multi-Chat Development Workflow

## Goal
Allow many coding agents and human engineers to work over weeks without relying on conversational memory or accidentally forking the architecture.

## Roles
- **Task owner/coordinator**: owns scope, integration, and final acceptance of the development task.
- **Implementer agent(s)**: create bounded patches in isolated worktrees.
- **Reviewer agent/human**: checks code and architecture against recorded contracts.
- **Integrator**: resolves cross-branch conflicts and runs integration gates. Often the coordinator.

## Task packet is mandatory
Every non-trivial unit of work has `docs/tasks/TASK-ID.md` containing:
- purpose and user-visible outcome;
- exact scope and non-goals;
- base commit;
- allowed/expected paths;
- dependencies/ADRs;
- interfaces/schemas touched;
- acceptance tests;
- documentation obligations;
- risk/security notes;
- current status and owner.

## Worktree rule
One concurrent implementer = one branch/worktree. Agents do not share a mutable working directory.

Suggested layout:
```text
../worktrees/SIN-P1.4-003-agent-a/
../worktrees/SIN-P1.4-003-agent-b/
```

## Parallel decomposition
Parallelize only work with clean artifact boundaries, for example:
- one agent writes a schema + tests;
- one builds a tool adapter behind that schema;
- one prepares golden logs/canary fixtures;
- one reviews docs/ADR.

Avoid two agents editing the same state machine or schema simultaneously unless one explicitly owns integration.

## Findings and disagreements
A disagreement is recorded in the task/PR with:
- claim;
- relevant invariant/ADR;
- concrete evidence;
- proposed discriminating test or decision required.

Do not resolve architecture disagreements by majority vote between models.

## New-chat continuation
A fresh chat must be able to continue using only repository state. The new agent reads root rules, project state, repo map, task packet, latest handoff, branch history, and local rules. If anything important exists only in the old chat, the previous session was not closed correctly.

## End-of-session handoff
Every meaningful session ends by writing or updating `docs/handoffs/TASK-ID.md`, **whether or not the work is merged**: phase/subphase boundaries, gate submissions, agent replacement, long interruptions, architecture decisions and integration completion all require it. Use `docs/handoffs/TEMPLATE.md`. It records:
- exact branch/worktree and HEAD commit;
- what is complete;
- what changed and why;
- tests run and results;
- files intentionally left modified;
- open failures/risks;
- next exact action;
- decisions that still need promotion to ADR/docs.

Handoffs are temporary coordination artifacts. Durable decisions must move into ADRs/architecture/component docs.
