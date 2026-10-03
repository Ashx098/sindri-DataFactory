# Third-Party Dependency Policy

Every significant dependency must answer:
- what exact capability it provides;
- why building a small internal abstraction is insufficient;
- license and training/data-use implications;
- whether it owns authoritative state or only implements an adapter;
- how it is sandboxed/isolated;
- upgrade and rollback strategy;
- maintenance health and security posture;
- replacement path.

Agent frameworks are evaluated behind replaceable interfaces. No generic agent framework may own Sindri's workflow state, evidence model, hidden evaluator, permissions, or task lineage.

Pin production dependencies through the package lockfile and container image digests. Update deliberately with compatibility/canary tests.

## Current dependency register

| Dependency | License | Scope | Behind interface |
|---|---|---|---|
| pydantic v2 | MIT | runtime (`schemas`) | boundary records |
| pytest, hypothesis, ruff, mypy, pyyaml | MIT / MPL-2.0 / MIT / MIT / MIT | dev only | n/a |

Planned EDA images (pinned by digest when P1.4 adds them): Verilator 5.x, Icarus Verilog, Yosys + yosys-slang, SymbiYosys, EQY, cocotb 2.x.
