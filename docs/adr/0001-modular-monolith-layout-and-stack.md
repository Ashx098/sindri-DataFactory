# ADR-0001: Modular monolith layout and V1 stack

- Status: proposed (prepared by coding agent; awaiting architecture-owner review)
- Date: 2026-10-03
- Owners: platform lead
- Supersedes: master architecture §21.1 layout and the "Python 3.11+" row of §21.2

## Context
The master architecture (§21) and the repository constitution (§2–3) describe slightly different
layouts and Python versions. Master §21.1 uses top-level `foundation/`, `gate/`, `exporter/`;
the constitution places everything under `src/sindri/` with `qualification/` and `data/`. Master
specifies Python 3.11+, the constitution 3.12+. Leaving both alive invites agents to "fix" one
toward the other.

## Decision
- One Python package `sindri` under `src/` (src layout), packages as listed in
  `ARCHITECTURE_GUARDRAILS.md` and `docs/REPO_MAP.md`.
- Name mapping from master §21.1: `foundation/{gateway,runners}` → `tools`, `foundation/store` →
  `evidence`, `foundation/controller` → `controller`, `foundation/blackboard` → `evidence`
  (findings table) until it needs its own package, `foundation/models` → `models`, `gate` →
  `qualification`, `exporter` → `data`.
- Python ≥ 3.12, managed with `uv` and a committed `uv.lock`.
- Stack per constitution §2.1: Pydantic v2, FastAPI + Typer, PostgreSQL (SQLite for the local pilot),
  content-addressed filesystem → S3/MinIO, Parquet + DuckDB/Polars, Docker, provider-neutral model
  gateway, OpenTelemetry, MkDocs + Mermaid, pytest + Hypothesis. Lint/type: ruff + mypy strict.
- Dependency direction enforced by `tests/architecture/test_import_boundaries.py`.

## Alternatives considered
### Keep master §21.1 top-level packages
Pro: matches the component chapters 1:1. Con: no src layout (import-path accidents), and the
constitution's dependency table is written against the `src/sindri` names.
### Early microservices
Rejected by principle 10: network contracts and deploy failure modes before behaviour is stable.

## Consequences
Component cards in the master document map to packages via the table above. Services may be
extracted later only after observed scale or isolation need, with a new ADR.

## Validation
Boundary test stays green as packages fill in; no cross-package dict passing in review.

## Follow-up
SIN-P1.1-001 (formerly TASK-0001, see ADR-0003) creates the first schemas inside this layout.
