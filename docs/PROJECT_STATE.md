# Project State

> Coordination document, not runtime truth. Phase and gate states live **only** in
> `implementation/current.yaml`; task status **only** in `implementation/task_board.yaml`
> (ADR-0003). This file holds workstreams, decisions and blockers. Update it in the same PR as
> milestone or workstream changes.

_Last updated: 2026-10-04_

## Versions
See `docs/implementation/VERSION.md`.

## Roles and owners
Roles must exist even when one person holds several. `unassigned` roles are real gaps, not TBD placeholders.

| Role | Owner | Notes |
|---|---|---|
| Coordinator / architecture owner | Avinash (@Ashx098) | accepts ADRs, approves gates, assigns tasks |
| Foundation / platform | Avinash | P1 lead |
| AI / model / solver | Avinash | |
| Data / training | Avinash | |
| Judge / release | Avinash + DV/formal reviewer | acceptance-critical: needs the DV reviewer once assigned |
| RTL / domain reviewer | **unassigned** | needed by P1.6 (FIFO contract review) |
| DV / formal reviewer | **unassigned** | needed by P1.6–P1.7; key-person risk (master §24) |
| Product / domain | **unassigned** | Chipforge owner for use cases and authority conflicts |

## Active workstreams
| Workstream | Status | Active task | Blocking decision |
|---|---|---|---|
| Governance/bootstrap | complete | — | — |
| Foundation (P1) | active | SIN-P1.1-001…005 verified; 006 + 007 ready (parallel) | — |
| Task Forge | planned | — | P1.G |
| Spec Forge | planned | — | P1.G + P2 assets |
| Verification Forge | planned | — | P1.G + P3 contracts |
| Solver/Judge | planned | — | P1 substrate |
| Data/Training | planned | — | qualified data |

## Scheduled decisions
| Decision | When | Status |
|---|---|---|
| Split policy: family/lineage split before descendants; no train/dev/final contamination via retrieval, caches, examples or generated descendants | now | fixed by master §4/§9 T5; enforced in P2.6 |
| Candidate held-out families profiled (structurally different, base+harness pass rate in a useful band) | P2.G / early P3 | open |
| Final held-out family locked | before the first tuning dataset is finalized; before SFT sees anything derived from it | open |
| Second reviewer for code-owner-required reviews | before enabling "require code owner review" | open |

## Current blockers
- None. Recommended: enable "Do not allow bypassing the above settings" on `main` (required checks are currently enforced for non-admins only).

## Risks being watched
Verification/formal engineer key-person dependency; density of weeks 10–16 (P4 tail + P5).
