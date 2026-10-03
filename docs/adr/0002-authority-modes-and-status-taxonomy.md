# ADR-0002: Task authority modes and shared status taxonomy

- Status: proposed (prepared by coding agent; awaiting architecture-owner review)
- Date: 2026-10-03
- Owners: platform lead, DV/formal engineer
- Supersedes: n/a

## Context
Two decisions are likely to be "simplified" by future agents without knowing why:
1. Whether golden RTL is always the truth.
2. Whether timeouts, crashes and unsupported constructs can be folded into PASS/FAIL.
Both silently corrupt labels if gotten wrong (master §4, §14 J2).

## Decision
- Every task declares `AuthorityMode`: `reference_behavior` (reproduce the reference under a
  declared relation), `engineering_intent` (approved contract outranks the reference; conflicts are
  quarantined), or `correct_by_construction` (reviewed generator/reference defines the family; a
  generator bug invalidates all descendants).
- All components use the enums in `sindri.core.status`: `ToolStatus`, `CheckStatus`, `Verdict`,
  `Tier`, `EvidenceLevel`, `AuthorityMode`. No ad-hoc status strings.
- Only `PASS` and `FAIL` are labels. `TOOL_ERROR`, `UNSUPPORTED` and `INCONCLUSIVE` are never labels
  and never acceptance. `TIMEOUT` is a negative label only when the contract sets a performance bound.
- `ACCEPTED` requires every mandatory check to be `PASS`.

## Alternatives considered
### Golden is always authoritative
Simpler, but teaches reference bugs as requirements for engineering-intent tasks.
### Binary pass/fail
Simpler, but labels infrastructure failures as candidate failures (a past bug class).

## Consequences
Schemas reference these enums; adding a status is a schema-semantic change requiring an ADR update.

## Validation
`tests/unit/test_status.py`; evaluator self-tests (timeout-as-pass must fail).

## Follow-up
SIN-P1.1-001 (formerly TASK-0001, see ADR-0003) uses these enums in `TaskManifest`, `Observation` and `EvaluationPolicy`.
