# Project State

> Coordination document, not runtime truth. Phase and gate states live **only** in
> `implementation/current.yaml`; task status **only** in `implementation/task_board.yaml`
> (ADR-0003). This file holds workstreams, decisions and blockers. Update it in the same PR as
> milestone or workstream changes.

_Last updated: 2026-10-03_

## Versions
See `docs/implementation/VERSION.md`.

## Active workstreams
| Workstream | Owner | Status | Active task | Blocking decision |
|---|---|---|---|---|
| Governance/bootstrap | TBD | gate review | SIN-B0.1-001 | B0.G sign-off |
| Foundation (P1) | TBD | planned | SIN-P1.1-001 (planned) | B0.G |
| Task Forge | TBD | planned | — | P1.G |
| Spec Forge | TBD | planned | — | P1.G + P2 assets |
| Verification Forge | TBD | planned | — | P1.G + P3 contracts |
| Solver/Judge | TBD | planned | — | P1 substrate |
| Data/Training | TBD | planned | — | qualified data |

## Open decisions (need ADR/RFC or owner)
- Held-out family for the P5 transfer experiment (must be frozen before tuning; master §17.4).
- Real GitHub handles/teams for `.github/CODEOWNERS.example` → `CODEOWNERS`.
- Git remote and where CI runs.

## Current blockers
- B0.G awaiting coordinator review: `docs/implementation/gates/B0.G.md`.

## Risks being watched
Verification/formal engineer key-person dependency; density of weeks 10–16 (P4 tail + P5).
