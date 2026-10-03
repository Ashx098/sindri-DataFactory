# Sindri Engineering Principles

These are repository invariants. A pull request that violates one requires an accepted architecture decision record (ADR) or must not merge.

1. **Agents propose; deterministic tools observe; approved policy accepts.** Model text is never acceptance evidence by itself.
2. **No self-certification by agreement.** Multiple models agreeing is not independent evidence.
3. **Disagreement becomes an experiment.** Prefer a test, assertion, counterexample, mutant, or trace question over more discussion.
4. **Authority is separated.** Solver code cannot mutate hidden evaluators, reward code, tool profiles, or acceptance policy.
5. **Every result belongs to exact immutable inputs.** Candidate, task, tool image, configuration, assumptions, and evaluator version are part of identity.
6. **Ambiguity is a valid outcome.** The system may stop with REVIEW_REQUIRED, INVALID_TASK, or INCONCLUSIVE rather than guess.
7. **Correctness gates optimization.** PPA, style, cost, or coverage cannot compensate for wrong behavior.
8. **Training data is admitted, not merely generated.** Provenance, rights, lineage, evidence, and split integrity are mandatory.
9. **Split by semantic lineage before descendants exist.** Near-copies, mutations, paraphrases, and parameter variants stay with their parent split.
10. **The evaluator is production software.** It is versioned, mutation-qualified, false-rejection-tested, and requalified after relevant changes.
11. **The oracle side may use specialist swarms; the default solver remains deployment-shaped.** Multi-agent solving is an experiment until it wins at matched budget.
12. **Durable state lives in structured records.** Chat transcripts, summaries, and model memory are convenience, never authority.
13. **Build the smallest architecture that preserves the invariants.** Prefer a modular monolith and replaceable adapters over premature services.
14. **Every architecture decision must be discoverable from the repository.** Decisions made only in meetings or chats do not exist until recorded.
15. **A change is not done until code, tests, schemas, and affected documentation agree.**
16. **Measure label precision; never assume it.** "Verified" is a number: a human audits a random sample of every batch, and the measured false-accept rate (with confidence interval) ships with every dataset. *(Restored from master architecture §4 by ADR-0003.)*
17. **Independence comes from information hiding and diversity, not personas.** The reference-model and test authors never see golden or candidate RTL; the solver never sees hidden tests; judges see blinded A/B traces; different roles use different model families where possible. *(Restored from master architecture §4 by ADR-0003.)*
