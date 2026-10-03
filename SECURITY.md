# Security and Integrity Policy

Sindri executes model-generated HDL, Python test code, build scripts, and repository content. Treat all generated/external code as untrusted.

## Non-negotiable controls
- sandbox execution with no network by default;
- least-privilege filesystem mounts;
- protected hidden evaluator and reward workspaces;
- secrets never mounted into model-controlled workspaces unless a narrowly approved action requires them;
- tool profiles are immutable/versioned during a run;
- final evaluator/reward code is outside solver write paths;
- logs, prompts, traces, retrieval caches, and model memories respect customer/eval/data-split boundaries;
- artifacts are content-addressed and provenance recorded;
- candidate code cannot declare its own PASS or alter the authoritative status channel.

## Secrets
Use an approved secret manager or CI secret store. Never commit keys, tokens, private URLs, PDK credentials, or commercial-tool credentials. `.env` files are local only and ignored.

## Dependency/security scans
CI should include secret scanning, Python dependency audit, container scan, and license review for new dependencies.

## Reporting
Security/integrity findings that could allow evaluator tampering, data leakage, or false acceptance are release blockers.

## Evaluator self-test threat checklist
Every judge/evaluator change must keep these attacks failing: test never ran; early exit / `$finish`; printed fake PASS; wrong candidate compiled; stale cached result; silently dropped assertion; changed formal assumption; timeout reported as pass; `ifdef SYNTHESIS`/`VERILATOR`/`FORMAL` divergence; writes outside the candidate tree; references to testbench hierarchy or hidden test names; hidden-test content in solver-visible messages.
