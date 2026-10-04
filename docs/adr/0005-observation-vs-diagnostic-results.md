# ADR-0005: Observation is check evidence; diagnostic and qualification results are separate types

- Status: accepted
- Accepted by: Avinash (architecture owner), 2026-10-04; coordinator decision O1 posted on PR #13, recorded (not made) by the coding agent in SIN-P1.1-005 planning
- Owners: Avinash
- Supersedes: the reading of master architecture §8 F1 under which every Tool Gateway output is an `Observation`

## Context
Master §8 F1 says the Tool Gateway's output is "an Observation record", and lists among its typed
tools both candidate executions (`lint`, `compile`, `run_sim`, `run_formal`, `check_equiv`, `synth`)
and query-style tools (`inspect_waveform(run_id, …)`, `coverage(run_id)`). The same document makes
Observation the evidence required behind any claim of "passed", "failed", "proved" or "equivalent"
(§8.7), and treats PASS/FAIL as correctness-bearing statuses (§14 J2).

Read literally, a successful waveform query would be an `Observation(status=PASS)`. That overloads
PASS: the query succeeded, but the RTL did not pass anything. The same holds for:
- `coverage(run_id)`, which measures what an existing run exercised. Coverage shows what was exercised, not whether bugs would be caught (§11.11).
- formal `cover`, which is reachability/non-vacuity evidence, not proof of behaviour (E4 in SIN-P1.1-003).
- ad-hoc tool queries that match no declared policy check.

## Decision
- `Observation` v1 is the record of an **attempted execution of one declared EvaluationPolicy check** against one exact candidate. Only it can carry a correctness-bearing `ToolStatus` and serve as acceptance evidence.
- Waveform inspection, coverage queries, formal `cover` runs and undeclared ad-hoc queries produce a **separately typed result** (e.g. `DiagnosticResult`, or a qualification-specific result). That type is defined by the first task with a real consumer (P1.4 or P1.8), not now.
- Judge, qualification and dataset interfaces accept `Observation`, so the boundary is enforced by types rather than by every consumer remembering to filter.
- The master's informal use of "observation" for any tool output (e.g. §13: the solver sees "its own tool observations") remains valid prose. This ADR narrows the *record type* name only.

## Alternatives considered
### Every Tool Gateway output is an Observation (master F1 read literally)
Rejected: a query success becomes spellable as a correctness PASS; formal `cover` would contradict E4.
### One Observation type with a `scope: check | diagnostic` discriminator
Rejected for v1: every consumer would have to filter on scope; a missed filter turns diagnostics into
evidence. Separate types make the mistake unrepresentable.

## Consequences
- SIN-P1.1-005 implements `Observation` for declared check executions only, with `check_id` and `configuration_id` always required.
- P1.4/P1.8 define the diagnostic result type when `inspect_waveform`/`coverage` are implemented.
- SIN-P1.1-006 (Finding) decides how findings may cite diagnostic results as supporting, non-acceptance evidence.

## Validation
SIN-P1.1-005 tests show an Observation cannot exist without a policy check binding, and that
`quality` (no defined acceptance semantics yet) is not an Observation check kind in v1.

## Follow-up
SIN-P1.1-005 packet; diagnostic result type in P1.4/P1.8; SIN-P1.1-006 citation rules.
