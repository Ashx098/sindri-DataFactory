# P5 — Solver, Exporter and Deciding Experiment

Canonical window: **weeks 10-16**.

## Subphases

### P5.1 — Model gateway and minimal agent runtime
- Deliverable: Provider-independent generate/tool loop, model/version/cost/provenance logging, budgets.
- Depends on: `P1.5`
- Exit evidence: Same task can run across configured models without changing solver code.

### P5.2 — Hardware-native ACI and minimal repo intelligence
- Deliverable: typed file/module/hierarchy/search/diff/waveform/formal tools; bounded context builder.
- Depends on: `P2.2 + P5.1`
- Exit evidence: Agent does not require raw hidden shell/evaluator access; context provenance recorded.

### P5.3 — Deployment-shaped solver loop
- Deliverable: Understand -> plan -> implement -> check -> debug -> submit, single agent default.
- Depends on: `P5.1 + P5.2 + P4.9`
- Exit evidence: Solver cannot read hidden suite/golden/reference internals and respects controller budgets.

### P5.4 — Failure triage and repair planner
- Deliverable: Deterministic routing, first violation/minimal reproducer, observation vs inference, repeat-failure/stagnation handling.
- Depends on: `P5.3`
- Exit evidence: Known syntax/sim/assertion/formal/infra fixtures route correctly; repairs branch from immutable candidate.

### P5.5 — Episode/trajectory recorder
- Deliverable: Complete actions, candidates, observations, costs, assistance, checkpoints, final verdict.
- Depends on: `P5.3 + P1.2`
- Exit evidence: Replay can reconstruct episode state; no critical step exists only in chat/log prose.

### P5.6 — Dataset exporter
- Deliverable: reasoning SFT, agentic trajectory, debug, verification, preference, RL-task streams; provenance/rights/evidence filters.
- Depends on: `P5.5 + P2.6 + P4.10`
- Exit evidence: Ineligible/final-eval/customer-isolated data is excluded by testable policy.

### P5.7 — SFT baseline
- Deliverable: Verified teacher/student data format, EOS/tool schema checks, training recipe and checkpoint evaluation.
- Depends on: `P5.6`
- Exit evidence: Training loss is recorded but not used as deployment decision; base+harness comparator frozen.

### P5.8 — Pre-register held-out transfer experiment
- Deliverable: Arms A-E, budgets, metrics, seeds, exclusion rules, structurally different held-out family >=100 tasks.
- Depends on: `P4.G + P5.7`
- Exit evidence: Experiment plan committed before viewing final results.

### P5.9 — Run matched-budget experiment
- Deliverable: Base, base+harness, harness+playbook, SFT+harness, optional RL arm only if ready.
- Depends on: `P5.8`
- Exit evidence: Capability vector + paired results + evaluator false-accept estimate reported.

### P5.10 — Go/no-go decision
- Deliverable: Apply pre-registered decision table; decide scale/redesign/RL entry.
- Depends on: `P5.9`
- Exit evidence: Decision references held-out transfer, cost and verification quality—not public benchmark/training reward alone.

### P5.G — Phase gate
- Deliverable: Integrated P5 review.
- Depends on: `P5.1-P5.10`
- Exit evidence: Single-agent baseline stable; trajectories complete; held-out family frozen; SFT vs base+harness compared fairly; decision recorded.
