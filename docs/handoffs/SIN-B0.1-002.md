# SIN-B0.1-002 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code) for Avinash
- Branch/worktree: `chore/SIN-B0.1-002-governance-fixups` (main working tree)
- HEAD commit: the commit that adds this file (child of `198c79a`)
- Base commit: `0743238` (`main`)
- Dirty files, if any: none after commit

## Completed
- **B0 as a whole (SIN-B0.1-001, merged `0743238`):** governance pack v2 with the ADR-0003 amendments; the B0 definition; text-native master architecture (`docs/architecture/MASTER_ARCHITECTURE.md`); scripts (`agent_bootstrap`, `new_task`, `new_handoff`, `show_ready_tasks`, `docx_to_md`); governance, import-boundary and status tests; the CI fast gate; `sindri.core.status` (the only product code).
- **This task (SIN-B0.1-002):**
  - ADRs back to `proposed`; decision-authority rule (AGENTS.md §3A) with an ADR status test.
  - SIN-B0.1-001 marked `merged`; task-status meanings documented (`merged` ≠ `verified`).
  - Exceptions register (`docs/implementation/EXCEPTIONS.md`).
  - Mandatory handoffs and the "never choose your next task" rule; richer handoff template.
  - Roles and owners plus held-out-family timing in PROJECT_STATE; `.github/CODEOWNERS` → `@Ashx098`.
  - SIN-P1.1-001 narrowed to base primitives; P1.1 breakdown in `docs/implementation/CURRENT_PHASE.md`.
  - CI runs on every branch push; CI negative probes run and deleted.
  - B0.G packet ready with `PENDING_HUMAN_APPROVAL`.
  - Pack ZIP moved to `~/Downloads`.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check . && uv run mypy && uv run pytest -q` | pass, 20 passed / 9 skipped | skips = packages not yet created |
| GitHub Actions `ci / fast-gate` on `main@0743238` | success | |
| GitHub Actions on `chore/...@198c79a` | success, run 37144678334 | |
| CI probes (one planted violation each) | all 4 failed at the `tests` step only | runs 37144694001, 37144697032, 37144700051, 37144703668; details in B0.G |

## Changed
Governance docs, `implementation/*.yaml`, `.github/` (CI trigger, CODEOWNERS), `tests/unit/test_governance.py`. No product code. No architecture content.

## Decisions
- ADR-0001 modular monolith layout and stack: **proposed**
- ADR-0002 authority modes and status taxonomy: **proposed**
- ADR-0003 adopt governance pack v2 with amendments: **proposed**

## Deviations
- B0-E001 direct push to `main` for the bootstrap commit (one-time, expired).
- B0-E002 combined B0.1–B0.5 in one packet (one-time).
- B0-E003 agent self-accepted ADRs (corrected here).
- This task also edits several B0 subphase areas, under the B0-E002 bootstrap exception; it is the last B0 task.

## Open questions
- Who fills the unassigned roles: RTL/domain reviewer, DV/formal reviewer, product/domain owner?
- When does a second reviewer exist, so code-owner review can be required?

## Blocked on
- **B0.G human approval** (`docs/implementation/gates/B0.G.md`), which needs:
  1. `main` branch protection enabled (repo admin: PR required, `fast-gate` check required, no force push);
  2. an accept/reject decision on ADR-0001/0002/0003;
  3. approval of exceptions B0-E001/E002.
- PR for this branch not opened: the agent's `gh` token is invalid. Open it from the GitHub UI or after `gh auth login`.

## Next ready after approval
- `SIN-P1.1-001`, base IDs, content hashing, enums and status taxonomy. Only this task, and only once the coordinator marks it `ready`.

## Do not start
- Any other P1.1 task (002–009) until SIN-P1.1-001 has merged and the coordinator opens it.
- P1.2 / P1.3 / P1.6 until P1.1 schemas merge and the coordinator opens them.
- Any P2+ work: repo miner, Spec Forge, exporter, RL, multi-agent orchestration, UI, PPA.

## Risks / things not to change casually
- `implementation/current.yaml` is the only phase-state authority; do not restate phase state in Markdown (a test enforces this).
- `tests/architecture/test_import_boundaries.py` package list mirrors ARCHITECTURE_GUARDRAILS; change both together, via an ADR.
- Do not require code-owner review while `@Ashx098` is the sole owner (it would block every merge).
