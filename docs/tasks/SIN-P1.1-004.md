# SIN-P1.1-004 — CandidateManifest

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`CandidateManifest` exists as a strict, immutable record of exactly one candidate design version:
which task it is for, which files with which content hashes it consists of, the context it was built
against, which candidate it was derived from and by what patch, and which model configuration
produced it. Every later observation and judgement can then bind to an exact, reproducible candidate
identity (master principle 9: "a pass on yesterday's file means nothing for today's file").

## Why / architecture references
- Master architecture: §4 principle 9; §8.7 ("CandidateManifest: candidate/parent IDs, source hash, dependency hash, model configuration and patch ancestry"); §8.8 (candidate edits create new immutable candidate identity, architecture branches are separate candidates); §6.6 (the agent "edits a new immutable candidate"); §8 F1 `submit(candidate)`; §8 F6 provenance; §20.3 example.
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md`: 002 → **{003, 004}** → 005.
- ADRs/RFCs: ADR-0001, ADR-0002.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` when the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-004`

## Dependencies
- Required completed tasks: SIN-P1.1-002 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.core.ids` (`CandidateId`, `EpisodeId`, `TaskId`, `ContentId` already exist; this task adds **no** ID types)

## Decisions needed before READY
The §20.3 example conflicts with already-accepted decisions in places. The agent recommends an option for each; **the coordinator decides**.

| ID | Question | Agent recommendation |
|---|---|---|
| F1 | **`temperature: 0.8` is a binary float**, which D5 forbids in records. | An exact scaled integer: `temperature_millis: StrictInt ≥ 0` (0.8 → 800). It is simpler and less ambiguous than a canonical decimal string. The same convention applies to any later sampling parameter (e.g. `top_p_millis`). |
| F2 | **`frozen: true`.** Every manifest is already immutable, so "frozen" can only mean "submitted for judging" (`submit(candidate)`), which is lifecycle state. | Drop `frozen` from the record, following the D1 reasoning. Submission is an event/registry fact (controller, P1.5). |
| F3 | **Source hash** (§8.7). | `source_hash: ContentId` is required and must equal the canonical ID computed from the sorted `(path, hash)` file list. A record whose declared hash disagrees with its files is rejected, so identity cannot be asserted, only derived. |
| F4 | **Dependency hash** (§8.7): the read-only context (repo files, packages, includes) the candidate was built against. | `dependency_hash: ContentId \| None`, required but nullable, so a task with no external context says so explicitly. What goes into the dependency bundle is defined by the controller/context work (P1.5, §8.10), not here. |
| F5 | **Patch ancestry** (§8.7): `parent_candidate` alone does not say what changed. | `parent_candidate_id: CandidateId \| None` and `patch_hash: ContentId \| None`, both required keys; `patch_hash` is present if and only if there is a parent. A first candidate has neither. |
| F6 | **Producer.** §20.3 assumes a solver episode, but oracle-side roles also produce candidates (reconstructors S7, microarchitecture explorer X4 alternatives). | `episode_id: EpisodeId \| None` plus a required `producer_role` enum: `solver`, `reconstructor`, `architecture_explorer`. `episode_id` is required if and only if the role is `solver`. Human-written goldens are not candidates (master §2 "Candidate means any design produced by an agent"). |
| F7 | **Model configuration** (§8.7, F6). | `author`: `model` (non-blank), `model_version` (non-blank), `temperature_millis`, `seed: StrictInt`. Licence/provenance tags are attached where datasets are exported (DatasetRecord, later), not duplicated here. |
| F8 | **Semantic IDs.** `c_pktfr_0193_e17_v3` encodes task, episode and version in its text. | Do **not** parse meaning out of ID text. Relationships are explicit fields only; IDs are opaque labels. |

## Scope (written for the recommended options; finalized after decisions)
- In scope:
  - `src/sindri/schemas/candidate.py`: `CandidateManifest` (`Record`):
    - Identity: `candidate_id`, `task_id`, `producer_role`, `episode_id`.
    - Ancestry: `parent_candidate_id`, `patch_hash`.
    - `files`: non-empty and unique by path, each with a safe relative POSIX `path` (same rules as 002 `EditPath`) and a `hash: ContentId`.
    - Hashes: `source_hash`, `dependency_hash`.
    - `author` per F7.
  - In-record invariants:
    - `source_hash` equals the canonical ID of the sorted file list;
    - the patch/parent pairing;
    - the episode/role pairing;
    - a candidate is not its own parent;
    - unsafe or duplicate paths rejected;
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.3 example fixture.
- Allowed paths: `src/sindri/schemas/candidate.py`, `src/sindri/schemas/__init__.py` (exports only), `tests/contract/`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-004.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Other forbidden paths: `src/sindri/core/ids.py` (owned by SIN-P1.1-003 in this pair), `src/sindri/schemas/{_base,task,requirement}.py`, `src/sindri/schemas/policy.py` (003), `core/status.py`.
- **Reuse:** the safe-path validator lives in `schemas/task.py`, a verified file this task may not edit. 004 may *import* `EditPath` from it. If moving it to `_base.py` is preferable, that is a coordinator call, not an in-task refactor.

## Non-goals
- No file storage or hashing of files on disk (P1.2); the manifest records hashes it is given.
- No submission/freeze lifecycle (P1.5), no dependency-bundle definition (P1.5/§8.10).
- No cross-record checks. These belong to SIN-P1.1-009:
  - every file path lies inside the task's `allowed_edit_paths`;
  - `task_id` resolves to a manifest;
  - the parent candidate belongs to the same task;
  - read-only tasks have no candidates.
- No Observation, Finding or EpisodeState.

## Interfaces touched
- Schemas: new `CandidateManifest` v1. IDs: none new. Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [ ] The adapted §20.3 example (per F1–F8) validates, round-trips and re-serializes to identical JSON.
- [ ] A first candidate (no parent, no patch), a derived candidate (parent + patch), and a reconstructor candidate (no episode) each validate.
- [ ] `source_hash` is independent of the input order of `files` and changes when any file hash or path changes.

Negative (each a separate test):
- [ ] Every field required (no defaults), including the nullable ones as explicit keys.
- [ ] Unknown fields rejected at every level, including `frozen` (F2) and `temperature` (F1).
- [ ] A `source_hash` that does not match the files → rejected.
- [ ] Parent without patch, patch without parent, or a candidate as its own parent → rejected.
- [ ] `solver` without `episode_id`, or a non-solver role with one → rejected.
- [ ] Empty files, duplicate paths, absolute paths, `..`, empty segments or backslashes → rejected.
- [ ] Negative `temperature_millis`, non-integer `seed`, floats anywhere → rejected; no coercion (`"800"`, `True` rejected as integers).
- [ ] The record is immutable.

Planted-bug checks (run, record in the handoff, revert):
- [ ] Skipping the `source_hash` recomputation makes the suite fail.
- [ ] Making `parent_candidate_id` default to `None` makes the suite fail.

General:
- [ ] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [ ] `components/schemas.yaml` gains the candidate invariants; `docs/REPO_MAP.md` updated.
- [ ] Handoff written; report ends with "Awaiting coordinator assignment."

## Verification commands
```bash
uv run ruff check .
uv run mypy
uv run pytest -q
uv run pytest -q tests/contract
```

## Plan of record
`src/sindri/schemas/candidate.py`, `src/sindri/schemas/__init__.py`, `tests/contract/test_candidate_manifest.py`, `tests/contract/examples/candidate_manifest.json`, `components/schemas.yaml`, `docs/REPO_MAP.md`.

## Parallel work with SIN-P1.1-003
- Shared files: `src/sindri/schemas/__init__.py` (exports), `components/schemas.yaml`, `docs/REPO_MAP.md`. These are append-only edits; the integrator resolves ordering.
- This task does not touch `src/sindri/core/ids.py`.

## Status
`planned`. Draft for coordinator review; decisions F1–F8 open (authoritative status: `implementation/task_board.yaml`).

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
