# tools/AGENTS.md: stricter local rules

- Never infer PASS from an exit code; normalise to `sindri.core.status.ToolStatus` explicitly and verify the
  expected tests/properties actually ran.
- Every adapter: schema + permission validation, fresh sandbox from content hashes, pinned image digest,
  CPU/memory/time/output limits, no network, raw logs stored by reference.
- Every adapter change ships golden-log tests (PASS/FAIL/TIMEOUT/TOOL_ERROR/UNSUPPORTED) and canary HDL fixtures.
- Never build shell commands from untrusted strings.
- Cache keys include the complete semantic input tuple; a partial-key hit is a bug.
