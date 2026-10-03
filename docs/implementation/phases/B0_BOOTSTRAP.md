# B0 — Bootstrap (governance, tasking, handoffs, CI)

B0 is not a seventh architecture phase. It makes the repository able to run the P1–P6 process:
an agent given a TASK-ID can find its rules, scope, phase and verification commands from the
repository alone, and CI enforces the fast gate.

## Subphases

### B0.1 — Governance installation
- Deliverable: governance pack v2 installed; amendments recorded (ADR-0003); ADR-0001 layout/stack and ADR-0002 authority/status taxonomy accepted.
- Depends on: —
- Exit evidence: root docs, templates and local AGENTS.md present; no contradictions between PRINCIPLES, GUARDRAILS and the master architecture's authority modes.

### B0.2 — Text-native master architecture
- Deliverable: `docs/architecture/MASTER_ARCHITECTURE.md` generated from the canonical .docx by `scripts/docx_to_md.py`, with figures.
- Depends on: —
- Exit evidence: all 27 chapters and appendices present; tables, code blocks and links preserved; header names the source document.

### B0.3 — Working tasking and handoff tooling
- Deliverable: `agent_bootstrap.py`, `new_task.py`, `new_handoff.py`, `show_ready_tasks.py` run; single source of truth for phase state (`implementation/current.yaml`).
- Depends on: B0.1
- Exit evidence: each script exercised; governance consistency test validates board ↔ packets ↔ current.yaml.

### B0.4 — Fast CI gate
- Deliverable: `.github/workflows/ci.yml` running ruff, mypy --strict and pytest (unit + architecture + governance).
- Depends on: B0.3
- Exit evidence: the same commands pass locally; import-boundary test proven to fail on a planted violation.

### B0.5 — First P1 task packet
- Deliverable: `SIN-P1.1-001` packet on the board as `planned`, depending on `B0.G`.
- Depends on: B0.1
- Exit evidence: packet has phase identity, dependencies, allowed/forbidden paths, non-goals, verification commands.

### B0.G — Gate
- Deliverable: gate evidence packet `docs/implementation/gates/B0.G.md`.
- Exit evidence: coordinator sets Decision to COMPLETE, sets `phases.B0.state: COMPLETE`, `phases.P1.state: ACTIVE`, `active_phase: P1` in `implementation/current.yaml`, and marks `SIN-P1.1-001` ready.
