# SIN-B0.1-001 — Install governance pack v2 with amendments

## Phase identity
- Phase: `B0`
- Subphase: `B0.1` (also delivers B0.2–B0.5; bootstrap is one integration task)
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
The repository can run the P1–P6 process: a fresh agent given a TASK-ID can find its rules, scope,
phase and verification commands from the repository alone, and the fast CI gate exists.

## Why / architecture references
- Master architecture section(s): §4 principles, §21 repository, §23 build plan.
- Phase/subphase: `docs/implementation/phases/B0_BOOTSTRAP.md`
- ADRs/RFCs: ADR-0001, ADR-0002, ADR-0003.

## Owner / coordinator
- Owner: coding agent (Claude Code) under the platform lead
- Integrator: platform lead
- Reviewers: platform lead

## Base
- Base branch: `main`
- Base commit: none (initial repository)
- Worktree: main working tree

## Dependencies
- Required completed tasks: none
- Required schemas/contracts: none

## Scope
- In scope: pack v2 installation, ADR-0003 amendments, script fixes, B0 definition and gate packet, text-native master architecture, CI fast gate, governance consistency test, pruning empty packages, SIN-P1.1-001 packet.
- Allowed paths: repository root docs, `docs/`, `implementation/`, `scripts/`, `.github/`, `tests/unit/`, `tests/architecture/`, `src/sindri/*/AGENTS.md`, `pyproject.toml`, `uv.lock`.

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Other forbidden paths: any P1+ implementation code.

## Non-goals
No schemas, stores, tools, controller or judge code. No CODEOWNERS activation (needs real handles).

## Interfaces touched
- Schemas: none. Tool APIs: none. DB/migrations: none.
- External dependencies: `pyyaml` (dev only, governance test).

## Acceptance criteria
- [x] Pack v2 installed; amendments recorded in ADR-0003.
- [x] Broken scripts fixed and exercised.
- [x] `implementation/current.yaml` is the single phase-state authority; consistency test enforces it.
- [x] Master architecture available as Markdown with figures.
- [x] CI fast gate defined; same commands green locally.
- [x] Empty future-phase packages removed; boundary test cannot pass vacuously.
- [x] SIN-P1.1-001 packet created as `planned`.
- [ ] Coordinator review of B0.G (tracked in SIN-B0.1-002).

## Verification commands
```bash
uv run ruff check . && uv run mypy && uv run pytest -q
python scripts/show_ready_tasks.py --all
python scripts/agent_bootstrap.py SIN-P1.1-001 --path src/sindri/judge --brief
```

## Plan of record
See ADR-0003 "Decision".

## Status
`merged` at `0743238` (authoritative status: `implementation/task_board.yaml`)

## Completion evidence
- Files changed: see `git status` at the B0 commit; summary in ADR-0003.
- Tests run/results: recorded in `docs/implementation/gates/B0.G.md`.
- Acceptance evidence: `docs/implementation/gates/B0.G.md`.
- Known limitations: deviations B0-E001, B0-E002, B0-E003 (`docs/implementation/EXCEPTIONS.md`); follow-ups in SIN-B0.1-002.
- Handoff/next action: coordinator reviews B0.G, then marks SIN-P1.1-001 ready.
