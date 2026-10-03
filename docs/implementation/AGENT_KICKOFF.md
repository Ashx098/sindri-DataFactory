# Agent Kickoff Protocol

Every fresh coding-agent chat/session must:
1. Read root PRINCIPLES, AGENTS, ARCHITECTURE_GUARDRAILS.
2. Read PROJECT_STATE, CURRENT_PHASE, IMPLEMENTATION_PLAN and active phase file.
3. Read the assigned task packet and nested AGENTS files.
4. Inspect ADRs/component contracts/schemas/tests relevant to the task.
5. Inspect git status, branch/worktree and base commit.
6. Restate outcome, non-goals, dependencies, allowed paths and verification plan before editing.
7. Implement only that task; no future-phase scaffolding.
8. Run acceptance checks and update docs in the same change.
9. Record a handoff if work is not fully merged.

A new chat is given a TASK-ID, not “continue from the previous chat.”
