# Verification Forge-specific rules
- Clean-room boundary (master architecture §11.2): testplan, reference-model, stimulus, scoreboard and property authors work from the contract/spec only. No code path in this package may place golden or candidate RTL in their context. Structural checks that need RTL belong to the judge/qualifier, not to oracle authors.
- Every requirement must map to explicit verification obligations or an explicit NOT_APPLICABLE/UNSUPPORTED disposition.
- Coverage is evidence of exercised scenarios, not proof of checking quality.
- Assumptions come from approved contract/environment policy, not from candidate convenience.
- Every suite must be qualified with known-good, alternative-correct, realistic mutant, and anti-hacking controls before it can grade training/evaluation data.
