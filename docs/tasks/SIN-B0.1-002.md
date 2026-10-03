# SIN-B0.1-002 — Governance fixups before B0.G review

## Phase identity
- Phase: `B0`
- Subphase: `B0.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
B0 is clean enough for human gate review: no self-accepted decisions, accurate task states,
documented bootstrap exceptions, a durable fresh-session handoff, CI proven to pass and to fail on
violations in GitHub Actions, and a B0.G packet with Decision `PENDING_HUMAN_APPROVAL`.

## Why / architecture references
- Master architecture section(s): §4 (agents propose, authority accepts).
- Phase/subphase: `docs/implementation/phases/B0_BOOTSTRAP.md`.
- ADRs/RFCs: ADR-0001/0002/0003 (status correction only; content unchanged).
- Coordinator review of B0 (2026-10-04): "Clean B0 first. Submit B0.G evidence. Stop."

## Owner / coordinator
- Owner: coding agent (Claude Code)
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `0743238`
- Worktree: main working tree, branch `chore/SIN-B0.1-002-governance-fixups`

## Dependencies
- Required completed tasks: SIN-B0.1-001
- Required schemas/contracts: none

## Scope
- In scope:
  - ADR-0001/0002/0003 → `proposed`; ADR lifecycle and decision-authority rule (AGENTS.md §3A); ADR status test.
  - SIN-B0.1-001 → `merged`; task-status meanings (`merged` ≠ `verified`) on the board.
  - Exceptions register: B0-E001 direct-to-main, B0-E002 combined B0 packet, B0-E003 self-accepted ADRs.
  - Mandatory end-of-session handoff rule; richer handoff template; B0 handoff.
  - "Agents never choose their next task" end-of-task report rule.
  - Roles/owners and held-out-family timing in PROJECT_STATE; CODEOWNERS with the real maintainer handle.
  - SIN-P1.1-001 narrowed to base primitives; P1.1 breakdown recorded in CURRENT_PHASE.
  - CI runs on every branch push; negative CI probes; B0.G evidence packet.
  - Stray ZIP moved out of the repository.
- Allowed paths: governance docs, `docs/`, `implementation/`, `.github/`, `tests/unit/test_governance.py`.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Other forbidden paths: all `src/sindri/` product code; architecture content of ADRs.

## Non-goals
No product architecture change, no P1 implementation, no gate approval, no ADR acceptance.

## Interfaces touched
- Schemas: none. Tool APIs: none. DB/migrations: none. External dependencies: none.

## Acceptance criteria
- [x] ADRs `proposed`; agents cannot accept decisions (rule + test).
- [x] Board and packets consistent; SIN-B0.1-001 `merged`.
- [x] Exceptions B0-E001..E003 recorded as non-precedent.
- [x] B0 handoff exists (`docs/handoffs/SIN-B0.1-002.md`).
- [x] Fast gate passes in GitHub Actions on this branch.
- [x] Deliberate violations fail in GitHub Actions (probe branches, then deleted).
- [x] B0.G packet complete with `PENDING_HUMAN_APPROVAL`.
- [x] `main` branch protection enabled (coordinator; closed B0-E004).
- [x] PR opened and merged (PR #1, by the coordinator).

## Verification commands
```bash
uv run ruff check . && uv run mypy && uv run pytest -q
python scripts/show_ready_tasks.py --all
```

## Plan of record
See Scope.

## Status
`merged` (head `0cb29dd`, on `main` via `7cf0fd8`; authoritative status: `implementation/task_board.yaml`)

## Completion evidence
- Files changed: see PR diff.
- Tests run/results: `docs/implementation/gates/B0.G.md`.
- Acceptance evidence: `docs/implementation/gates/B0.G.md`.
- Known limitations: branch protection and PR creation require a repo admin with valid GitHub auth.
- Handoff/next action: `docs/handoffs/SIN-B0.1-002.md`.
