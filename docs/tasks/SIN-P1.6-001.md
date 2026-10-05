# SIN-P1.6-001 — Minimal FIFO authority seed for the first vertical slice

## Phase identity
- Phase: `P1`
- Subphase: `P1.6` (first task; it does **not** complete P1.6)
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
A small, real hardware **engineering seed** under `evals/fixtures/fifo/` that the P1 vertical slice
(P1.3 → P1.4 → P1.2 → P1.5 → P1.7 → P1.8) can drive. It contains:
- one parameterized synchronous FIFO with documented semantics;
- a canonical reference RTL and an independently written alternate-correct RTL;
- a minimal machine-readable contract/requirements draft expressed in P1.1 records where possible;
- a directed self-checking testbench;
- 3–5 meaningful mutants of different bug classes, each with a recorded kill matrix.

It is explicitly **not certified**. P1.6 authority certification (the reviewed contract, a 15–20
critical-mutant set, and classification of every mutant) stays blocked on the RTL/DV/formal reviewer.

## Why / architecture references
- `docs/implementation/phases/P1_FOUNDATION_AND_JUDGE_V0.md` §P1.6: a reviewed FIFO contract, two correct implementations, a fixed parameter matrix, known-bad fixtures and 15–20 reviewed critical mutants. It depends on P1.1.
- P1.1-G "Post-gate execution strategy" (`docs/tasks/SIN-P1.1-010.md`): one real FIFO through real tools before broadening abstractions.
- `docs/PROJECT_STATE.md` risk: RTL/DV reviewer roles are unassigned, and P1.6 certification cannot complete without them.
- `docs/REPO_MAP.md`: `evals/fixtures/fifo/` is created by P1.6.
- AGENTS.md §3 (never infer PASS from exit code; TOOL_ERROR/TIMEOUT/INCONCLUSIVE/UNSUPPORTED/FAIL are distinct) and ADR-0002.

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned 2026-10-05
- Integrator: Avinash
- Reviewers: Avinash (engineering); **RTL/DV/formal reviewer: unassigned** (required only for certification)

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged and marked ready (drafted against `7a09c90`)
- Worktree: `../worktrees/SIN-P1.6-001`

## Dependencies
- Required: P1.1 complete (SIN-P1.1-001…010 verified; P1.1-G approved).
- **None of P1.2–P1.5.** The seed is pure fixture data, plus tests that validate the record drafts with the P1.1 models.

## Two tracks
| | **Engineering seed (this task)** | **Authority certification (later P1.6 task, blocked)** |
|---|---|---|
| Who | coding agent + coordinator | coding agent + **RTL/DV/formal reviewer** |
| When | now | after a reviewer is assigned |
| Contract | **engineering-seed v1 approved for development use** (F1–F7), explicitly `uncertified`; revisioned if real-tool/DV evidence changes it | reviewed, signed-off/certified contract; `approved_contract_hash` refers to the certified revision |
| Implementations | reference + alternate-correct, both passing the seed testbench | both reviewed; the alternate also reviewed for independence |
| Mutants | 3–5 meaningful, different bug classes, a recorded kill matrix, labelled `seed`/`uncertified` | 15–20 critical mutants, each classified (killed/equivalent/out-of-scope) with reviewer sign-off |
| Testbench | directed, self-checking, 4-state strict | reviewed coverage and expected-behaviour review; formal properties where applicable |
| Use | drives the vertical slice; may be revised | required before P1.6 is declared complete and before P1.7 may claim "rejects predefined critical defects" |
| Labels | every file and record says `engineering seed — uncertified` | `certified` only after review |

## Draft FIFO semantics (for coordinator decision; F-rows below)
- **Interface:** `clk`, `rst`, `in_valid`/`in_ready`/`in_data[WIDTH]`, `out_valid`/`out_ready`/`out_data[WIDTH]`, `full`, `empty`.
- **Handshake:** valid/ready on both sides (F1). A push happens on a rising edge when `in_valid && in_ready`; a pop when `out_valid && out_ready`.
- **Reset:** synchronous, active-high `rst` (F2). The reset must be held for ≥ 1 rising edge. After reset: `empty=1`, `full=0`, `out_valid=0`, `in_ready=1`. Stored data is not reset and is not observable.
- **Flags:** `in_ready == !full`, `out_valid == !empty`, `full ⇔ occupancy == DEPTH`, `empty ⇔ occupancy == 0`.
- **Overflow:** a push attempted while full is not accepted (backpressure); state is unchanged. **In particular, no push is accepted when full, even if a pop happens in the same cycle** (F3).
- **Underflow:** a pop attempted while empty is ignored; state is unchanged.
- **Simultaneous push + pop** (neither full nor empty): occupancy is unchanged, and order is preserved.
- **Visibility:** there is no fall-through. A word written into an empty FIFO is first visible on `out_*` in the next cycle (F4). `out_data` is the oldest word whenever `out_valid=1`, and it is **unspecified** when `out_valid=0`.
- **Stall stability:** while `out_valid && !out_ready`, `out_data` holds its value.
- **Parameters:** `WIDTH ≥ 1`, `DEPTH ≥ 1`, any integer. Non-power-of-two depths are allowed (F5).
- **Language:** synthesizable Verilog-2005 subset for RTL and testbench (F6), so the seed runs on Icarus without `-g2012`.

### Requirement semantics (P1.1 `Requirement`)
Coordinator decision on PR #33: R01–R09 are **approved for the engineering-seed v1 development contract** once this planning PR merges, while the entire package remains **uncertified** for P1.6 completion. A later RTL/DV review may create new Requirement/TaskManifest/Policy revisions.
| ID | Normalized semantics (draft) | Applicability |
|---|---|---|
| R01 | After reset: empty, not full, `out_valid=0`, `in_ready=1` | all configs |
| R02 | `in_ready == !full` and `out_valid == !empty` at all times after reset | all |
| R03 | Accepted words are popped in order (FIFO order) | all |
| R04 | `full` iff occupancy == DEPTH; `empty` iff occupancy == 0 | all |
| R05 | A push while full is not accepted, and state is unchanged | all |
| R06 | A pop while empty is ignored, and state is unchanged | all |
| R07 | Simultaneous push and pop keep occupancy and order | prose rule: DEPTH ≥ 2; **record encoding for the current finite matrix:** `parameter_scope DEPTH in {2,3,4,8}`. DEPTH=1 is excluded. A later matrix expansion requires a Requirement/Policy revision. |
| R08 | `out_data` stable while `out_valid && !out_ready` | all |
| R09 | No fall-through: a write to empty is visible the next cycle | all |

### Parameter matrix (proposed `EvaluationPolicy.configurations`)
`(WIDTH, DEPTH)` ∈ {(8,4), (8,3), (32,8), (1,2), (8,1)}. Probe P8 shows that **a non-power-of-two depth is required**: mutant M2 is equivalent at every power-of-two depth. DEPTH = 1 and WIDTH = 1 are edge cases.

## Facts established by read-only tool probes (local machine, 2026-10-05)
The probes used scratch copies of draft RTL, testbench and mutants, outside the repository; nothing was committed.

**Tool inventory**

| # | Finding | Consequence |
|---|---|---|
| P1 | Installed: **Icarus Verilog 12.0 (stable)** (`iverilog`, `vvp`). **Not installed:** Verilator, slang/pyslang, Yosys, SBY, EQY, Verible, svlint. No HDL container images are present locally; Docker is available. | Only Icarus evidence was gathered. The Verilator/slang/Yosys diagnostics the coordinator asked for need tool provisioning, which is decision F8. I did not install or pull anything, because that is outside a read-only probe. |

**Correct implementations**

| # | Finding | Consequence |
|---|---|---|
| P2 | Reference and alternate-correct drafts (different structure: count register vs explicit full/empty flags) **compile and pass** the directed testbench in all 5 configurations. There are no errors; the only message is one timescale-inheritance warning on stderr. | Both controls are feasible now. |

**Compile diagnostics**

| # | Finding | Consequence |
|---|---|---|
| P3 | **Compile diagnostics go to stderr** as `file:line: error: …` / `file:line: warning: …`. A syntax error prints `file:line: syntax error` (no `error:` token) plus `I give up.`. An unknown `-P` parameter prints `:0: error: …` (no file). | The normalizer cannot rely on a single regex; diagnostics may lack a path. P1.1 `Diagnostic` already allows `path: None` and `code: None`; no schema change is needed. |
| P4 | **The `iverilog` exit code equals the number of errors** (syntax error → 2; one bad port → 1; three elaboration errors → 3). | Exit-code *values* carry no category. An adapter may only use "non-zero means compile did not produce an executable" and must parse stderr. |
| P5 | `-Wall` warns about implicit nets but **does not warn about width truncation** (assigning 8 bits to 4 bits is silent). SystemVerilog (`logic`, `always_ff`) **fails without `-g2012`** (exit 3). `` `default_nettype none `` turns implicit nets into errors. | Icarus is a weak lint. A real LINT check needs Verilator or slang (F8). The compile flags (`-g2005` vs `-g2012`, `` `default_nettype none ``) belong in the tool profile. |

**Simulation exit behaviour**

| # | Finding | Consequence |
|---|---|---|
| P6 | Under `vvp`: `$display` output, the `$finish called at …` line, and `ERROR:` / `FATAL:` messages **all go to stdout**. `$error` **exits 0**; `$fatal(1, …)` exits 1. A testbench that prints a fake `RESULT PASS` and finishes early exits 0, and so does one that never calls `$finish`. | This confirms AGENTS §3 and ADR-0002: **simulation PASS can never be inferred from the exit code.** The seed defines an explicit result protocol (F7). Completeness (every expected test reported) is what turns a run into PASS. |

**Reset and X handling**

| # | Finding | Consequence |
|---|---|---|
| P7 | At time 0, before the first reset edge, all state is `x`. Uninitialized memory makes `out_data = x` when empty. **An X-blind testbench (`if (!cond)`) silently passed mutant M4 (read pointer not reset) in all 5 configurations: `out_data = xx` while `out_valid = 1`.** After switching the checks to 4-state strict (`cond !== 1'b1` and `===` on data), M4 is killed in 5/5. | **X-pessimism can produce fake PASS.** The seed testbench must be 4-state strict. This becomes a permanent anti-fake-PASS fixture for P1.7 (an X-blind checker is a known-bad *testbench*). It is a strong argument for a 2-state simulator cross-check (Verilator) later. |

**Mutant kill matrix**

| # | Finding | Consequence |
|---|---|---|
| P8 | Mutant kill matrix with the strict testbench (table below): every mutant is killed in ≥ 1 configuration, and **M2 (read pointer without wrap) is equivalent at power-of-two depths** (4, 8, 2) because natural binary overflow wraps correctly. | The parameter matrix must include a non-power-of-two depth. Mutant classification is **per configuration**, which certification must record. |
| P9 | **M3 (simultaneous push/pop count) and M5 (stale read) are equivalent at DEPTH = 1.** At DEPTH = 1 a push and a pop cannot both be enabled (`in_ready = !full`, `out_valid = !empty`), and the read pointer is always 0. | R07 is inapplicable at DEPTH = 1 (applicability scope). This is real evidence for `Requirement.applicability`. |

**Performance and determinism**

| # | Finding | Consequence |
|---|---|---|
| P10 | Simulation is deterministic: three runs gave byte-identical stdout (same sha256). Compile and simulation each take < 0.01 s and about 8 MB RSS per configuration. Timing printed in the `$finish` line depends on `timescale`. | This is cheap enough for every-push CI once a pinned Icarus exists in CI. Replay equality is feasible at the stdout level, but the `timescale` must be fixed in the profile. |

### Mutant kill matrix (draft mutants of the reference; 4-state strict testbench)
| Mutant | Bug class | (8,4) | (8,3) | (32,8) | (1,2) | (8,1) |
|---|---|---|---|---|---|---|
| M1 `full = (count == DEPTH-1)` | off-by-one full/empty | killed | killed | killed | killed | killed |
| M2 `rd_ptr <= rd_ptr + 1` (no wrap) | broken pointer update | *equiv.* | killed | *equiv.* | *equiv.* | killed |
| M3 `if (push) count++` (ignores simultaneous pop) | incorrect simultaneous push/pop | killed | killed | killed | killed | *equiv.* |
| M4 `rd_ptr` not reset | reset-state defect | killed | killed | killed | killed | killed |
| M5 `out_data = mem[rd_ptr_prev]` (one cycle stale) | stale read data | killed | killed | killed | killed | *equiv.* |
| *(same matrix, X-blind testbench v1)* | | M4 survives in 5/5; M2 survives at (8,1) | | | | |

## Mapping to P1.1 records, and mismatch evidence (for review; no schema change)
| # | Observation | Proposed handling in the seed | Needs a coordinator decision? |
|---|---|---|---|
| S1 | `TaskManifest.source` kinds are `repo_cut`/`commit_feature`/`commit_fix`/`mutation`/`generator`/`use_case`; none means "hand-authored in-house seed". | Use `use_case` with `intake_ref: "sindri:p1.6-seed/fifo"` for the base task. Mutant **debug tasks** use `mutation` (parent = base task, operator = mutant id). | yes (F9) |
| S2 | `authority_mode`: `reference_behavior` (needs `golden_hash` = reference RTL) vs `engineering_intent` (contract-first). | `engineering_intent` for the seed, because the contract is the authority and the reference is one witness; `golden_hash` stays null. | yes (F10) |
| S3 | A mutant has no natural `CandidateManifest.producer_role` (`solver`/`reconstructor`/`architecture_explorer`), and there is **no P1.1 record for known-bad fixtures or mutant classification**. | In the seed, mutants and the kill matrix are **plain fixture data** (`mutants/manifest.json`), not records. When the slice needs a failing Observation, the mutant RTL is the *starting repo state of a mutation debug task*, not a candidate. | yes (F11). Possible future record type: surfaced, not invented. |
| S4 | `approved_contract_hash` / `EvaluationPolicy.contract_hash` need *contract bytes*, but there is no Contract record (009 D6). | Hash the exact engineering-seed-v1 contract document (`contract/contract.md`) with `core.ids.content_id`. The document says `status: engineering-seed-approved`, `certification: uncertified`. Certification may later issue a new reviewed revision/hash. | no (coordinator decision, PR #33; consistent with D6) |
| S5 | `Observation.expected_test_ids` should come from the evaluator-bundle inventory (005 R5, 009 D4), which has no record yet. | The seed publishes its test inventory (`tb/tests.json`: the TEST names) as fixture data, so P1.4/P1.6 can anchor expected tests to it. | no; the evidence bundle stays P1.4/P1.6 |
| S6 | `TestId` pattern `[A-Za-z][A-Za-z0-9]*(_…)*` fits the testbench's `TEST <name>` lines; per-test PASS/FAIL maps to `SimulationReport.test_results`. Run-level `RESULT PASS/FAIL` plus `$fatal` on failure gives a TOOL_ERROR vs FAIL distinction by parsing, never by exit code. | Result protocol F7. | yes (F7) |
| S7 | Compile diagnostics without a file (P3) and errors without codes map to `Diagnostic(path=None, code=None)`. | No change. | no |

## Decisions requested (agent recommendations)
| ID | Question | Recommendation |
|---|---|---|
| F1 | Handshake | **Accepted:** valid/ready on both sides. |
| F2 | Reset | **Accepted:** synchronous, active-high, held for ≥ 1 rising edge; data storage not reset and is unobservable while `out_valid=0`. |
| F3 | Push when full while popping | **Accepted:** not accepted (`in_ready = !full`), even if a pop occurs in that cycle; no `out_ready -> in_ready` combinational path. |
| F4 | Fall-through | **Accepted:** none; push into empty becomes visible on the following cycle. |
| F5 | Depth constraint | **Accepted:** `WIDTH ≥ 1`, `DEPTH ≥ 1`, including non-power-of-two depths. |
| F6 | Language | **Accepted for the engineering seed:** synthesizable Verilog-2005 subset with explicit future tool-profile language mode; this is not a permanent Sindri language restriction. |
| F7 | Result protocol | **Accepted with strict completeness rules.** `tb/tests.json` is **configuration-scoped** and lists the exact expected `TestId`s for each configuration (R07 is absent at DEPTH=1). The transcript must contain each expected `TEST <TestId> PASS|FAIL` exactly once, no duplicates or unexpected IDs, plus exactly one terminal `RESULT PASS|FAIL`. `RESULT PASS` is valid only when every expected test is present exactly once and PASS and the final result agrees. Missing/duplicate/unexpected tests or disagreement fail closed. `$fatal(1,…)` remains a failure signal, but exit code is never the semantic oracle. |
| F8 | Tool provisioning for the requested Verilator/slang/Yosys evidence | **Coordinator decision: pinned OCI/container tooling.** No host-package installs. P1.3 owns provisioning/isolation and pins immutable digests. First execution/simulation profile: Icarus 12.x. Before a P1.4 compile/lint normalizer is considered stable, repeat diagnostics on pinned Verilator 5.x and slang/pyslang profiles. Yosys/SBY do not block this seed; provision them when synthesis/formal first enters the vertical slice and before P1.6/P1.7 certification claims depend on them. Do not invent image digests in this packet; P1.3 records the verified images. |
| F9 | Task source for an in-house seed | **Accepted narrowly:** use `use_case` for this exact coordinator-approved internal engineering use case, with a stable intake ref such as `sindri:p1.6/fifo-seed-v1`. This is not precedent for all authored assets; if authored seeds recur, surface a real source-kind change later. |
| F10 | Authority mode | **Accepted:** `engineering_intent`; the contract/requirements are authority, the reference RTL is a witness, and `golden_hash=None`. |
| F11 | Mutant representation | **Accepted:** plain, explicitly uncertified fixture data plus mutation-debug task inputs when needed. Do not invent a mutant/known-bad Record here. |
| F12 | X-blind testbench as a P1.7 fixture | **Accepted:** keep it quarantined under `known_bad/` for P1.7 anti-fake-PASS work; the positive test path must never discover/run it by default. |

## Proposed vertical-slice dependency shape (sequencing proposal, not an architecture change)
```text
P1.6 minimal FIFO seed (this task; depends on P1.1 only)
         ↓
P1.3 minimal execution substrate (one sandboxed process run, wall limit, captured stdout/stderr)
         ↓
P1.4 one real compile/sim adapter (Icarus first per F8; golden-log tests from P3–P7)
         ↓
P1.2 minimal durable evidence for the slice (blobs + records + append-only events)
         ↓
P1.5 minimal controller path (fakes first, then the real adapter in P1.8)
         ↓
P1.7 judge v0
         ↓
P1.8 repair + replay
```
Dependencies that the existing phase graph requires, or that the probes make objectively necessary:
1. **P1.6 does not need P1.3.** It can start now and may run in parallel with P1.3 (both depend only on P1.1).
2. **Coordinator decision: G-B moves earlier.** The ID-allocation ADR must land before any P1.4 implementation commits or mints `ObservationId` fixtures/outputs. Do not let sequential-style Observation IDs become a new fixture contract. G-S/G-U remain P1.2 persistence-entry requirements.
3. **Coordinator accepts this sequencing refinement.** P1.4 may exercise an ephemeral adapter path before P1.2 because its canonical dependency is P1.1 + P1.3, provided it persists nothing. Durable evidence arrives in P1.2 before controller/judge integration consumes stored evidence.
4. **P1.7 depends on P1.2 + P1.4 + P1.6** (phase file). P1.7 can be *engineered* against the seed, but its exit claim ("rejects predefined critical defects") needs the **certified** mutant set. So P1.7 completion, and therefore P1.8/P1.G, is gated on P1.6 certification and hence on the RTL/DV reviewer.
5. **Tool provisioning (F8) is a P1.3 entry question.** The sandbox has to run a pinned toolchain; the Icarus-only environment is not reproducible as-is (it is a host install).

No different ordering is objectively necessary beyond points 2 and 4.

## Scope (engineering seed, once ready)
- In scope, under `evals/fixtures/fifo/` (proposed layout):
  - `README.md`: semantics F1–F6, an "engineering seed — uncertified" label, and the two-track table;
  - `rtl/fifo_ref.v`, `rtl/fifo_alt.v`;
  - `tb/tb_fifo.v` (4-state strict, protocol F7) and `tb/tests.json` (**configuration-scoped** exact test inventories);
  - `mutants/M1…M5.v` (or patch files) and `mutants/manifest.json` (bug class, intended defect, recorded kill matrix, `status: uncertified`);
  - `known_bad/tb_fifo_xblind.v` (F12);
  - `contract/contract.md` (engineering-seed-v1 approved development contract; explicitly uncertified);
  - `records/*.json`: engineering-seed-v1 `TaskManifest` (base task + one mutation debug task), `Requirement` R01–R09 (`disposition: approved` for development scope), and `EvaluationPolicy` with the five-configuration matrix and directed-sim checks. All remain uncertified for P1.6 completion.
- Tests:
  - `tests/contract/test_fifo_seed_records.py`: the record drafts validate with the P1.1 models, `check_records` over the seed bundle returns `()` (or only documented, explained codes), and the contract hash matches `contract/contract.md`.
  - `tests/eda/test_fifo_seed_icarus.py`, marked `eda` and skipped when `iverilog` is absent: both controls pass every configuration, and every mutant's kill matrix reproduces exactly.
- Allowed paths: `evals/fixtures/fifo/**` (new), `tests/contract/test_fifo_seed_records.py` (new), `tests/eda/` (new, `eda` marker), `docs/REPO_MAP.md`, this packet, the handoff, and the task-board status.

## Forbidden paths / authority boundaries
- No Sindri adapters, sandbox, store, controller or judge code (P1.2–P1.5, P1.7).
- No P1.1 schema change because a tool output is inconvenient: mismatches are recorded (S1–S7) for review.
- No claim of certification. Every artifact is labelled `uncertified`. No hidden or final-evaluation material: the seed is development-visibility only.
- No tool installation into the repository or CI in this task (F8 decides provisioning).

## Non-goals
- Completing P1.6: the 15–20 critical mutants, reviewer sign-off and formal properties.
- Verilator/slang/Yosys/SBY evidence (blocked on F8), synthesis, formal, equivalence.
- Any vertical-slice code; any CI change to install EDA tools.

## Interfaces touched
- None in `src/`. New fixture data and tests only. The P1.1 records are used as-is.

## Acceptance criteria (engineering seed)
- [x] Reference and alternate RTL pass the 4-state strict testbench in all 5 configurations (`eda` test; reproduced locally with Icarus 12.0).
- [x] Each of M1–M5 compiles; its kill matrix reproduces exactly; each is killed in ≥ 1 configuration; equivalences are recorded per configuration (P8/P9).
- [x] The X-blind known-bad testbench is quarantined from the positive discovery path, retained, and shown to pass M4 (fake PASS) where the strict testbench kills it.
- [x] Record drafts validate with the P1.1 models; R01–R09 use `disposition: approved` for the engineering-seed-v1 scope; R07 encodes exact finite applicability; `check_records` over the seed bundle is clean or every code is explained.
- [x] Every artifact is labelled `engineering seed — uncertified`; the two-track table is in the README.
- [x] No `src/` change; no adapter, sandbox, store, controller or judge code.
- [x] Handoff written, with probe evidence and F-decisions; status → `review`.

## Verification commands
```bash
uv run ruff check . && uv run mypy && uv run pytest -q
uv run pytest -q -m eda tests/eda        # requires iverilog (Icarus 12.0); skipped otherwise
git diff --stat origin/main -- src/       # must be empty
```

## Plan of record
1. Write the semantics and contract draft (after F1–F7, F9–F12 decisions).
2. Add the RTL controls, strict testbench, test inventory, mutants and manifest, and the known-bad testbench.
3. Add the record drafts and the contract-hash test; run `check_records`.
4. Add the `eda` reproduction tests; record the kill matrix and tool version.
5. Handoff; status → `review`.

## Status
`review` (authoritative status: `implementation/task_board.yaml`). Engineering seed implemented from `main` `20e21e3`. It is approved for development use and **uncertified**; P1.6 certification remains blocked on RTL/DV/formal review.

## Completion evidence
- Files changed:
  - `evals/fixtures/fifo/**` (new):
    - `README.md`, `contract/contract.md`;
    - `rtl/fifo_ref.v`, `rtl/fifo_alt.v`;
    - `tb/tb_fifo.v`, `tb/tests.json`;
    - `mutants/m1…m5*.v`, `mutants/manifest.json`;
    - `known_bad/tb_fifo_xblind.v`, `known_bad/manifest.json`;
    - `records/fifo_seed/{task_manifest,requirements,evaluation_policy}.json` and `records/fifo_seed_m4/…`.
  - Tests: `tests/contract/test_fifo_seed_records.py`; `tests/eda/{__init__,_protocol,test_protocol,test_fifo_seed_icarus}.py`.
  - Docs: `docs/REPO_MAP.md`, this packet, the handoff, and the task board.
  - **No `src/` change**, no schema or ID change, no tool installed or pulled.
- Tests run/results:
  - `ruff` clean; `mypy --strict` clean.
  - `pytest`, local with Icarus 12.0: 2003 passed, 8 skipped.
  - `pytest -m eda tests/eda`: 71 passed.
  - Without `iverilog` on `PATH`: 12 protocol tests pass and 71 `eda` tests skip (the CI situation).
- Acceptance evidence:
  - **Controls:** `fifo_ref` and `fifo_alt` give protocol verdict PASS in all 5 configurations.
  - **Kill matrix**, reproduced exactly as in the packet (verdict FAIL = killed). Configurations in order (8,4) (8,3) (32,8) (1,2) (8,1):

    | Mutant | (8,4) | (8,3) | (32,8) | (1,2) | (8,1) |
    |---|---|---|---|---|---|
    | M1 | K | K | K | K | K |
    | M2 | S | K | S | S | K |
    | M3 | K | K | K | K | S |
    | M4 | K | K | K | K | K |
    | M5 | K | K | K | K | S |

    Each survival has an `uncertified` equivalence note.
  - **Quarantined X-blind testbench:** fake-PASSes M4 in all 5 configurations (and M2 at (8,1)), while the strict testbench kills M4 everywhere. Its expected verdicts are pinned in `known_bad/manifest.json`, and it is not reachable from `tb/`.
  - **F7 protocol:** missing, unexpected or duplicate tests, a missing or duplicate `RESULT`, a non-terminal `RESULT`, `RESULT`/test disagreement, and a bare fake `RESULT PASS` all yield INVALID (never PASS).
  - **Inventory:** derived from requirement applicability; `simultaneous_push_pop` (R07) is absent at DEPTH = 1.
  - **Records:**
    - 22 records validate, and `check_records(...) == ()`;
    - R01–R09 are `approved` and mandatory;
    - R07 is `parameter_scope DEPTH ∈ {2,3,4,8}`;
    - the contract hash equals `content_id(contract.md)` on both tasks and policies;
    - base task `use_case` (`sindri:p1.6/fifo-seed-v1`); debug task `mutation` (parent `fifo_seed`, operator `m4_rdptr_not_reset`);
    - `engineering_intent` with `golden_hash = null`.
- Implementation notes (for review):
  - **X-blind testbench:** making only two check lines X-blind did **not** reproduce the probe's fake PASS. The strict testbench's flag and data checks use `===`, which turns X into a definite 0. The quarantined testbench is therefore the strict one with **every** `===` turned into `==`, plus the `!cond` failure test. A test pins this exact mechanical transform.
  - **Rights:** `split: dev`; `licence: LicenseRef-Chipforge-Internal`, `training_allowed: false`, `evaluation_allowed: true`, `redistribution_allowed: false`. Seed choices; the coordinator may revise.
  - **Placeholder profile IDs:** the policy uses `tp_icarus12_compile` / `tp_icarus12_sim`; no profile record exists (009 D5; P1.3/P1.4 own it).
- Known limitations:
  - Icarus only. The Verilator 5.x and slang re-probe is a P1.3/P1.4 condition (F8). Yosys/SBY are not exercised.
  - CI skips the `eda` reproduction until P1.3 provides a pinned Icarus profile.
  - Not certified.
- Handoff/next action: `docs/handoffs/SIN-P1.6-001.md`.
