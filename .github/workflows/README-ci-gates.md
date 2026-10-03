# Recommended CI Gates

The PR fast gate is implemented in `ci.yml`. The other tiers are added by the tasks that create the components they test.

## PR fast gate
- formatting/lint (`ruff`)
- static typing (`mypy --strict`, per ADR-0001)
- unit + schema/contract tests (`pytest`)
- documentation link/structure checks
- secret scan
- dependency/license delta check

## Component integration gate
Triggered by path ownership:
- tool adapter golden logs and canary HDL;
- controller replay/recovery;
- evaluator self-tests/mutation smoke;
- schema migration compatibility;
- architecture import-boundary checks.

## Protected/main gate
- affected end-to-end frozen fixtures;
- deterministic replay;
- packaging/container build;
- migration dry run where applicable.

## Scheduled/nightly
- full tool capability matrix;
- expensive mutation/formal qualification;
- container/dependency vulnerability scan;
- final-eval leakage canaries;
- reproducibility/flakiness report.
