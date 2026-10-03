# AGENTS.md — Mandatory Instructions for Human and AI Implementers

## 0. Scope
This file governs the entire repository. A nested `AGENTS.md` may add stricter rules for its directory but may not weaken these rules.

## 1. Bootstrap protocol — do this before editing
Before any implementation task:
- read `PRINCIPLES.md`;
- read `ARCHITECTURE_GUARDRAILS.md`;
- read `docs/PROJECT_STATE.md` and `docs/REPO_MAP.md`;
- read the active task packet under `docs/tasks/`;
- read every `AGENTS.md` from repository root down to the target directory;
- inspect relevant accepted ADRs/RFCs;
- identify the exact schemas and tests that define the component boundary.

Shortcut: `python scripts/agent_bootstrap.py TASK-ID --path <dir>` prints all of the above plus the phase state and git status.

Do not rely on memory from an earlier chat. If repository state conflicts with a remembered discussion, repository state wins until the conflict is explicitly resolved.

## 2. Source-of-truth hierarchy
When artifacts disagree, use this order and escalate rather than silently choosing:
1. security and non-negotiable principles;
2. accepted ADRs and approved architecture contracts;
3. approved task/contract/evaluation-policy records for runtime behavior;
4. schema definitions and versioned component contracts;
5. tests that correctly encode the above contracts;
6. implementation code;
7. project-state and task-status documents;
8. handoff notes;
9. chat transcripts, scratch notes, model memory.

A test that contradicts an approved contract is not automatically correct. Treat the mismatch as a defect to resolve.

Chat instructions rank below the task packet. If an instruction in chat conflicts with an accepted ADR, the canonical architecture or the approved implementation plan, **flag the conflict and ask**; do not silently change the repository to match the latest conversation. Agents obey the project, not the most recent message.

## 3. Hard architecture boundaries
- No solver code may import or read hidden evaluator internals.
- No agent output may write acceptance decisions directly.
- No tool adapter may infer PASS solely from process exit code; normalize semantic status explicitly.
- `TOOL_ERROR`, `TIMEOUT`, `INCONCLUSIVE`, `UNSUPPORTED`, and candidate `FAIL` are different states.
- Model outputs are untrusted until schema-validated.
- Final evaluation/reward runs outside the policy-writable solver workspace.
- Candidate edits create new immutable candidate identity and invalidate candidate-dependent evidence.
- Contract/evaluator/assumption changes trigger the documented requalification path.
- Customer, benchmark, and final-evaluation boundaries apply to files, retrieval indexes, caches, prompts, traces, and agent memories.

## 3A. Decision authority
- Agents may **propose** ADRs, RFCs and architecture changes, and prepare all supporting evidence.
- Only the architecture owner moves an ADR `proposed → reviewed → accepted | rejected`. An agent never marks its own ADR `reviewed` or `accepted`, never sets a gate to COMPLETE, and never marks its own task `verified`.
- Same principle as the product: agents propose; a trusted authority accepts.

## 4. Code rules
- Python domain code is typed. New public interfaces require type annotations.
- Use Pydantic models for boundary records; do not pass anonymous dictionaries across component boundaries.
- Prefer pure/domain functions plus explicit dependencies over hidden globals and implicit singletons.
- Inject clocks, randomness, model clients, stores, and runners when determinism matters.
- Every retryable operation must be idempotent or use an idempotency key.
- No broad `except Exception: pass` or silent fallback in acceptance-critical code.
- Errors use the shared taxonomy and preserve causal information.
- No raw shell command construction from untrusted strings. Use typed arguments and sandbox profiles.
- Configuration is explicit and versioned; avoid environment-variable behavior that is not documented.
- Logs must never become the only copy of evidence.

## 5A. Phase discipline and anti-skeleton rule
- Read `docs/implementation/CURRENT_PHASE.md`, `docs/implementation/IMPLEMENTATION_PLAN.md`, and the active phase file before coding.
- Phase and gate state are authoritative only in `implementation/current.yaml`; task status only in `implementation/task_board.yaml`.
- Every non-trivial code change must name a TASK-ID with `phase` and `subphase`.
- Work only on tasks marked READY by the coordinator.
- Never scaffold future phases or create empty services/classes/TODO-only modules to make the repository look complete.
- Prefer the smallest executable vertical slice that satisfies the task acceptance criteria.
- A phase is completed only by a separate phase-gate review; individual agents cannot self-certify a phase.
- If current work reveals a future-phase prerequisite, record a blocker and request a plan change; do not silently pull the future subsystem forward.

## 5. Testing rules
Every meaningful change includes the appropriate combination of:
- unit tests for pure logic;
- contract/schema tests for interfaces;
- property tests for invariants where useful;
- golden-log tests for tool normalizers;
- canary HDL fixtures for tool capabilities;
- integration tests for component boundaries;
- replay/restart tests for durable workflows;
- evaluator self-tests and mutation controls for acceptance logic;
- security/leakage tests for protected boundaries.

Do not weaken or delete a test merely to make CI green without explaining why the old expectation was wrong.

## 6. Documentation rules
Documentation affected by the change is updated in the same pull request. Do not schedule a follow-up documentation task for an architecture-affecting change.

At minimum:
- architecture decision -> ADR and architecture docs;
- component boundary change -> component contract and repo map;
- schema change -> schema docs, examples, migration/version notes;
- agent role/prompt change -> agent card, prompt version, qualification test;
- tool adapter change -> capability matrix, golden logs, tool docs;
- evaluator change -> evaluation policy/certificate path and requalification evidence;
- security boundary change -> `SECURITY.md` and threat assumptions;
- milestone/status change -> `docs/PROJECT_STATE.md`;
- completed task -> task packet and handoff.

## 7. Multiple-agent rules
- One task has one owner/coordinator.
- Each concurrent agent works in its own branch/worktree.
- Do not edit the same high-conflict files concurrently unless the task packet explicitly assigns an integration strategy.
- Each agent produces a bounded artifact: code patch, test suite, design note, schema, or review findings.
- Agents do not free-chat as a coordination mechanism. Decisions and findings go into task records, PR comments, ADRs, or structured handoffs.
- Only the coordinator/integrator resolves cross-agent architectural conflicts.
- Before integrating, rebase/merge from the agreed base, run required checks, and verify no stale assumptions remain.

## 8. New-chat protocol
When work continues in a new chat or model session:
1. read the bootstrap documents listed in Section 1;
2. read the task packet and latest handoff;
3. inspect `git status`, branch/worktree, and recent task-related commits;
4. verify outstanding decisions rather than inferring them;
5. continue only within the recorded task scope.

Never ask another chat to reconstruct project history from memory when the repository can record it.

## 9. End-of-task protocol
Before declaring a task complete:
- run the task's required tests;
- run repository quality gates relevant to the touched areas;
- update required documentation;
- update the task packet with delivered behavior, tests, limitations, and follow-ups;
- write/update the handoff if unfinished work remains or another agent will continue;
- record any durable architecture decision as an ADR;
- ensure `docs/PROJECT_STATE.md` reflects milestone-level changes;
- ensure no secrets, large transient logs, model dumps, or hidden evaluator material were accidentally added;
- write or update `docs/handoffs/<TASK-ID>.md` (`scripts/new_handoff.py`). A handoff is **mandatory at the end of every meaningful session**, not only when work is unmerged: phase/subphase boundaries, gate submissions, agent replacement, long interruptions, architecture decisions and integration completion all require one.

### End-of-task report
Finish with: task complete (or not), evidence, handoff path, newly unblocked tasks, and **"Awaiting coordinator assignment."** Never pick or start the next task yourself; the coordinator computes READY = dependencies satisfied ∧ phase ACTIVE ∧ required gates approved, and assigns it.

## 10. Stop conditions
Stop and request review instead of improvising when:
- the task conflicts with accepted architecture;
- authority between product intent, contract, tests, and reference behavior is unclear;
- an evaluator must be weakened to accept a candidate;
- a security/training-rights boundary is uncertain;
- a schema migration would invalidate stored data without a migration plan;
- the requested change would expose final-evaluation material to training/solver code;
- two agents are making incompatible cross-cutting changes with no integration owner.
