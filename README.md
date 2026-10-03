# Sindri Factory

A verified hardware engineering and data factory. It turns real RTL, repository history, reviewed
generators and approved use cases into executable engineering tasks; builds and qualifies
independent answer keys; lets deployment-shaped Sindri agents solve those tasks with controlled
tools; and exports the judged episodes as evaluation, SFT, preference and RL assets.

> Agents may propose. Tools may observe. Only independently controlled evidence may accept.

**Chat memory is never the source of truth. The repository is.**

## Start here
1. `PRINCIPLES.md`, `AGENTS.md`, `ARCHITECTURE_GUARDRAILS.md`
2. `docs/PROJECT_STATE.md`, `docs/REPO_MAP.md`
3. `implementation/current.yaml` (active phase) and `docs/implementation/CURRENT_PHASE.md`
4. your task packet under `docs/tasks/` and the nearest local `AGENTS.md`

Or let the script print all of it:
```bash
python scripts/agent_bootstrap.py SIN-P1.1-001 --path src/sindri/schemas
```

The architecture itself: `docs/architecture/MASTER_ARCHITECTURE.md` (generated from the canonical
`.docx` in `docs/reference/`).

## Implementation sequencing
The six-phase execution plan is under `docs/implementation/`. Coding agents do not choose what to
build next: they implement one coordinator-approved, dependency-ready TASK-ID.
```bash
python scripts/show_ready_tasks.py        # what may be worked on now
python scripts/new_task.py SIN-P1.4-003 "Verilator lint adapter"   # coordinator only
python scripts/new_handoff.py SIN-P1.1-001                         # end of an unfinished session
```

## Developer quick start
```bash
uv sync
uv run ruff check . && uv run mypy && uv run pytest -q
```

## Scope (V1)
Single-clock, synchronous, block-level digital RTL. Not silicon sign-off, CDC, timing closure,
analog or physical design (master architecture §25).
