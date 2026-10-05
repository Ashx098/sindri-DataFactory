# FIFO authority package — engineering seed v1

**Status: `engineering-seed-approved` for development use. Certification: `UNCERTIFIED`.**
This seed drives the P1 vertical slice (SIN-P1.6-001). It does **not** complete P1.6.

| | Engineering seed (this directory) | Authority certification (later, blocked) |
|---|---|---|
| Who | coding agent + coordinator | coding agent + **RTL/DV/formal reviewer** (unassigned) |
| Contract | `contract/contract.md`, v1, approved for development use, uncertified | reviewed and certified revision with a new hash |
| Implementations | `rtl/fifo_ref.v` and `rtl/fifo_alt.v` (independent structure) | both reviewed, including the alternate's independence |
| Mutants | M1–M5 (`mutants/`), different bug classes, kill matrix recorded, uncertified | 15–20 critical mutants, each classified with reviewer sign-off |
| Testbench | `tb/tb_fifo.v`: directed, self-checking, 4-state strict, F7 protocol | reviewed coverage; formal properties where applicable |
| Use | drives the vertical slice; may be revised after real-tool contact | required before P1.6 is complete and before P1.7 exit claims |

## Layout
- `contract/contract.md` — semantics F1–F7, requirements R01–R09, parameter matrix and result protocol. Its bytes are the contract hash.
- `rtl/` — the two correct implementations (module `fifo`, Verilog-2005).
- `tb/tb_fifo.v` — the strict testbench. `tb/tests.json` gives the configuration-scoped expected test inventory.
- `mutants/` — M1–M5 and `manifest.json` (bug class, defect, violated requirements, kill matrix, uncertified equivalence notes).
- `known_bad/` — **quarantined**. `tb_fifo_xblind.v` is an X-blind testbench that fake-PASSes M4; `manifest.json` gives its expected verdicts. It is never part of the positive path. P1.7 uses it as an anti-fake-PASS fixture.
- `records/` — P1.1 records:
  - `fifo_seed/`: base task (`use_case`), R01–R09 and the policy;
  - `fifo_seed_m4/`: a mutation-debug task for M4, with its requirements and policy.

## F7 boundary (read before trusting a PASS)
The F7 protocol gives **completeness and consistency, not provenance**. A candidate that prints the
whole expected `TEST … PASS` set plus `RESULT PASS` and stops the simulation would spoof a
stdout-only parser. P1.4/P1.7 must add candidate-integrity restrictions and/or an out-of-band,
authenticated harness result channel before the judge claims anti-spoof security.

## Reproduce (Icarus Verilog 12.0; no other tool is required)
```bash
uv run pytest -q tests/eda          # skipped automatically when iverilog is not installed
```
A single run by hand:
```bash
iverilog -g2005 -Wall -Ptb.WIDTH=8 -Ptb.DEPTH=3 -o /tmp/f.vvp tb/tb_fifo.v rtl/fifo_ref.v && vvp -n /tmp/f.vvp
```
