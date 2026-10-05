# FIFO contract — engineering seed v1

- Contract ID: `ct_fifo_seed_v1`
- Status: `engineering-seed-approved` (approved for development use; coordinator, PR #33)
- Certification: `uncertified` (P1.6 authority certification requires RTL/DV/formal review)
- Authority mode: `engineering_intent`. This contract and requirements R01–R09 are the authority.
  `rtl/fifo_ref.v` is one correct witness, not golden behaviour.
- Identity: `TaskManifest.approved_contract_hash` and `EvaluationPolicy.contract_hash` are the
  `sindri.core.ids.content_id` of the exact bytes of this file. Any edit is a new contract revision.

## Interface
A single-clock synchronous FIFO with parameters `WIDTH >= 1` and `DEPTH >= 1`. Any integer depth is
allowed, including non-power-of-two depths. Ports: `clk`, `rst`, `in_valid`, `in_ready`,
`in_data[WIDTH-1:0]`, `out_valid`, `out_ready`, `out_data[WIDTH-1:0]`, `full`, `empty`.

## Semantics
- **Handshake (F1).** A push happens at a rising edge of `clk` when `in_valid && in_ready`. A pop
  happens at a rising edge when `out_valid && out_ready`.
- **Reset (F2).** `rst` is synchronous and active-high. The environment holds it across at least one
  rising edge. Stored data is not reset and is unobservable while `out_valid = 0`.
- **Backpressure at full (F3).** `in_ready = !full`. A full FIFO accepts no push, even when a pop
  happens in the same cycle. There is no combinational path from `out_ready` to `in_ready`.
- **No fall-through (F4).** A word pushed into an empty FIFO is visible on `out_valid`/`out_data`
  from the following cycle.
- **Language (F6).** The RTL (`rtl/`, `mutants/`) uses a synthesizable Verilog-2005 subset. The
  testbenches (`tb/`, `known_bad/`) use Verilog-2005 simulation constructs (`initial` blocks,
  delays, tasks, `$display`, `$finish`) and are not synthesizable. This is a compatibility choice
  for the seed, not a project-wide restriction.

## Requirements (engineering-seed v1; all mandatory, disposition `approved`)
Each requirement has an explicit anchor (`#r01` … `#r09`) that the Requirement records cite as
`source_ref`.

<a id="r01"></a>
### R01 — Reset state
After reset the FIFO is empty and not full, with `out_valid = 0` and `in_ready = 1`.

<a id="r02"></a>
### R02 — Ready/valid flags
After reset, `in_ready == !full` and `out_valid == !empty` at all times.

<a id="r03"></a>
### R03 — Order
Accepted words are popped in exactly the order they were accepted.

<a id="r04"></a>
### R04 — Full and empty
`full` holds iff occupancy equals `DEPTH`; `empty` holds iff occupancy is 0.

<a id="r05"></a>
### R05 — Push while full
A push attempted while full is rejected and has **no effect of its own** (F3). An independently
accepted pop in the same cycle still performs its normal state transition. The rejected push does
not make the rest of the state "unchanged".

<a id="r06"></a>
### R06 — Pop while empty
A pop attempted while empty is rejected and has **no effect of its own**. An independently accepted
push in the same cycle still performs its normal state transition. The rejected pop does not make
the rest of the state "unchanged".

<a id="r07"></a>
### R07 — Simultaneous push and pop
A simultaneous push and pop, when neither full nor empty, keeps occupancy and order.
Mathematical rule: applies when `DEPTH >= 2` (at `DEPTH = 1` a push and a pop can never both be
enabled). Record encoding over the finite seed matrix: `DEPTH in {2, 3, 4, 8}`. Adding a new depth
needs a Requirement and Policy revision.

<a id="r08"></a>
### R08 — Stall stability
While `out_valid && !out_ready`, `out_data` holds its value.

<a id="r09"></a>
### R09 — No fall-through
A push into an empty FIFO becomes visible on the next cycle (F4).

## Parameter matrix (engineering-seed v1)
`(WIDTH, DEPTH)` ∈ {(8,4), (8,3), (32,8), (1,2), (8,1)}. The non-power-of-two depth 3 is required
(mutant M2 is equivalent at every power-of-two depth), and `DEPTH = 1` is an edge case where R07 is
inapplicable.

## Result protocol (F7)
For each configuration, `tb/tests.json` lists the exact expected test IDs. A transcript is PASS only
if all of the following hold; anything else fails closed:
- each expected `TEST <id> PASS|FAIL` line appears exactly once;
- there is no unexpected or duplicate test ID;
- every line that looks like a protocol line (it starts with `TEST` or `RESULT`) matches the exact
  grammar;
- exactly one terminal `RESULT PASS|FAIL` line appears;
- every expected test is PASS, and the final RESULT agrees with the per-test results.

The testbench ends with `$finish` after both `RESULT PASS` and `RESULT FAIL`. The process exit code
is never the semantic oracle.

**Boundary: completeness and consistency, not provenance.** F7 proves that a transcript is complete
and internally consistent. It does **not** prove who wrote it. An untrusted candidate that prints
the whole expected `TEST … PASS` set plus `RESULT PASS` and stops the simulation is
indistinguishable to a stdout-only parser. P1.4/P1.7 must close this, before the judge claims
anti-spoof security, with candidate-integrity restrictions and/or an out-of-band, authenticated
harness result channel. This is a hard follow-up, not a property of this seed.
