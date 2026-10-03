# P1 — Foundation and Judge v0

Canonical window: **weeks 1-4**.

## Subphases

### P1.1 — Core domain schemas, IDs and status taxonomy
- Deliverable: TaskManifest, Requirement, EvaluationPolicy, CandidateManifest, Observation, Finding, EpisodeState; content IDs; semantic statuses.
- Depends on: `B0.G`
- Exit evidence: Schema tests; serialized examples; status enum cannot collapse TOOL_ERROR/TIMEOUT/INCONCLUSIVE into FAIL.

### P1.2 — Artifact identity and evidence store
- Deliverable: Content-addressed blobs, metadata store, append-only events, provenance references.
- Depends on: `P1.1`
- Exit evidence: Put/get/idempotency tests; same input hashes same; changed input never reuses result.

### P1.3 — Sandbox and execution substrate
- Deliverable: Fresh workspaces, resource limits, no-network profile, typed process execution.
- Depends on: `P1.1`
- Exit evidence: Isolation/security fixtures; resource limit and cleanup tests.

### P1.4 — Tool Gateway v0 and capability matrix
- Deliverable: slang/elaboration, lint/compile, Verilator/Icarus sim, basic SBY/Yosys/EQY interfaces, normalizers.
- Depends on: `P1.1 + P1.3`
- Exit evidence: Golden-log tests; canary HDL fixtures; unsupported constructs yield UNSUPPORTED, not fake PASS.

### P1.5 — Controller v0
- Deliverable: State machine, budgets, WAITING, invalidation, retry classification, pending jobs, restart.
- Depends on: `P1.1 + P1.2`
- Exit evidence: Transition tests; crash/restart; candidate edit invalidates evidence; infra retry distinct from candidate failure.
- Constraint (coordinator, 2026-10-04): P1.5 depends on abstract job/tool contracts and fakes only; it must not import concrete Verilator/SBY/Yosys adapters. It may proceed in parallel with P1.3/P1.4 once P1.1 and P1.2 have merged; integrated behaviour is demonstrated in P1.8.

### P1.6 — FIFO validation authority package
- Deliverable: Reviewed FIFO contract, two correct implementations, fixed parameter matrix, known-bad fixtures and 15-20 reviewed critical mutants.
- Depends on: `P1.1`
- Exit evidence: Both correct controls build; each mutant classified; expected behavior reviewed.

### P1.7 — Judge v0 and evaluator self-tests
- Deliverable: Equivalence/lint/synthesis-based acceptance inventory, anti-fake-PASS/stale-candidate fixtures.
- Depends on: `P1.2 + P1.4 + P1.6`
- Exit evidence: Judge accepts correct controls, rejects predefined critical defects and cannot be bypassed by status text.

### P1.8 — End-to-end deterministic FIFO episode
- Deliverable: Controller + tools + judge + evidence + replay, initially without LLM; then one bounded solver repair loop.
- Depends on: `P1.5 + P1.7`
- Exit evidence: Broken FIFO diagnosed/repaired/replayed; complete evidence graph; deterministic decision.

### P1.G — Phase gate
- Deliverable: Integrated P1 review.
- Depends on: `P1.1-P1.8`
- Exit evidence: Self-tests pass; all critical FIFO mutants killed; stale/fake PASS attacks fail; restart reproduces state; no unexplained replay mismatch.
