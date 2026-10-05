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
- **Language (F6).** The seed RTL and testbench use a synthesizable Verilog-2005 subset. This is a
  compatibility choice for the seed, not a project-wide restriction.

## Requirements (engineering-seed v1; all mandatory, disposition `approved`)
- **R01** After reset the FIFO is empty and not full, with `out_valid = 0` and `in_ready = 1`.
- **R02** After reset, `in_ready == !full` and `out_valid == !empty` at all times.
- **R03** Accepted words are popped in exactly the order they were accepted.
- **R04** `full` holds iff occupancy equals `DEPTH`; `empty` holds iff occupancy is 0.
- **R05** A push attempted while full is not accepted and leaves the state unchanged (F3).
- **R06** A pop attempted while empty is ignored and leaves the state unchanged.
- **R07** A simultaneous push and pop, when neither full nor empty, keeps occupancy and order.
  Mathematical rule: applies when `DEPTH >= 2` (at `DEPTH = 1` a push and a pop can never both be
  enabled). Record encoding over the finite seed matrix: `DEPTH in {2, 3, 4, 8}`. Adding a new depth
  needs a Requirement and Policy revision.
- **R08** While `out_valid && !out_ready`, `out_data` holds its value.
- **R09** No fall-through: a push into an empty FIFO becomes visible on the next cycle (F4).

## Parameter matrix (engineering-seed v1)
`(WIDTH, DEPTH)` ∈ {(8,4), (8,3), (32,8), (1,2), (8,1)}. The non-power-of-two depth 3 is required
(mutant M2 is equivalent at every power-of-two depth), and `DEPTH = 1` is an edge case where R07 is
inapplicable.

## Result protocol (F7)
For each configuration, `tb/tests.json` lists the exact expected test IDs. A transcript is PASS only
if all of the following hold; anything else fails closed:
- each expected `TEST <id> PASS|FAIL` line appears exactly once;
- there is no unexpected or duplicate test ID;
- exactly one terminal `RESULT PASS|FAIL` line appears;
- every expected test is PASS, and the final RESULT agrees with the per-test results.

`$fatal` signals a testbench-declared failure, but the process exit code is never the semantic
oracle.
