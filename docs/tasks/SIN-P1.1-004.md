# SIN-P1.1-004 — CandidateManifest

## Phase identity
- Phase: `P1`
- Subphase: `P1.1`
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
`CandidateManifest` exists as a strict, immutable record of exactly one candidate design version:
which task it is for, which files with which content hashes it consists of (with a precisely defined
source identity), the context it was built against, which candidate it was derived from and by what
patch, and which model configuration and provenance produced it. Every later observation and
judgement can then bind to an exact, reproducible candidate identity (master principle 9).

## Why / architecture references
- Master architecture: §4 principle 9; §8.7 (CandidateManifest contents); §8.8 (edits create new immutable candidate identity; branches are separate candidates); §8.9 ("every model output carries model/version/licence/provenance tags; records whose usage rights do not permit training are filtered before export"); §8 F6 model gateway (records version, seed, temperature and licence tags); §8 F1 `submit(candidate)`; §20.3 example.
- Phase/subphase: P1.1; order in `docs/implementation/CURRENT_PHASE.md`: 002 → **{003, 004}** → 005.
- ADRs/RFCs: ADR-0001, ADR-0002.

## Owner / coordinator
- Owner: coding agent (Claude Code), assigned 2026-10-04
- Integrator: Avinash
- Reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` when the packet is marked ready
- Worktree: `../worktrees/SIN-P1.1-004`

## Dependencies
- Required completed tasks: SIN-P1.1-002 (verified)
- Required schemas/contracts: `sindri.schemas._base`, `sindri.schemas.task.EditPath` (import only), `sindri.core.ids` (`CandidateId`, `EpisodeId`, `TaskId`, `ContentId`, `canonical_json_id` already exist; this task adds **no** ID types)

## Coordinator decisions (PR #8, 2026-10-04; recorded, not made, by the agent)
| ID | Decision |
|---|---|
| F1 | **Accepted.** `temperature_millis: StrictInt ≥ 0` (0.8 → 800). Any later sampling parameter follows the same scaled-integer convention. |
| F2 | **Accepted.** No `frozen` field; submission is an event/registry fact (controller, P1.5). |
| F3 | **Accepted, tightened.** `source_hash` is required and must equal exactly `canonical_json_id({"kind": "candidate_file_set_v1", "files": [{"path": p, "hash": h}, …]})`, with files sorted by `path`. The construction is domain-separated and versioned, so different implementations cannot produce different identities for the same file set. Changing the construction means a new `kind` tag. |
| F4 | **Accepted, with one meaning for `None`.** `dependency_hash: ContentId \| None` is a required key. `None` means **this task explicitly has no external dependency bundle**. It never means "unknown" or "not computed yet"; a manifest whose dependencies are not yet known cannot be created. |
| F5 | **Accepted.** `parent_candidate_id` and `patch_hash` are both required keys and must be both present or both `None`. |
| F6 | **Accepted, corrected in PR #11 review.** `producer_role: solver \| reconstructor \| architecture_explorer`. `solver` requires `episode_id`; `reconstructor` forbids it; `architecture_explorer` has it optional: `None` means oracle-side exploration, a value means solver-side exploration inside that episode (master X4 uses the explorer in both places, so the solver-side episode provenance must be kept). |
| F7 | **Corrected.** Provenance is recorded at the source, not first at DatasetRecord. `author` must contain at least: `model`, `model_version`, `temperature_millis`, `seed: StrictInt`, `provenance_ref` (non-blank) and `training_allowed: StrictBool` (required, no default). Later, the model gateway (F6/P5.1) makes `provenance_ref` resolve to the exact call/provider/terms record. DatasetRecord may derive export eligibility from it, but must not be the first place provenance appears. |
| F8 | **Accepted.** Candidate IDs are opaque; relationships are explicit fields only. |
| Path reuse | **Decided.** 004 imports `EditPath` from the verified `schemas/task.py`. It must **not** refactor it into `_base.py` during this task, because that kind of innocent cleanup makes parallel branches overlap. |

## Scope
- In scope:
  - `src/sindri/schemas/candidate.py`: `CandidateManifest` (`Record`) with:
    - `candidate_id: CandidateId`, `task_id: TaskId`, `producer_role`, `episode_id: EpisodeId | None`;
    - `parent_candidate_id: CandidateId | None`, `patch_hash: ContentId | None`;
    - `files`: non-empty and unique by path, each `{path: EditPath, hash: ContentId}`;
    - `source_hash: ContentId` (F3), `dependency_hash: ContentId | None` (F4);
    - `author` (F7): `model`, `model_version` (non-blank), `temperature_millis`, `seed`, `provenance_ref`, `training_allowed`.
  - A module-level function `candidate_source_hash(files) -> ContentId` that implements the F3 construction exactly. It is the only place the construction lives, and the validator and tests use it.
  - In-record invariants:
    - `source_hash` equals `candidate_source_hash(files)`;
    - the parent/patch pairing;
    - the episode/role rule (F6: solver requires, reconstructor forbids, explorer optional);
    - a candidate is not its own parent;
    - unique, safe file paths;
    - floats rejected (inherited).
  - Tests under `tests/contract/`, with an adapted §20.3 example fixture.
- Allowed paths: `src/sindri/schemas/candidate.py`, `src/sindri/schemas/__init__.py` (exports only), `tests/contract/`, `components/schemas.yaml`, `docs/REPO_MAP.md`, this packet, `docs/handoffs/SIN-P1.1-004.md`, `implementation/task_board.yaml` (status-only governance state).

## Forbidden paths / authority boundaries
- Hidden evaluator/final-eval paths: none.
- Other forbidden paths:
  - `src/sindri/core/ids.py` (owned by SIN-P1.1-003 in this pair);
  - `src/sindri/schemas/{_base,task,requirement}.py` (verified; import only);
  - `src/sindri/schemas/policy.py` (003);
  - `core/status.py`.

## Non-goals
- No file storage or on-disk hashing (P1.2); the manifest records hashes it is given.
- No submission/freeze lifecycle (P1.5), no dependency-bundle definition (P1.5/§8.10), no model-gateway provenance records (P5.1).
- No cross-record checks. These belong to SIN-P1.1-009:
  - file paths lie inside the task's `allowed_edit_paths`;
  - `task_id` resolves;
  - the parent belongs to the same task;
  - read-only tasks have no candidates.
- No Observation, Finding or EpisodeState.

## Interfaces touched
- Schemas: new `CandidateManifest` v1. IDs: none new. Tool APIs, DB, external dependencies: none.

## Acceptance criteria
Positive:
- [x] The adapted §20.3 example (per F1–F8) validates, round-trips and re-serializes to identical JSON.
- [x] First candidate (no parent, no patch), derived candidate (parent + patch), and reconstructor candidate (no episode) each validate.
- [x] `candidate_source_hash` equals a hand-computed `canonical_json_id({"kind": "candidate_file_set_v1", "files": [...]})` known vector; it is independent of `files` input order and changes when any path or hash changes.
- [x] `training_allowed: false` validates (provenance that forbids training is representable).

Negative (each a separate test):
- [x] Every field required (no defaults), including the nullable ones as explicit keys and every `author` field.
- [x] Unknown fields rejected at every level, including `frozen` (F2) and `temperature` (F1).
- [x] A `source_hash` computed without the domain tag, with a different tag, or over unsorted files → rejected.
- [x] Parent without patch, patch without parent, or a candidate as its own parent → rejected.
- [x] `solver` without `episode_id`, or `reconstructor` with one → rejected; `architecture_explorer` validates both with an episode (solver-side) and without (oracle-side) (F6, PR #11 review).
- [x] Empty files, duplicate paths, absolute paths, `..`, empty segments or backslashes → rejected.
- [x] Blank `provenance_ref`, `model` or `model_version` → rejected; `training_allowed` given as `1` or `"true"` → rejected.
- [x] Negative `temperature_millis`; `"800"`, `True` or `0.8` as numbers → rejected (no coercion, no floats).
- [x] The record is immutable.

Planted-bug checks (run, record in the handoff, revert):
- [x] Dropping the domain tag from `candidate_source_hash` makes the suite fail.
- [x] Skipping the `source_hash` recomputation makes the suite fail.
- [x] Defaulting `training_allowed=True` in `author` makes the suite fail.

General:
- [x] `ruff`, `mypy --strict`, full `pytest` green; the boundary test still covers `schemas`.
- [x] `components/schemas.yaml` gains the candidate invariants (incl. the F3 construction and F4 meaning of `None`); `docs/REPO_MAP.md` updated.
- [x] Handoff written; report ends with "Awaiting coordinator assignment."

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
- Shared files: `src/sindri/schemas/__init__.py` (exports), `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`. These are append-only edits; the integrator resolves ordering.
- This task does not touch `src/sindri/core/ids.py` and does not move `EditPath`.

## Status
`review` (authoritative status: `implementation/task_board.yaml`). Decisions F1–F8 implemented as written.

## Completion evidence
- Files changed: `src/sindri/schemas/candidate.py` (new), `src/sindri/schemas/__init__.py` (exports), `tests/contract/test_candidate_manifest.py` (new), `tests/contract/examples/candidate_manifest.json` (new), `components/schemas.yaml`, `docs/REPO_MAP.md`, `implementation/task_board.yaml`, this packet, handoff. `core/ids.py` and the verified schema files are untouched; `EditPath` is imported, not moved.
- Tests run/results (after PR #11 review fixes): `ruff` clean; `mypy --strict` clean (14 files); `pytest`: 328 passed, 8 skipped (64 CandidateManifest contract tests).
- Acceptance evidence:
  - The F3 construction is pinned by a **byte-level vector built with `hashlib` from a hand-written canonical JSON string**, independent of `canonical_json_id`. Hashes from four other constructions (no tag, other tag, unsorted, bare list) are rejected.
  - The adapted §20.3 example validates and re-serializes to identical JSON. Its `source_hash` was produced by `candidate_source_hash`, and the byte-level vector independently confirms that function.
  - Rejection reasons spot-checked: absolute path, duplicate path, backslash and malformed hash each fail on their own rule, not on a hash mismatch.
  - Planted bugs, each caught and reverted:
    - domain tag dropped → 15 failures;
    - recomputation skipped → 4;
    - `training_allowed=True` default → 1.
- Review fix (PR #11): with the old over-strict episode rule restored, the new solver-side explorer test fails (1 failure); with the corrected rule, all pass.
- Known limitations: `seed` is any strict integer (no range is specified by the master); paths sort by Unicode code point (documented in `candidate_source_hash`).
- Handoff/next action: `docs/handoffs/SIN-P1.1-004.md`.
