# SIN-P1.3-001 — Minimal isolated execution substrate for the FIFO vertical slice

## Phase identity
- Phase: `P1`
- Subphase: `P1.3` (first task)
- Architecture version: `master-architecture-v1`
- Governance version: `governance-v1.1`
- Implementation-plan version: `execution-v1.0`

## Outcome
The smallest typed, reproducible execution substrate. It runs one argv command inside a **pinned OCI
image**, in a **fresh isolated workspace**, with **no network**, under **CPU, memory, PID, wall-clock
and output limits**. It returns **raw stdout/stderr plus exit, signal, OOM, timeout and start-failure
metadata**, and **always cleans up**.

The first real workload is the verified FIFO seed (`evals/fixtures/fifo/`): Icarus compile and
simulate for the reference RTL, in all five configurations, inside a pinned Icarus 12 image.

```text
typed ExecutionRequest
  → fresh workspace (inputs materialized from content hashes, mounted read-only)
  → pinned OCI image (by digest / image ID)
  → argv execution (no shell)
  → CPU / memory / PID / wall / output limits
  → no-network sandbox
  → ExecutionResult: raw stdout/stderr (bounded) + exit / signal / OOM / timeout / start-failure metadata
  → deterministic cleanup (container + workspace), also after crashes
```

**Not P1.4.** The substrate does not:
- parse Verilog diagnostics;
- build Observations or map anything to `ToolStatus`;
- infer candidate correctness;
- mint `ObservationId`s.

It reports *what the process did*, never *what that means*.

## Why / architecture references
- `docs/implementation/phases/P1_FOUNDATION_AND_JUDGE_V0.md` §P1.3: fresh workspaces, resource limits, a no-network profile and typed process execution. Exit evidence: isolation/security fixtures, plus resource-limit and cleanup tests.
- `SECURITY.md`:
  - no network by default;
  - least-privilege mounts;
  - immutable/versioned tool profiles;
  - candidate code cannot alter the authoritative status channel;
  - the threat checklist (timeout reported as pass, writes outside the candidate tree).
- `src/sindri/tools/AGENTS.md`:
  - fresh sandbox from content hashes;
  - pinned image digest;
  - CPU/memory/time/output limits;
  - no network;
  - raw logs stored by reference;
  - never build shell commands from untrusted strings.
- AGENTS.md §4: no raw shell command construction from untrusted strings; inject clocks; idempotent retries.
- SIN-P1.6-001: F8 (pinned OCI tooling; Icarus 12.x first profile; re-probe Verilator/slang before P1.4 normalizers stabilize) and the FIFO seed workload.
- P1.1-G / P1.6 sequencing: P1.3 depends only on P1.1. G-B is needed before P1.4 mints Observation IDs, not for P1.3.

## Owner / coordinator
- Owner: assigned by coordinator when marked ready
- Integrator / reviewers: Avinash

## Base
- Base branch: `main`
- Base commit: `main` after this packet is merged and marked ready (drafted against `ab78611`)
- Worktree: `../worktrees/SIN-P1.3-001`

## Dependencies
- P1.1 complete (SIN-P1.1-010 verified).
- SIN-P1.6-001 verified: it provides the FIFO workload.
- No P1.2 or P1.4 dependency. No G-B dependency, because P1.3 mints no domain IDs.

## Facts from read-only probes on this host (2026-10-05; no image pulled or built)
The probes used only an image already present locally, `postgres@sha256:6efd0df0…`, with its entrypoint overridden for bash/coreutils. No HDL image exists locally.

Probe flags: `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --memory-swap 256m --cpus 1 --user 65534:65534 --tmpfs /work:size=64m -w /work --log-driver none`, plus `--init` in E4/E5 and later probes.

**Host**

| # | Finding | Consequence for the design |
|---|---|---|
| E1 | Docker 29.7.2 (API 1.55): **rootful** daemon, runc, cgroup v2 (systemd), AppArmor + seccomp, overlay2; 24 CPUs, ~93 GiB. **The user is in the `docker` group, which is root-equivalent on the host.** | The substrate must treat daemon access as privileged. Running *untrusted model-generated code* needs a hardening decision (D7). |

**Isolation**

| # | Finding | Consequence for the design |
|---|---|---|
| E2 | `--network none`: only `lo` exists; DNS lookup exit 2; TCP connect gives "Network is unreachable". `--read-only` root: writes fail (EROFS). `--cap-drop ALL`: CapEff = 0, NoNewPrivs = 1, Seccomp = 2 (filter). A size-limited tmpfs gives ENOSPC when full. | The isolation flags work as intended. Each becomes an asserted isolation fixture. |

**Exit and start-failure semantics**

| # | Finding | Consequence for the design |
|---|---|---|
| E3 | **`docker run` exit codes are ambiguous.** A missing binary gives CLI exit **127** with a daemon error on stderr, exactly what a process that itself exits 127 gives. With `docker create` → `docker start -a` → `docker inspect`, a start failure shows `Status=created` with a non-empty `State.Error`, while a real exit-127 process shows `Status=exited` with an empty `Error`. | Use **create → start (attached) → inspect**. The result distinguishes `start_failed` (infrastructure) from `exited(code)`, and never relies on CLI exit codes. |
| E4 | **PID-1 signal semantics:** without `--init`, `kill -SEGV $$` exits **0** and `kill -TERM $$` is ignored (the kernel ignores default-action signals sent to PID 1). With `--init`: SEGV → **139**, TERM → **143**. | Always use `--init`. The result carries `signal = exit − 128` when ≥ 129 under init, and also the raw exit code. |

**Resource limits**

| # | Finding | Consequence for the design |
|---|---|---|
| E5 | **OOM:** when a *child* is OOM-killed, the container still exits **0** with `State.OOMKilled = true`. When the *main* process is OOM-killed: exit 137 with `OOMKilled = true`. | `oom_killed` comes from `inspect`, is independent of the exit code, and is always reported. |
| E6 | **PID limit:** `--pids-limit 64` makes forks fail with "fork: retry: Resource temporarily unavailable". bash retries and then continues (3.2 s), so the job slows down rather than failing. | A wall-clock timeout is mandatory, and the PID limit is an asserted fixture. |
| E7 | **Output is unbounded:** 50 MB of stdout passes through the attached CLI intact. The **default log driver is `json-file`** (unbounded on-disk copies). | Use `--log-driver none`. Capture with **host-side bounded readers** (per-stream byte cap, `truncated` flag, total bytes observed). Raw output is returned as bytes, never decoded or interpreted. |
| E8 | **Orphaned containers:** killing the `docker run` client (timeout −s KILL) leaves the container **running**. `docker kill` gives exit 137; `docker rm -f` removes it. | Every run gets a unique container name and a `sindri.run=<id>` label. On timeout, kill then `rm -f`. A `finally` and a startup **sweep of stale labelled containers** give deterministic cleanup, even after a crashed host process. |

**Environment, files and performance**

| # | Finding | Consequence for the design |
|---|---|---|
| E9 | **Image ENV leaks** into the process (`PATH`, `GOSU_*`, `PG_*`, …), and `HOSTNAME` is random per run. | The environment is part of the pinned image profile. The request sets an explicit env allow-list and `--hostname` is fixed. Host env is never passed through. |
| E10 | **Files:** a read-only bind mount of the FIFO seed works (writes give EROFS). A writable host workspace mounted with `--user <host uid>:<host gid>` produces files owned by the host user, so cleanup needs no privilege. tmpfs content disappears with the container. | Inputs go to `/in` (read-only), materialized from content hashes. The writable `/work` is a fresh host temp dir owned by the host uid. Declared outputs are collected after exit, size-capped and hashed. |
| E11 | Cold `docker run --rm … true` takes ≈ **0.23 s**; stdin is closed (read returns EOF); stdout and stderr stay separate when attached through pipes. | Per-job overhead is acceptable. The FIFO (10 runs) costs about 3 s of container overhead. |
| E12 | **No HDL image is available locally,** and `docker build`/`pull` was deliberately not run. | The pinned Icarus 12 image is produced during implementation, per D3; its digest is recorded then. |

## Decisions requested (agent recommendations)
| ID | Question | Recommendation |
|---|---|---|
| D1 | Where does the code live? | **`src/sindri/tools/sandbox/`**, a subpackage of `tools`, matching `REPO_MAP` ("sandbox / `src/sindri/tools/` — P1.3/P1.4"). It needs no new top-level package, no guardrails/ADR change and no import-test change. `tools` still must not import `solver`. |
| D2 | Container interface | **Docker CLI via `subprocess` with an argv list** (never `shell=True`), behind a small `ContainerRuntime` protocol: `create`, `start_attached`, `inspect`, `kill`, `remove`, `sweep`. Unit tests use a fake runtime; real tests are marked `sandbox`. **No new Python dependency.** The Docker SDK would need a licence/dependency review; Podman and gVisor are later runtimes behind the same protocol. |
| D3 | The pinned Icarus 12 image | **(a) A repository-owned Dockerfile** (`images/icarus12/Dockerfile`): base image pinned by digest, Icarus pinned to an exact 12.0 package version, no network at run time. It is built once and **pinned by image ID / digest** recorded in a checked-in profile file. **(b) A third-party image pinned by digest.** Recommend **(a)**: provenance is reviewable. Building or pulling requires coordinator approval at implementation time; the planning PR does neither. Note that apt-based builds are not bit-reproducible, so the *recorded digest* is the authority, not the Dockerfile. |
| D4 | Typed request/result | **Frozen strict value models in `tools.sandbox`, not `Record`s:** `ExecutionRequest`, `ExecutionLimits`, `InputFile`, `ExecutionResult`, `StreamCapture`. `ExecutionRequest.request_hash()` is the canonical content hash, a candidate for `PendingJob.request_hash` later. **No job-request Record** (009 D3 stays with P1.2/P1.5). Nothing is persisted. |
| D5 | Limits and defaults | Memory = memory-swap (no swap); `--cpus` for the rate; `--ulimit cpu=<s>` for total CPU time; `--pids-limit`; host-side wall clock (monotonic, injected clock); a per-stream output cap; a tmpfs `/tmp` size limit; a writable `/work` size checked on collection. Every limit is explicit in the request, with no hidden defaults; the FIFO profile states its values. |
| D6 | Outcome vocabulary (substrate only) | `ExecutionResult.outcome ∈ {exited, timed_out, start_failed, runtime_unavailable}`, plus orthogonal flags `oom_killed`, `stdout_truncated`, `stderr_truncated`, `signal` (if any) and `exit_code`. **No `ToolStatus` mapping:** that is P1.4. |
| D7 | Rootful Docker and untrusted code (E1) | Accept rootful Docker with the E2 hardening for **P1.3 on trusted FIFO fixtures**. **Gate:** before the slice executes *model-generated* candidates (P1.5/P1.8), the coordinator decides on rootless Docker / userns-remap / gVisor (or equivalent) and records it as an ADR. The P1.3 substrate keeps the runtime behind D2's protocol so it can be swapped. |
| D8 | Should "sandbox runtime = pinned OCI via Docker" be an ADR? | Yes: **draft ADR-0007, "Execution substrate: pinned OCI containers behind a ContainerRuntime protocol"**, proposed in the implementation PR. The coordinator accepts or rejects it. |
| D9 | CI | Unit tests always run (fake runtime). `sandbox`-marked tests run when Docker and the pinned image are available, and are skipped otherwise. **Whether CI builds or pulls the Icarus image on every push** is a separate coordinator decision; recommend a scheduled or manual job first, not the fast gate. |

## Scope (once ready)
- `src/sindri/tools/sandbox/` (new):
  - `models.py`: request, limits, inputs, result, streams. Strict, frozen, typed; canonical `request_hash()`.
  - `runtime.py`: the `ContainerRuntime` protocol and `DockerCliRuntime` (argv only, create/start/inspect/kill/rm/sweep).
  - `executor.py`: `execute(request, runtime, clock, workspace_root) -> ExecutionResult`. It materializes and verifies inputs, mounts `/in` read-only and `/work` read-write, applies flags, enforces the wall clock, runs bounded capture, collects declared outputs, and cleans up in `finally`.
  - `profiles/icarus12.json`: the pinned image reference (digest/ID), the image env allow-list, default limits, and the language-mode flags (`-g2005`).
- `images/icarus12/Dockerfile` (D3a), with the base image pinned by digest.
- Tests:
  - **Unit (fake runtime):**
    - argv never goes through a shell;
    - every isolation flag is present;
    - `--init`, `--log-driver none` and labels are set;
    - inputs are verified against content hashes, and a hash mismatch is refused before start;
    - timeout leads to kill and remove;
    - the bounded reader truncates exactly at the cap and flags it;
    - outcome classification follows E3/E4/E5;
    - cleanup runs on every path, including runtime exceptions;
    - an injected clock makes timestamps and durations deterministic.
  - **`sandbox`-marked integration (real Docker), each probe E2–E10 as a fixture:**
    - no network;
    - read-only root and read-only inputs;
    - no capabilities;
    - OOM (main and child);
    - PID limit;
    - wall timeout with an orphan-free cleanup and sweep;
    - output cap;
    - start failure vs exit 127;
    - SIGSEGV → 139 under init;
    - deterministic hostname and env.
  - **FIFO workload (`sandbox` + pinned image):**
    - reference RTL compile + `vvp` in all 5 configurations, inside the container;
    - raw stdout passed to the **test-only** `tests/eda/_protocol.py` verdict gives PASS;
    - M4 gives FAIL;
    - the raw stdout is byte-identical across two runs, and to the host-Icarus transcript where the versions match.
    - The substrate itself performs no verdict.
- Docs: `components/tools.yaml` (new: the sandbox component contract), `docs/REPO_MAP.md`, `SECURITY.md` (sandbox controls, plus D7 as an open risk), this packet, and the handoff.

## Allowed paths (proposed)
- `src/sindri/tools/sandbox/**`, `images/icarus12/**`;
- `tests/unit/tools/**`, `tests/sandbox/**` (new marker `sandbox` in `pyproject.toml`);
- `components/tools.yaml`, `docs/REPO_MAP.md`, `SECURITY.md`, `docs/adr/0007-*.md` (proposed status only);
- this packet, the handoff, the task board;
- `pyproject.toml` (marker registration only).

## Forbidden paths / authority boundaries
- No Verilog diagnostic parsing, no `Observation` construction, no `ToolStatus` mapping, no correctness inference (P1.4).
- No evidence store, persistence or event log (P1.2).
- No controller or scheduler (P1.5); no judge (P1.7).
- No `ObservationId` or other domain-ID minting. Container names and run labels are ephemeral substrate identifiers, not domain IDs.
- No change to P1.1 schemas or IDs, `core/ids.py`, `cross_record.py` or the FIFO seed (read-only workload).
- No host-package EDA installs. Image build or pull only as approved under D3.

## Non-goals
- Verilator, slang, Yosys or SBY images (the F8 re-probe belongs to the P1.4 entry).
- A multi-job scheduler, retries or caching.
- Rootless or gVisor hardening (D7 gate).
- Windows/macOS hosts.

## Acceptance criteria (once ready)
- [ ] `execute()` runs an argv list in a pinned image with every E2 isolation property asserted by a `sandbox` fixture.
- [ ] Outcomes are distinguished exactly: exited(code), signal under `--init`, OOM flag (main and child), timed_out (with orphan-free cleanup), start_failed (vs exit 127), runtime_unavailable.
- [ ] Output caps are enforced host-side with truncation flags; `--log-driver none`.
- [ ] Inputs are materialized from content hashes and verified before start; `/in` is read-only; `/work` is fresh and removed after the run; a stale-container sweep is proven.
- [ ] The FIFO reference passes in all 5 configurations and M4 fails, judged only by the test-side F7 parser over **raw** substrate stdout. Two runs are byte-identical.
- [ ] No ToolStatus/Observation/ID logic in `tools.sandbox`; no shell; no new Python dependency.
- [ ] ADR-0007 is drafted as `proposed`; the D7 risk is recorded in SECURITY.md.
- [ ] Handoff written; status → `review`.

## Verification commands (once ready)
```bash
uv run ruff check . && uv run mypy && uv run pytest -q
uv run pytest -q -m sandbox tests/sandbox     # requires Docker + the pinned Icarus image
docker ps -a --filter label=sindri.run --format '{{.Names}}'   # must be empty after the suite
```

## Status
`planned` (authoritative status: `implementation/task_board.yaml`). Planning only. Open decisions: D1–D9. D3 (image source; build/pull approval) and D7 (rootful Docker before untrusted code) are the most consequential.

## Completion evidence
- Files changed:
- Tests run/results:
- Acceptance evidence:
- Known limitations:
- Handoff/next action:
