# Sindri Implementation Plan

This is the normative sequencing companion to the Canonical Master Architecture. It does **not** replace the architecture. The master defines *what* Sindri is; this plan defines *what may be built next*.

## Core execution rule
Agents never “build a phase.” They implement one bounded TASK-ID with explicit dependencies, allowed paths, acceptance tests and non-goals. A phase completes only through a separate gate review.

## Anti-skeleton rule
Do not scaffold future phases. No empty services/classes, TODO-only modules, or broad placeholder trees unless an approved interface task specifically requires one. Prefer one executable vertical slice over broad unverified structure.

## Phase state authority
`implementation/current.yaml` is the only authoritative record of the active phase and phase/gate
states (ADR-0003). `implementation/task_board.yaml` is the only authoritative task status list.
Markdown documents point to them and must not restate their values.

## Canonical phases

### B0 — Bootstrap (not an architecture phase)
- B0.1 Governance installation
- B0.2 Text-native master architecture
- B0.3 Working tasking and handoff tooling
- B0.4 Fast CI gate
- B0.5 First P1 task packet
- B0.G Gate

### P1 — Foundation and Judge v0
- P1.1 Core schemas / IDs / status taxonomy
- P1.2 Artifact identity / evidence store
- P1.3 Sandbox / execution substrate
- P1.4 Tool Gateway v0 / capability matrix
- P1.5 Controller v0 / budgets / invalidation / recovery
- P1.6 FIFO authority package / goldens / mutants
- P1.7 Judge v0 / evaluator self-tests
- P1.8 End-to-end FIFO episode / repair / replay
- P1.G Gate

### P2 — Code-first and mutation sources
- P2.1 Rights/source registry
- P2.2 Repo miner / elaboration / task cutting
- P2.3 Git-history feature/fix tasks
- P2.4 Mutation operators
- P2.5 Equivalent-mutant filter / severity
- P2.6 Lineage / dedup / decontamination
- P2.7 Silver task admission
- P2.8 Difficulty profiler / human audit
- P2.G Gate

### P3 — Spec Forge
- P3.1 Fact Sheet
- P3.2 Authority / contract compiler
- P3.3 Spec writers / linter
- P3.4 Equivalence-miter engineering
- P3.5 Reconstructors
- P3.6 Ambiguity hunters
- P3.7 Trace interrogation / resolver
- P3.8 Leakage / certificate
- P3.9 Planted-ambiguity calibration
- P3.G Gate

### P4 — Verification Forge
- P4.1 VerificationPlan / requirement-obligation matrix
- P4.2 Reusable DV library
- P4.3 Clean-room reference-model path
- P4.4 Directed stimulus / scoreboard
- P4.5 Constrained-random / coverage
- P4.6 Properties / formal / assumption audit
- P4.7 Equivalence harness generation
- P4.8 Suite qualifier / mutant kill loop
- P4.9 Development-hidden split / anti-hacking
- P4.10 EvaluatorCertificate / 3-family qualification
- P4.G Gate

### P5 — Solver, Exporter and Deciding Experiment
- P5.1 Model gateway / minimal agent runtime
- P5.2 Hardware-native ACI / minimal repo intelligence
- P5.3 Deployment-shaped solver
- P5.4 Failure triage / repair
- P5.5 Episode recorder
- P5.6 Dataset exporter
- P5.7 SFT baseline
- P5.8 Pre-register held-out experiment
- P5.9 Run matched-budget arms
- P5.10 Go/no-go
- P5.G Gate

### P6 — RL Environment and Flywheel
- P6.1 RL environment API
- P6.2 Sealed reward/verifier service
- P6.3 Async rollouts
- P6.4 Curriculum / difficulty
- P6.5 Failure miner
- P6.6 First RL round
- P6.7 Held-out + verification regression
- P6.8 Scale decision
- P6.G Gate

## Change control
Changing a canonical phase objective, authority boundary, solver topology or phase gate requires an ADR/RFC and an update to the Canonical Master Architecture. Subphase sequencing may be changed by the coordinator if the phase objective and gate remain intact; record the change in PROJECT_STATE and this plan.
