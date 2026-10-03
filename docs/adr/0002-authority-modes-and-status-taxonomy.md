# ADR-0002: Task authority modes and shared status taxonomy

- Status: accepted
- Accepted by: Avinash (architecture owner), 2026-10-04, with the TIMEOUT amendment in Decision; coordinator decision recorded by the coding agent from Avinash's instruction of 2026-10-04 (SIN-B0.1-002); confirm with an architecture-owner review comment on the B0 PR
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
- Raw status and its interpretation are separate layers, and the raw evidence is never rewritten:
  - **Observation layer.** A tool run's status is recorded exactly as observed. `TIMEOUT`,
    `TOOL_ERROR`, `UNSUPPORTED` and `INCONCLUSIVE` always remain themselves and MUST NOT be coerced to
    `FAIL` or `PASS`, by any component, at any time.
  - **Correctness labels.** Only `PASS` and `FAIL` observations carry a correctness label by default.
    `TOOL_ERROR`, `UNSUPPORTED` and `INCONCLUSIVE` never produce a label and never count toward
    acceptance.
  - **TIMEOUT.** By default a `TIMEOUT` produces no correctness label. If the task's
    `EvaluationPolicy` explicitly declares the relevant runtime limit as a task requirement, the
    downstream judge/training policy may derive a negative task outcome or reward from that
    `TIMEOUT`, while the underlying Observation keeps status `TIMEOUT` and the derived outcome
    references it. Code such as `if timeout and performance_bound: status = FAIL` is forbidden.
- `ACCEPTED` requires every mandatory check to be `PASS`.

## Alternatives considered
### Golden is always authoritative
Simpler, but teaches reference bugs as requirements for engineering-intent tasks.
### Binary pass/fail
Simpler, but labels infrastructure failures as candidate failures (a past bug class).

## Consequences
Schemas reference these enums; adding a status is a schema-semantic change requiring an ADR update.

## Validation
`tests/unit/test_status.py`; evaluator self-tests (timeout-as-pass must fail); SIN-P1.1-005 must show that an Observation's TIMEOUT status cannot be rewritten.

## Follow-up
SIN-P1.1-001 (formerly TASK-0001, see ADR-0003) finalizes these enums and aligns the `ToolStatus.is_label` docstring with the TIMEOUT wording above; later P1.1 tasks use them in `TaskManifest`, `Observation` and `EvaluationPolicy`.
