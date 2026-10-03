# SIN-P1.4-003 — Verilator lint adapter

## Phase identity
- Phase: `P1`
- Subphase: `P1.4`
- Architecture version: `master-architecture-v1`

## Outcome
`lint(candidate)` returns a schema-validated Observation with semantic status and immutable input identity.

## Dependencies
- P1.1 Observation/status schema complete
- P1.3 sandbox runner complete

## Scope / allowed paths
- `src/sindri/tools/verilator/**`
- `tests/tools/verilator/**`
- `docs/tools/verilator.md`

## Non-goals
- simulation adapter
- SBY/formal adapter
- generic model/agent runtime
- future tool-registry refactor

## Acceptance
- [ ] warnings/errors normalize through golden-log fixtures
- [ ] unsupported canary => UNSUPPORTED
- [ ] timeout/crash never => PASS
- [ ] Observation includes candidate/tool/profile hashes
- [ ] docs and tests updated
