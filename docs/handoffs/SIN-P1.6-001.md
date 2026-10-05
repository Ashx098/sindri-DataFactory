# SIN-P1.6-001 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-05
- Agent / person: coding agent (Claude Code)
- Branch/worktree: `feat/SIN-P1.6-001-fifo-seed` at `../worktrees/SIN-P1.6-001`
- HEAD commit: the commit that adds this file
- Base commit: `20e21e3` (`main`; READY via PR #33, narrative PR #34). PR #33 coordinator comment `5991739339` re-read before starting.
- Dirty files, if any: none after commit

## Completed
- `evals/fixtures/fifo/`: the FIFO **engineering seed v1**, approved for development use and **uncertified**. It contains:
  - the contract (F1–F7, R01–R09, matrix, protocol), whose bytes are the contract hash;
  - reference and alternate-correct RTL;
  - the 4-state strict testbench and the configuration-scoped inventory;
  - M1–M5 and their manifest with the kill matrix;
  - the quarantined X-blind known-bad testbench and its manifest;
  - 22 P1.1 records: base `use_case` task and M4 mutation-debug task, each with R01–R09 and a policy.
- Tests:
  - `tests/contract/test_fifo_seed_records.py`: 12 pure checks;
  - `tests/eda/_protocol.py`: the F7 verdict;
  - `tests/eda/test_protocol.py`: 12 pure checks;
  - `tests/eda/test_fifo_seed_icarus.py`: 71 `eda` checks that reproduce the kill matrix and the known-bad verdicts.

## Verified
| Command / check | Result |
|---|---|
| `uv run ruff check .`, `uv run mypy` | pass |
| `uv run pytest -q` (local, Icarus 12.0) | 2003 passed, 8 skipped |
| `uv run pytest -q -m eda tests/eda` | 71 passed |
| `tests/eda` without `iverilog` on PATH | 12 passed, 71 skipped (the CI situation) |
| `check_records` over the 22 seed records | `()` |
| `git diff --stat origin/main -- src/` | empty |

The kill matrix reproduces exactly:
- M1 and M4 are killed in all 5 configurations.
- M2 survives at the power-of-two depths (8,4), (32,8) and (1,2).
- M3 and M5 survive at (8,1).

The X-blind testbench fake-PASSes M4 in all 5 configurations.

## Decisions
None new. F1–F12 and the PR #33 record clarifications are implemented as decided: approved-but-uncertified, R07 exact `DEPTH ∈ {2,3,4,8}`, configuration-scoped inventory, quarantine.

## Implementation notes for review
- **X-blind testbench:** it must turn *every* `===` into `==`. Only two X-blind lines did not reproduce the fake PASS, because the strict testbench's other checks use `===`. A test pins the exact mechanical transform.
- **Rights and split:** `split: dev`, internal licence ref, `training_allowed: false`. Revisable by the coordinator.
- **Placeholder profile IDs:** `tp_icarus12_compile` / `tp_icarus12_sim`; there are no profile records yet.

## Open questions
None.

## Blocked on
- Coordinator review and merge.

## Next after approval
- **P1.3:** pinned Icarus 12.x profile; Verilator 5.x and slang re-probe before P1.4 normalizers are considered stable.
- **G-B ADR:** must merge before any P1.4 code mints `ObservationId`s.
- **P1.4:** the adapter must implement at least `tests/eda/_protocol.py`'s rules.
- **Certification (later P1.6 task):** blocked on the RTL/DV/formal reviewer.

## Do not start
- P1.3/P1.4/P1.2 or any adapter, sandbox, store, controller or judge code.
- Certification work.
- Tool installs or pulls.

## Risks / things not to change casually
- **Contract edits:** editing `contract/contract.md` changes its hash. Records must be re-issued as a new revision, not edited in place; the test fails on mismatch.
- **Positive testbench path:** keep `known_bad/` out of `tb/`. Discovery of positive testbenches is `tb/*.v` only.
- **Inventory changes:** adding a test to the testbench requires adding it to `tests.json` with its requirement mapping. The consistency tests enforce this.
