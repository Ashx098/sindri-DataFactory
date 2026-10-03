# Release Process

## Versioned things
Version independently where needed:
- repository/software release;
- schemas;
- task contracts;
- evaluation policies/evaluators;
- agent cards/prompts;
- tool container images/profiles;
- exported datasets;
- trained model checkpoints.

## Release gate
A release requires:
- clean CI for applicable tiers;
- no unresolved security/integrity blocker;
- migration/replay plan for schema/state changes;
- updated docs and changelog/release notes;
- pinned dependency/tool versions;
- reproducible build metadata;
- owner approval for acceptance-critical changes.

Do not reuse old evaluator evidence after evaluator, assumptions, tool image, candidate, or contract inputs change outside the documented compatibility policy.
