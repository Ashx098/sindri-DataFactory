# Repository Testing Strategy

The factory itself must be tested as aggressively as the RTL it evaluates.

## Test layers
1. **Unit** — hashes, permissions, state transitions, parsers, budget accounting, pure domain rules.
2. **Schema/contract** — serialization, compatibility, rejected invalid inputs, version migrations.
3. **Property** — invariants such as idempotency and invalidation rules where generative testing helps.
4. **Golden-log** — recorded tool outputs map to stable semantic statuses.
5. **Canary HDL** — tiny SV programs exercise every claimed tool capability on upgrades.
6. **Integration** — store/controller/tool/model interfaces with controlled fixtures.
7. **Replay/recovery** — process death during each state, pending-job recovery, cache correctness.
8. **Evaluator self-test** — fake PASS, skipped test, early finish, stale candidate, dropped assertion, changed assumption, timeout-as-pass, simulation/synthesis divergence attacks.
9. **Mutation qualification** — realistic family-specific faults plus alternative-correct designs.
10. **Leakage/security** — final-eval canaries, permission boundaries, sandbox escapes, secret handling.
11. **Governance consistency** — task board ↔ packets ↔ phase state agree; import boundaries hold (`tests/unit/test_governance.py`, `tests/architecture/`).
12. **End-to-end** — one frozen task from source through qualification, solve, judge, export, replay.

## CI tiers
- PR fast gate: format/lint/type/unit/schema/security-basics/docs checks.
- Component integration gate: affected integration/golden/canary tests.
- Protected-branch gate: replay, architecture-boundary, evaluator regressions as applicable.
- Scheduled/nightly: broad tool matrix, expensive formal/mutation, dependency/container scans.

Flaky acceptance-critical tests block automatic labels until explained and fixed.
