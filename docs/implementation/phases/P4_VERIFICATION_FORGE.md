# P4 — Verification Forge

Canonical window: **weeks 9-15**.

## Subphases

### P4.1 — VerificationPlan and requirement-obligation matrix
- Deliverable: Map every requirement to directed/random/formal/equivalence/mutation obligations and configurations.
- Depends on: `P3.2`
- Exit evidence: No mandatory requirement without disposition/obligation or explicit unsupported state.
- Ownership (ADR-0004): the VerificationPlan owns the requirement → obligation mapping; `Requirement` records carry no obligations.

### P4.2 — Reusable DV library
- Deliverable: clock/reset helpers; drivers/monitors/BFMs; ready-valid/APB/other initial protocol helpers; scoreboard base; trace utilities.
- Depends on: `P1.4 + P4.1`
- Exit evidence: Library has standalone unit/integration fixtures; no task-specific hidden assumptions baked into generic code.

### P4.3 — Clean-room reference-model path
- Deliverable: Reference author sees contract/spec, not candidate; fixed-width semantics and transaction model conventions.
- Depends on: `P4.1`
- Exit evidence: Reference model passes reviewed golden/alternative fixtures and has independent tests.

### P4.4 — Directed stimulus and scoreboard
- Deliverable: Reset, boundary, simultaneity, latency and protocol corner sequences; deterministic seeds.
- Depends on: `P4.2 + P4.3`
- Exit evidence: Known bugs produce first-divergence diagnostics tied to requirements.

### P4.5 — Constrained-random and coverage model
- Deliverable: Legal stimulus generators, seed recording, functional coverage bins/coverage matrix.
- Depends on: `P4.2 + P4.3`
- Exit evidence: Random runs are replayable; coverage does not itself decide acceptance.

### P4.6 — Property/formal subsystem
- Deliverable: SVA properties, assumptions, covers, proof modes/depth, assumption auditor.
- Depends on: `P4.1 + P1.4`
- Exit evidence: Vacuity/overconstraint fixtures caught; bounded vs proved scope preserved.

### P4.7 — Equivalence harness generation
- Deliverable: Task-specific reference/golden relation, reset alignment, parameter coverage and dont-care relation.
- Depends on: `P3.4 + P4.1`
- Exit evidence: Alternative correct architecture accepted when contract permits it.

### P4.8 — Suite qualifier / mutant kill loop
- Deliverable: Golden pass, alternative-correct pass, critical mutant kill, surviving-mutant targeted test loop.
- Depends on: `P4.4 + P4.5 + P4.6 + P4.7 + P2.5`
- Exit evidence: Every critical mutant killed or task quarantined; survivors inspected.

### P4.9 — Development vs hidden evaluator split + anti-hacking
- Deliverable: Protected hidden suite, solver visibility policy, fake PASS/early finish/test-edit/timeout/stale-cache attacks.
- Depends on: `P4.8`
- Exit evidence: No protected artifact reaches solver/retrieval/memory; attack fixtures blocked.

### P4.10 — EvaluatorCertificate and family qualification
- Deliverable: Versioned certificate, known-good/alternative counts, mutation vectors, formal scope, anti-hacking, replay, reviewer.
- Depends on: `P4.9`
- Exit evidence: At least three families qualified, including one spec-first/no-golden family.

### P4.G — Phase gate
- Deliverable: Integrated P4 review.
- Depends on: `P4.1-P4.10`
- Exit evidence: Three-family qualification bar met; alternative correct designs pass; critical mutants killed; assumptions/covers audited; development/hidden separation proven.
