# P2 — Code-first and mutation sources

Canonical window: **weeks 4-7**.

## Subphases

### P2.1 — Source-rights and repository registry
- Deliverable: Approved source list, license/rights fields, source provenance and exclusion policy.
- Depends on: `P1.G`
- Exit evidence: Every source candidate carries rights/provenance before task cutting.

### P2.2 — Repository miner and elaboration/cut pipeline
- Deliverable: Clone/import, elaborate with slang/Yosys, hierarchy map, build checker, clean cut points.
- Depends on: `P1.4 + P2.1`
- Exit evidence: Golden repo builds before/after cut; cut task retains reproducible build context.

### P2.3 — Git-history task extraction
- Deliverable: Classify feature/fix/refactor commits; build modification/debug task candidates.
- Depends on: `P2.2`
- Exit evidence: Sample feature/fix tasks reproduce before/after relation; refactors do not become false behavior-change tasks.

### P2.4 — Mutation operator library
- Deliverable: AST/semantic operators for reset, boundary, handshake, signedness, latency, FSM, width, simultaneity.
- Depends on: `P1.4 + P1.6`
- Exit evidence: Operators unit-tested; mutation metadata records operator/severity/source.

### P2.5 — Equivalent-mutant filter and severity
- Deliverable: Run equivalence/behavioral checks, discard no-op mutants, mark critical classes.
- Depends on: `P2.4`
- Exit evidence: Equivalent mutants excluded; critical-class rules reproducible.

### P2.6 — Lineage, dedup and decontamination
- Deliverable: family/lineage/task/variant IDs; text + structural dedup; benchmark/gold isolation.
- Depends on: `P2.1 + P2.2`
- Exit evidence: Near-copy fixtures stay in one split; final-eval lineage cannot export to train.

### P2.7 — Code-first task admission
- Deliverable: Reference-behavior authority mode, scoped equivalence labels, silver admission records.
- Depends on: `P2.2 + P2.5 + P2.6`
- Exit evidence: Admitted task has TaskManifest, evidence and reproducible gold check.

### P2.8 — Difficulty profiling and first human audit
- Deliverable: K-attempt baseline profiler; audit sample; false-accept/false-reject bookkeeping.
- Depends on: `P2.7`
- Exit evidence: Audit produces measured label-quality estimate; task difficulty stored, not guessed.

### P2.G — Phase gate
- Deliverable: Integrated P2 review.
- Depends on: `P2.1-P2.8`
- Exit evidence: Real tasks compile with gold present; lineage/rights complete; equivalence scope explicit; human audit complete. Master volume targets (~500 round-trip + ~500 mutation) remain estimates, not excuses to lower quality.
