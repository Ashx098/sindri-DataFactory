# ADR-0006: Solver EpisodeState lifecycle (master F3 + WAITING), separate from the release workflow

- Status: accepted
- Accepted by: Avinash (architecture owner), 2026-10-04; coordinator decision ED1 posted on PR #17, recorded (not made) by the coding agent in SIN-P1.1-007 planning
- Owners: Avinash
- Supersedes: the reading of constitution §15's workflow list as the solver EpisodeState enum

## Context
Two canonical documents describe the episode state machine differently:
- master architecture §8 F3: `PREPARE → PLAN → IMPLEMENT → DEV_CHECK → TRIAGE ⇄ REPAIR → SUBMIT → JUDGE → RECORD`, with no WAITING;
- master §8.8: adds "WAITING is an explicit state for long formal/synthesis jobs. No model tokens are burned while the system is waiting for external work";
- repository constitution §15: `PREPARE → PLAN → IMPLEMENT → DEV_CHECK → TRIAGE ⇄ REPAIR → SUBMIT → ACCEPTANCE → WAITING → REVIEW → RELEASE / STOP`.

The constitution list mixes the solver episode with the broader acceptance/release workflow (master
§14.7 ReleaseManifest). SIN-P1.1-007 needs exactly one enum and one transition table.

## Decision
- `EpisodeState` v1 follows the master F3 solver/controller lifecycle, plus the explicit WAITING overlay of §8.8, plus two terminal states:
  `PREPARE, PLAN, IMPLEMENT, DEV_CHECK, TRIAGE, REPAIR, SUBMIT, JUDGE, RECORD, WAITING, COMPLETED, ABORTED`.
- The constitution's `ACCEPTANCE / REVIEW / RELEASE` are broader acceptance/release workflow concepts, not solver EpisodeState.
- Allowed transitions:
  - PREPARE → PLAN
  - PLAN → IMPLEMENT
  - IMPLEMENT → DEV_CHECK
  - DEV_CHECK → TRIAGE (failed or needs diagnosis), or DEV_CHECK → SUBMIT (development checks sufficient)
  - TRIAGE → REPAIR, or TRIAGE → ABORTED
  - REPAIR → DEV_CHECK
  - SUBMIT → JUDGE
  - JUDGE → RECORD
  - RECORD → COMPLETED
  - any non-terminal active state may enter WAITING, only with pending jobs; WAITING returns only to its recorded `resume_state`
  - any non-terminal state may go to ABORTED, with a controller stop reason
  - COMPLETED and ABORTED are terminal
- If implementation later shows a needed edge is missing, the table changes only through an explicit controller/ADR review. Routes are never added silently.

## Alternatives considered
### Adopt constitution §15 as the enum
Rejected: it makes release review part of every solver episode and duplicates ReleaseManifest concerns.
### Master F3 without WAITING
Rejected: §8.8 requires an explicit state in which no model tokens are spent while external jobs run.

## Consequences
- SIN-P1.1-007 exports this table as data (`ALLOWED_EPISODE_TRANSITIONS`); P1.5 (controller) and SIN-P1.1-009 (cross-snapshot checks) consume the same table.
- Release/acceptance workflow states are modelled later with ReleaseManifest, not in EpisodeState.

## Validation
SIN-P1.1-007 tests enumerate the states and edges; 009 rejects consecutive snapshots whose transition is not in the table.

## Follow-up
SIN-P1.1-007 implementation; P1.5 controller; constitution §15 wording may be clarified in a later governance change.
