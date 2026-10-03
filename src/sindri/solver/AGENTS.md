# Solver-specific rules
- The solver must not import, read, search for, or infer hidden evaluator content.
- Only development tools and public task/repository context may be exposed.
- A tool status is trusted only through the typed ToolGateway observation.
- Solver prompts cannot contain final-eval artifacts, even for debugging.
- Candidate edits create a new candidate identity; do not mutate an accepted/frozen snapshot.
- Default topology is one deployment-shaped agent loop. Specialist escalation is feature-gated/experimental unless an accepted ADR changes this.
