# P6 — RL Environment and Flywheel

Canonical window: **weeks 16-24**.

## Subphases

### P6.1 — RL environment API
- Deliverable: Observation/action/transition/terminal interface over existing controller/tools; NeMo Gym-style adapter boundary.
- Depends on: `P5.G`
- Exit evidence: Inference evaluator and RL environment share trusted checker without sharing protected internals.

### P6.2 — Sealed reward/verifier service
- Deliverable: Correctness-first terminal reward, infra censor/retry policy, PPA disabled until correctness.
- Depends on: `P4.10 + P6.1`
- Exit evidence: Reward cannot be modified/read by policy workspace; hacking fixtures get no success reward.

### P6.3 — Asynchronous rollout execution
- Deliverable: Worker scheduling, idempotent episodes, checkpointing, cost/resource accounting.
- Depends on: `P6.1 + P6.2`
- Exit evidence: Worker loss/retry does not duplicate or corrupt episode labels.

### P6.4 — Curriculum and difficulty re-profiling
- Deliverable: Prioritize nontrivial pass-rate tasks; retire ceiling tasks; teacher/curriculum path for 0% tasks.
- Depends on: `P6.3`
- Exit evidence: Sampling distribution versioned and measurable.

### P6.5 — Failure miner
- Deliverable: Convert repeated Sindri failures into reviewed mutant/debug patterns and task candidates.
- Depends on: `P6.3`
- Exit evidence: Mined failures retain provenance and must re-enter qualification before training use.

### P6.6 — First RL round
- Deliverable: Run bounded RL after stable SFT/evaluator baseline.
- Depends on: `P6.2 + P6.4`
- Exit evidence: No reward-label instability or evaluator version drift during the scored round.

### P6.7 — Held-out evaluation and verification regression
- Deliverable: Compare E vs D; re-audit critical mutant escapes/false accept.
- Depends on: `P6.6`
- Exit evidence: Held-out-family gain with no increase in critical-mutant escape.

### P6.8 — Flywheel scale decision
- Deliverable: Decide production RL, more families, new task types, or redesign.
- Depends on: `P6.7`
- Exit evidence: Decision recorded in ADR/PROJECT_STATE; capacity scaling follows measured bottleneck.

### P6.G — Phase gate
- Deliverable: Integrated P6 review.
- Depends on: `P6.1-P6.8`
- Exit evidence: One RL round demonstrates held-out gain over SFT alone and verification quality does not regress; otherwise RL remains experimental.
