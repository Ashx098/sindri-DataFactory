# Trusted Judge-specific rules
- The judge consumes a frozen candidate; it does not coach or repair the solver.
- Hidden tests, references, assumptions, anti-hacking logic, and reward code are protected artifacts.
- Acceptance is a policy over typed observations, never free-form model opinion.
- `TIMEOUT`, `TOOL_ERROR`, `INCONCLUSIVE`, `UNSUPPORTED`, and `FAIL` remain distinct.
- Any evaluator/policy/tool-profile change that affects semantics requires requalification and a new evaluator certificate/version.
- Never route hidden-test diagnostics back into training or solver context unless explicitly designated as development feedback by policy.
