# SIN-P1.1-005 Handoff

> Mandatory at the end of every meaningful session (AGENTS.md §9). A fresh agent or engineer must
> be able to continue from this file plus the repository, with no chat history.

## Session
- Finished at: 2026-10-04
- Agent / person: coding agent (Claude Code), assigned by the coordinator
- Branch/worktree: `feat/SIN-P1.1-005-observation` at `../worktrees/SIN-P1.1-005`
- HEAD commit: the PR #15 review-fix commit (child of `9294d16`, whose CI run 37187622159 passed)
- Base commit: `08bda00` (`main`, PR #14: SIN-P1.1-005 READY on `main`, so the process rule was satisfied)
- Dirty files, if any: none after commit

## Completed
- `Observation` v1:
  - binding (exact candidate, exact policy check/configuration);
  - executor (action, profile ID/hash, image digest, adapter version/hash);
  - inputs (evaluator bundle, seed, formal mode/depth, wall-time limit);
  - `execution_key`;
  - result (`started_at`, `duration_ms`, raw `ToolStatus`, summary, diagnostics, log/evidence refs, typed execution report).
- Supporting types: `ObservationAction` and the closed `ACTION_FOR_KIND` map (R2, no `quality`), `Diagnostic`, `EvidenceRef`, and the four execution reports (`SimulationReport`, `FormalReport`, `EquivalenceReport`, `StructuralReport`).
- `observation_execution_key()`: the single implementation of `observation_execution_key_v1`.
- Additive IDs `TestId` and `PropertyId`. Contract tests, adapted §20.4 fixture, component invariants INV-OB-001…005.

## Verified
| Command / check | Result | Notes |
|---|---|---|
| `uv run ruff check .` | pass | |
| `uv run mypy` (strict) | pass | 16 files |
| `uv run pytest -q` | 602 passed, 8 skipped, no warnings | after PR #15 fixes |
| `uv run pytest -q tests/contract` | 489 passed | 172 Observation tests |
| Byte-level `hashlib` vector for the execution key | match | 15 request fields + the `kind` tag |
| Planted: TIMEOUT with failing test allowed | 3 failures | restored |
| Planted: sim PASS with executed ⊂ expected | 1 failure | restored |
| Planted: formal PASS with checked ⊂ expected | 1 failure | restored |
| Planted: `candidate_manifest_hash` dropped from key | 12 failures | restored |
| Planted: `adapter_hash` dropped from key | 12 failures | restored |
| Planted: `evaluator_bundle_hash` nullable | 1 failure | restored byte-identical |
| PR #15: synthesis black-box rule removed | 1 failure | restored byte-identical |

## Changed
`src/sindri/core/ids.py` (additive), `src/sindri/schemas/observation.py` (new), `src/sindri/schemas/__init__.py`, `tests/contract/test_observation.py`, `tests/contract/examples/observation.json`, `tests/unit/test_ids.py`, `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml` (→ `review`), task packet, this handoff. All within the packet's allowed paths.

## Decisions
No new decisions. Seven implementation interpretations are listed in the packet's completion evidence for coordinator review. The most consequential:
- formal FAIL needs a failing property and a counterexample;
- results outside the expected inventory are rejected for every status;
- non-verdict statuses reject any candidate failure evidence.

## Deviations
None. Implementation started from `main` after READY was authoritative there.

## Review fixes (PR #15)
- Synthesis PASS now rejects `blackbox_count > 0` (master §14 J1). Synthesis FAIL may rest on errors, black boxes or latches when a candidate error diagnostic is present. Latches are not judged in PASS.
- Expected-latch semantics recorded as a P1.4/P1.6 follow-up: the evaluator/profile defines expected latches; the adapter emits a candidate error for unexpected ones.
- `components/schemas.yaml`: ADR-0005 added to `related_adrs`; `related_docs`, `purpose` and `public_interfaces` refreshed for 003/004/005; INV-OB-006 added.
- Execution-key count corrected: 15 request fields plus the `kind` tag (previously written as "16 request fields").
- Coordinator approved the other six implementation interpretations as-is.

## Open questions
None.

## Blocked on
- Coordinator review and merge of this task's PR.

## Next ready after approval
Per the P1.1 order, once 005 is merged and verified (the coordinator opens them; the agent does not):
- SIN-P1.1-006 Finding and SIN-P1.1-007 EpisodeState, which may run in parallel. 006 must decide how Findings cite Observations (by `observation_id` + `content_id()`) and diagnostic results (ADR-0005).

## Do not start
- 006, 007, 008, 009, P1.1-G, any diagnostic/qualification result type, P1.2+.

## Risks / things not to change casually
- The execution-key construction is identity: changing a field, the tag or an encoding changes every key. Use a new `kind` tag, never an edit.
- Never add a status rewrite (e.g. TIMEOUT → FAIL) anywhere downstream. The raw status is evidence (ADR-0002).
- `quality` stays out of Observation until quality has defined acceptance semantics (O11).
- Expected inventories are adapter-reported until the evaluator-bundle manifest anchors them (R5 follow-up).
