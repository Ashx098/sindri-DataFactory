# Repository Map

Where responsibilities live **today**. Keep synchronized with structural changes. Packages under
`src/sindri/` are created by the task that first needs them (anti-skeleton rule); the planned set
and their import rules are fixed in `ARCHITECTURE_GUARDRAILS.md`.

```text
sindri-DataFactory/
  PRINCIPLES.md  AGENTS.md  ARCHITECTURE_GUARDRAILS.md  README.md
  CONTRIBUTING.md  SECURITY.md  THIRD_PARTY.md  pyproject.toml  uv.lock
  .github/
    workflows/ci.yml             PR fast gate (ruff, mypy, pytest)
    workflows/README-ci-gates.md planned CI tiers
    PULL_REQUEST_TEMPLATE.md  CODEOWNERS
  implementation/
    current.yaml                 AUTHORITATIVE active phase + phase/gate states
    task_board.yaml              AUTHORITATIVE task status
    phase_graph.yaml             phase dependencies
  docs/
    architecture/MASTER_ARCHITECTURE.md   generated from docs/reference/*.docx (+ img/)
    reference/                   source .docx documents (canonical originals)
    implementation/              plan, phases/, gates/, kickoff, dependency graph
    adr/  rfcs/  tasks/  handoffs/
    PROJECT_STATE.md  ROADMAP.md  REPO_MAP.md  DOCUMENTATION_POLICY.md
    MULTI_AGENT_WORKFLOW.md  TESTING_STRATEGY.md  RELEASE_PROCESS.md
  src/sindri/
    core/status.py               shared status taxonomy (ADR-0002)
    core/ids.py                  typed domain IDs, content IDs, canonical JSON hashing
    schemas/                     boundary records: TaskManifest, Requirement, EvaluationPolicy, CandidateManifest, Observation, Finding (more per P1.1 order)
    judge/ solver/ verification_forge/ data/ tools/   local AGENTS.md only (rules bind before code)
  components/component.template.yaml  schemas.yaml
  agents/agent-card.template.yaml
  tests/
    unit/                        IDs/hashing, status taxonomy, governance consistency
    contract/                    record contracts + adapted master-example fixtures
    architecture/                import-boundary enforcement
  scripts/
    agent_bootstrap.py  new_task.py  new_handoff.py  show_ready_tasks.py  docx_to_md.py
```

| Path | Created by | Notes |
|---|---|---|
| `src/sindri/schemas/` (remaining records) | SIN-P1.1-007 | EpisodeState |
| `src/sindri/evidence/` | P1.2 | |
| sandbox / `src/sindri/tools/` | P1.3 / P1.4 | `tool_profiles/` arrives with P1.4 |
| `src/sindri/controller/` | P1.5 | |
| `evals/fixtures/fifo/` | P1.6 | FIFO authority package |
| `src/sindri/judge/` | P1.7 | |

A directory added to `src/sindri/` must have a clear owner, public interface, dependency direction
(listed in the guardrails and the boundary test), tests and documentation.
