# ADR-0004: Requirement records do not own verification obligations

- Status: accepted
- Accepted by: Avinash (architecture owner), 2026-10-04; coordinator decision D4 posted on PR #4, recorded (not made) by the coding agent in SIN-P1.1-002 planning
- Owners: Avinash
- Supersedes: the `obligation_ids` field in the master architecture §20.9 `Requirement` example

## Context
The master architecture §20.9 example gives `Requirement` an `obligation_ids` list
(`[sim_stall_01, sva_stall_stable]`). The same document also says:
- requirements are clarified and approved at the task/spec stage (§6.5, Task Forge + Spec Forge);
- verification obligations are planned from approved requirements by the Verification Forge (§11.6:
  "Every Requirement ID produces one or more verification obligations"), which P4.1 implements as
  the "VerificationPlan and requirement-obligation matrix".

If `Requirement` owns its obligations, a requirement cannot be approved until its testbench plan
exists. That inverts the order of the flow: the requirement record would have to know verification
artifacts that are written later and by a different, clean-room role (§11.2).

## Decision
- `Requirement` records the requirement only: identity (`task_id`, `requirement_id`, version), source,
  original wording, normalized semantics, legal environment, assumptions, applicability, mandatory
  flag and disposition. It has **no** `obligation_ids` field.
- The requirement → obligation mapping is owned downstream by `EvaluationPolicy` (SIN-P1.1-003) and,
  in P4, by the `VerificationPlan` / requirement-obligation matrix (P4.1). Each obligation references
  the requirement it covers as (`task_id`, `requirement_id`).
- Traceability stays bidirectional (§11.6) and is computed from the policy/plan side.
  "Every approved mandatory requirement has at least one obligation" is enforced where the mapping
  lives: SIN-P1.1-003 for structure, P1.1-009 for cross-record checks, and qualification (G1)
  operationally.
- `ObligationId` is created by the first task that has a real consumer for it (SIN-P1.1-003), per
  decision D2's rule of no ID types without consumers.

## Alternatives considered
### Keep `obligation_ids` on Requirement (master §20.9 as written)
Rejected: it couples requirement approval to verification planning and lets a requirement record be
"incomplete" for reasons outside its authority.
### Store the mapping in both places
Rejected: two sources of truth for traceability that can drift.

## Consequences
- The §20.9 example is read without `obligation_ids`; the text-native master copy is generated from
  the .docx and is not hand-edited, so this ADR is the record of the difference.
- SIN-P1.1-003's packet must include the requirement → obligation mapping and the
  "approved mandatory requirement has ≥ 1 obligation" check.
- P4.1's VerificationPlan inherits the same ownership.

## Validation
SIN-P1.1-002 tests show `Requirement` rejects an `obligation_ids` field (unknown field). SIN-P1.1-003
and P1.1-009 test the mapping and its completeness.

## Follow-up
SIN-P1.1-003 packet; P4.1 phase notes.
