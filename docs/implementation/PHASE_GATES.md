# Phase Gates

Phase gates are integration reviews, not task counts. Coding agents cannot mark a gate complete.

## P1.G
- tool statuses regression-tested;
- hashes/invalidation correct;
- crash/restart restores state;
- FIFO critical mutants all killed;
- alternate correct implementation accepted;
- fake PASS, stale candidate and skipped-test attacks fail;
- replay has no unexplained decision mismatch.

## P2.G
- real repo tasks build with gold present;
- rights and lineage complete;
- equivalence scope explicit;
- first human audit yields measured label-quality estimate.

## P3.G
- at least two certified spec styles;
- planted-ambiguity calibration measured;
- spec-first/no-golden path works;
- authority conflicts quarantine correctly.

## P4.G
- at least three families have qualified evaluators;
- alternative correct designs pass;
- all critical mutants killed or task quarantined;
- assumptions/covers audited;
- development/hidden separation and anti-hacking fixtures pass.

## P5.G
- deployment-shaped single-agent baseline stable;
- complete trajectories/export provenance;
- held-out family frozen before final results;
- SFT compared to base+harness at matched budget;
- go/no-go decision follows preregistered rule.

## P6.G
- reward service sealed and stable;
- one RL round evaluated on held-out family;
- RL shows gain over SFT alone;
- no increase in critical-mutant escapes / evaluator quality regression.
