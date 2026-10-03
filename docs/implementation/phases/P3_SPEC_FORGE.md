# P3 — Spec Forge

Canonical window: **weeks 6-11**.

## Subphases

### P3.1 — Fact Sheet extractor
- Deliverable: ports, types, parameters, clock/reset, hierarchy hints, memories/FSMs, registered/combinational paths, behavioral probes.
- Depends on: `P1.4 + P2.7`
- Exit evidence: Facts reproducible from fixed golden/tool versions; uncertain facts marked instead of invented.

### P3.2 — Authority bundle and contract compiler
- Deliverable: authority_mode, requirement IDs, legal environment, reset/protocol/timing/arithmetic/parameter semantics, decision log.
- Depends on: `P3.1`
- Exit evidence: Contract never silently turns golden quirks into product intent; conflicts quarantine.

### P3.3 — Spec renderers and deterministic linter
- Deliverable: ticket/datasheet/waveform/state-table styles; number/port/polarity/coverage checks.
- Depends on: `P3.2`
- Exit evidence: Each style maps requirements back to contract; missing/unmapped fields fail lint.

### P3.4 — Spec equivalence/miter engineering
- Deliverable: reset alignment, dont-care masking, uninitialized state, contract assumptions, covers, bounded/proved evidence labels.
- Depends on: `P1.4 + P3.2`
- Exit evidence: Known equivalence/non-equivalence fixtures classified correctly.

### P3.5 — Round-trip reconstructors
- Deliverable: Multiple clean-room reconstructions from spec only + assumption logs.
- Depends on: `P3.3 + P3.4`
- Exit evidence: Compile failures separated from spec insufficiency; equivalence evidence recorded.

### P3.6 — Class hunters + free-form adversary
- Deliverable: reset/timing/handshake/simultaneity/memory/arithmetic/boundary/illegal input/bit-order/FSM forks.
- Depends on: `P3.3 + P3.4`
- Exit evidence: Forks are minimal and behavior-changing or discarded.

### P3.7 — Trace interrogation and resolver
- Deliverable: blind A/B traces, sentence-cited verdicts, pin/dont-care/human escalation policy.
- Depends on: `P3.5 + P3.6`
- Exit evidence: No majority-vote resolution; every ambiguity resolution has provenance.

### P3.8 — Leakage critic and SpecCertificate
- Deliverable: identifier/internal-structure leakage checks, evidence tier, rounds/forks/reconstructors/resolutions.
- Depends on: `P3.7`
- Exit evidence: Certificate is machine-readable and tied to exact contract/spec hashes.

### P3.9 — Planted-ambiguity calibration
- Deliverable: human-audited specs + sentence deletion/number blur/table-row drop/contradiction fixtures.
- Depends on: `P3.8`
- Exit evidence: Recall/false-flag measured per ambiguity class; “hunter-only finds” reported.

### P3.G — Phase gate
- Deliverable: Integrated P3 review.
- Depends on: `P3.1-P3.9`
- Exit evidence: Certified specs in at least two styles for P2 tasks; spec-first/no-golden route demonstrated; calibration measured; authority conflicts quarantine.
