"""Coherent cross-record bundle, built by construction from a typed spec (SIN-P1.1-009, Q1).

The §20 example files are isolated record fixtures and are deliberately left untouched. This
builder produces one internally consistent FIFO family. `seal()` builds records in spec order,
replacing every `Ref` with the content_id (or a field) of an already-built record. It recomputes
`CandidateManifest.source_hash` and `Observation.execution_key`, so a spec edit made before sealing
changes only what the edit names, and every dependent hash follows.
"""

import copy
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sindri.core.ids import ContentId
from sindri.schemas import (
    ACTION_FOR_KIND,
    CandidateFile,
    CandidateManifest,
    CheckKind,
    EpisodeBudget,
    EpisodeState,
    EvaluationPolicy,
    Finding,
    FindingTransition,
    FormalMode,
    Observation,
    ObservationAction,
    Requirement,
    TaskManifest,
    candidate_source_hash,
    observation_execution_key,
)
from sindri.schemas._base import Record


def H(byte: str) -> str:
    return "sha256:" + byte * 32


@dataclass(frozen=True)
class Ref:
    """The content_id of an earlier spec item, or one of its JSON fields."""

    name: str
    field: str | None = None


Spec = dict[str, tuple[type[Record], dict[str, Any]]]
Bundle = dict[str, Record]

ZERO = dict.fromkeys(
    ("tokens", "tool_calls", "candidate_versions", "sim_jobs", "formal_ms", "repair_attempts"), 0
)


def _resolve(value: Any, built: Bundle) -> Any:
    if isinstance(value, Ref):
        record = built[value.name]
        return record.content_id() if value.field is None else record.model_dump(mode="json")[
            value.field
        ]
    if isinstance(value, dict):
        return {k: _resolve(v, built) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_resolve(v, built) for v in value]
    return value


def _rekey(data: dict[str, Any]) -> None:
    mode = data["formal_mode"]
    dep = data["dependency_hash"]
    data["execution_key"] = observation_execution_key(
        candidate_manifest_hash=ContentId(data["candidate_manifest_hash"]),
        source_hash=ContentId(data["source_hash"]),
        dependency_hash=None if dep is None else ContentId(dep),
        policy_hash=ContentId(data["policy_hash"]),
        check_id=data["check_id"],
        configuration_id=data["configuration_id"],
        action=ObservationAction(data["action"]),
        tool_profile_hash=ContentId(data["tool_profile_hash"]),
        tool_image_digest=ContentId(data["tool_image_digest"]),
        adapter_hash=ContentId(data["adapter_hash"]),
        evaluator_bundle_hash=ContentId(data["evaluator_bundle_hash"]),
        seed=data["seed"],
        formal_mode=None if mode is None else FormalMode(mode),
        formal_depth=data["formal_depth"],
        wall_time_limit_ms=data["wall_time_limit_ms"],
    )


def seal(spec: Spec) -> Bundle:
    built: Bundle = {}
    for name, (model, data) in spec.items():
        resolved = _resolve(data, built)
        if model is CandidateManifest:
            files = [CandidateFile.model_validate(f) for f in resolved["files"]]
            resolved["source_hash"] = candidate_source_hash(files)
        if model is Observation:
            _rekey(resolved)
        built[name] = model.model_validate(resolved)
    return built


def records(spec: Spec) -> list[Record]:
    return list(seal(spec).values())


def data(spec: Spec, name: str) -> dict[str, Any]:
    """The mutable spec data of one item (edit before sealing)."""
    return spec[name][1]


def add(spec: Spec, name: str, model: type[Record], body: dict[str, Any]) -> None:
    spec[name] = (model, body)


def add_after(spec: Spec, after: str, name: str, model: type[Record],
              body: dict[str, Any]) -> None:
    """Insert so that later items may reference it (seal() builds in spec order)."""
    items = list(spec.items())
    at = [n for n, _ in items].index(after) + 1
    items.insert(at, (name, (model, body)))
    spec.clear()
    spec.update(items)


def clone(spec: Spec, source: str, name: str, **changes: Any) -> None:
    model, body = spec[source]
    new = copy.deepcopy(body)
    new.update(changes)
    spec[name] = (model, new)


def remove(spec: Spec, *names: str) -> None:
    for name in names:
        del spec[name]


# ---- record bodies -----------------------------------------------------------------------------

RIGHTS = {
    "licence": "Apache-2.0",
    "written_agreement_ref": None,
    "training_allowed": True,
    "evaluation_allowed": True,
    "redistribution_allowed": True,
    "customer_restricted": False,
}
AUTHOR = {
    "model": "nemotron-3-super",
    "model_version": "2026-09-01",
    "temperature_millis": 800,
    "seed": 1234,
    "provenance_ref": "model_gateway:call/7f3a",
    "training_allowed": True,
}


def task(task_id: str, version: int, contract: str, **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "task_id": task_id,
        "family_id": "fifo",
        "lineage_id": "fifo-sync",
        "variant_id": "w-d-matrix",
        "manifest_version": version,
        "supersedes": None,
        "authority_mode": "engineering_intent",
        "split": "train",
        "task_type": "modification",
        "source": {"kind": "repo_cut", "repo": "https://example.org/fifo-ip",
                   "commit": "3f2a9c1e5b7d4a6f8e0c2b4d6f8a0c2e4b6d8f0a"},
        "rights": dict(RIGHTS),
        "golden_hash": None,
        "contract_id": "ct_fifo_0001",
        "approved_contract_hash": contract,
        "allowed_edit_paths": ["rtl/fifo"],
        "requirement_ids": ["R03", "R17"],
    }
    body.update(changes)
    return body


def requirement(task_id: str, rid: str, version: int = 1, **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "task_id": task_id,
        "requirement_id": rid,
        "requirement_version": version,
        "supersedes": None,
        "source_ref": f"contract:{task_id}/{rid}",
        "original_text": f"{rid} original wording",
        "normalized_semantics": f"{rid} normalized semantics",
        "legal_environment": [],
        "assumptions": [],
        "applicability": {"kind": "all_supported_configs"},
        "mandatory": True,
        "disposition": "approved",
    }
    body.update(changes)
    return body


def config(cfg_id: str, width: Any, depth: Any) -> dict[str, Any]:
    return {"configuration_id": cfg_id,
            "assignments": [{"name": "WIDTH", "value": width}, {"name": "DEPTH", "value": depth}]}


def check(check_id: str, kind: str, cfgs: list[str], *, mandatory: bool = True,
          visibility: str = "development", profile: str = "tp_verilator_v0",
          formal_mode: str | None = None, depth: int | None = None) -> dict[str, Any]:
    return {"check_id": check_id, "kind": kind, "mandatory": mandatory, "visibility": visibility,
            "tool_profile_id": profile, "configuration_ids": cfgs, "formal_mode": formal_mode,
            "depth": depth}


ALL_CFGS = ["cfg_w8_d4", "cfg_w32_d8", "cfg_w1_d2"]


def policy(policy_id: str, version: int, task_id: str, contract: str,
           **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "policy_id": policy_id,
        "policy_version": version,
        "supersedes": None,
        "task_id": task_id,
        "contract_hash": contract,
        "configurations": [config("cfg_w8_d4", 8, 4), config("cfg_w32_d8", 32, 8),
                           config("cfg_w1_d2", 1, 2)],
        "checks": [
            check("chk_lint", "lint", list(ALL_CFGS), profile="tp_verilator_lint_v0"),
            check("chk_sim", "directed_sim", list(ALL_CFGS)),
            check("chk_formal", "formal", ["cfg_w8_d4", "cfg_w32_d8"], visibility="hidden",
                  profile="tp_sby_bmc_v0", formal_mode="bmc", depth=24),
            check("chk_area", "quality", ["cfg_w8_d4"], mandatory=False, visibility="hidden",
                  profile="tp_yosys_v0"),
        ],
        "environment_assumptions": [],
        "obligations": [
            {"obligation_id": "ob_r03", "requirement_id": "R03", "check_ids": ["chk_sim"]},
            {"obligation_id": "ob_r17", "requirement_id": "R17",
             "check_ids": ["chk_formal", "chk_sim", "chk_area"]},
        ],
        "exceptions": [{"exception_id": "ex_formal_w32",
                        "excludes": [{"check_id": "chk_formal", "configuration_id": "cfg_w32_d8"}],
                        "justification": "BMC at WIDTH=32 exceeds the profile budget",
                        "approved_by": "reviewer:fifo-owner"}],
    }
    body.update(changes)
    return body


def candidate(cand_id: str, role: str, episode: str | None, parent: str | None,
              file_hash: str, task_id: str = "fifo_0001", **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "candidate_id": cand_id,
        "task_id": task_id,
        "producer_role": role,
        "episode_id": episode,
        "parent_candidate_id": parent,
        "patch_hash": None if parent is None else H("5e"),
        "files": [{"path": "rtl/fifo/fifo.sv", "hash": file_hash}],
        "source_hash": H("00"),  # recomputed by seal()
        "dependency_hash": H("d0"),
        "author": dict(AUTHOR),
    }
    body.update(changes)
    return body


def observation(obs_id: str, cand: str, check_id: str, cfg: str, kind: str, status: str,
                report: dict[str, Any] | None, *, visibility: str = "development",
                profile: str = "tp_verilator_v0", policy_ref: str = "pol_v2",
                policy_id: str = "ep_fifo_main", **changes: Any) -> dict[str, Any]:
    formal = kind == "formal"
    body: dict[str, Any] = {
        "schema_version": 1,
        "observation_id": obs_id,
        "candidate_id": Ref(cand, "candidate_id"),
        "candidate_manifest_hash": Ref(cand),
        "source_hash": Ref(cand, "source_hash"),
        "dependency_hash": Ref(cand, "dependency_hash"),
        "policy_id": policy_id,
        "policy_hash": Ref(policy_ref),
        "check_id": check_id,
        "configuration_id": cfg,
        "check_kind": kind,
        "visibility": visibility,
        "action": ACTION_FOR_KIND[CheckKind(kind)].value,
        "tool_profile_id": profile,
        "tool_profile_hash": H("a4"),
        "tool_image_digest": H("0f"),
        "adapter_version": "adapter 0.1.0",
        "adapter_hash": H("ad"),
        "evaluator_bundle_hash": H("eb"),
        "seed": 1 if kind in ("directed_sim", "random_sim") else None,
        "formal_mode": "bmc" if formal else None,
        "formal_depth": 24 if formal else None,
        "wall_time_limit_ms": 600000,
        "execution_key": H("00"),  # recomputed by seal()
        "started_at": "2026-10-05T09:00:00Z",
        "duration_ms": 1000,
        "status": status,
        "summary": f"{check_id} on {cfg}: {status}",
        "diagnostics": [],
        "diagnostics_truncated": False,
        "log_ref": H("1f"),
        "evidence_refs": [],
        "execution_report": report,
    }
    body.update(changes)
    return body


SIM_PASS = {"report_kind": "simulation", "expected_test_ids": ["t_a"],
            "test_results": [{"test_id": "t_a", "outcome": "PASS"}]}


def formal_report(reached: int, outcome: str, requested: int = 24) -> dict[str, Any]:
    return {"report_kind": "formal", "mode": "bmc", "requested_depth": requested,
            "reached_depth": reached, "proof_closed": None, "expected_property_ids": ["p_a"],
            "property_results": [{"property_id": "p_a", "outcome": outcome}]}


def formal_obs(obs_id: str, cand: str, status: str, cfg: str = "cfg_w8_d4",
               **changes: Any) -> dict[str, Any]:
    if status == "PASS":
        report, evidence = formal_report(24, "PASS"), []
    else:
        report = formal_report(7, "FAIL")
        evidence = [{"kind": "counterexample_trace", "hash": H("8e")}]
    return observation(obs_id, cand, "chk_formal", cfg, "formal", status, report,
                       visibility="hidden", profile="tp_sby_bmc_v0", evidence_refs=evidence,
                       **changes)


def citation(obs_id: str, ref: str) -> dict[str, Any]:
    return {"observation_id": obs_id, "observation_hash": Ref(ref)}


def finding(fid: str, cand: str, rid: str, producer: dict[str, Any],
            citations: list[dict[str, Any]], **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "finding_id": fid,
        "task_id": "fifo_0001",
        "candidate_id": Ref(cand, "candidate_id"),
        "candidate_manifest_hash": Ref(cand),
        "requirement_id": rid,
        "claim": f"{fid}: output may change while stalled",
        "uncertainty": "medium",
        "producer": producer,
        "correctness_citations": citations,
        "supporting_evidence": (
            [] if citations
            else [{"kind": "trace", "hash": H("88"), "cycle_window": None}]
        ),
        "derived_from": None,
    }
    body.update(changes)
    return body


def model_producer(role: str) -> dict[str, Any]:
    return {"kind": "model", "role": role, "model": "nemotron-3-super",
            "model_version": "2026-09-01", "provenance_ref": "model_gateway:call/9b21",
            "training_allowed": True}


def transition(finding_ref: str, fid: str, seq: int, prev: str | None, frm: str, to: str,
               **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": 1,
        "finding_id": fid,
        "finding_hash": Ref(finding_ref),
        "sequence": seq,
        "previous_transition_hash": None if prev is None else Ref(prev),
        "from_status": frm,
        "to_status": to,
        "proposed_check": None,
        "deciding_citations": [],
        "drop_reason": None,
        "superseded_by": None,
    }
    body.update(changes)
    return body


def existing_check(check_id: str = "chk_formal", cfg: str = "cfg_w8_d4",
                   confirming: str = "PASS", policy_ref: str = "pol_v2") -> dict[str, Any]:
    return {"proposal_kind": "existing_policy_check", "policy_hash": Ref(policy_ref),
            "check_id": check_id, "configuration_id": cfg, "confirming_status": confirming}


def budget(**limits: int) -> dict[str, Any]:
    wall = limits.pop("wall", 3600000)
    return {"schema_version": 1, "limits": {**ZERO, **limits}, "wall_clock_limit_ms": wall}


def binding(cand: str) -> dict[str, Any]:
    return {"candidate_id": Ref(cand, "candidate_id"), "candidate_manifest_hash": Ref(cand)}


def job(job_id: str, request: str, cand: str | None, **reserved: int) -> dict[str, Any]:
    return {"job_id": job_id, "request_hash": H(request),
            "candidate": None if cand is None else binding(cand),
            "reserved": {**ZERO, **reserved}}


def state(episode: str, seq: int, prev: str | None, status: str, *, budget_ref: str,
          spent: dict[str, int] | None = None, elapsed: int = 0, active: str | None = None,
          best: str | None = None, jobs: Iterable[dict[str, Any]] = (),
          resume: str | None = None, abort: str | None = None, task_id: str = "fifo_0001",
          policy_ref: str = "pol_v2", policy_id: str = "ep_fifo_main") -> dict[str, Any]:
    pending = list(jobs)
    reserved = dict(ZERO)
    for j in pending:
        for dim, amount in j["reserved"].items():
            reserved[dim] += amount
    return {
        "schema_version": 1,
        "episode_id": episode,
        "task_id": task_id,
        "sequence": seq,
        "previous_state_hash": None if prev is None else Ref(prev),
        "policy_id": policy_id,
        "policy_hash": Ref(policy_ref),
        "budget_hash": Ref(budget_ref),
        "solver_config_hash": H("5c"),
        "state": status,
        "resume_state": resume,
        "abort_reason": abort,
        "active_candidate": None if active is None else binding(active),
        "best_candidate": None if best is None else binding(best),
        "pending_jobs": pending,
        "spent": {**ZERO, **(spent or {})},
        "reserved": reserved,
        "wall_clock_elapsed_ms": elapsed,
        "last_failure_signature": None,
        "failure_repeat_count": 0,
        "checkpoint_ref": None,
    }


# ---- the positive bundle -----------------------------------------------------------------------

E1_PLAN: list[tuple[str, dict[str, Any]]] = [
    # (state, keyword arguments for state()); sequence and predecessor are filled in order.
    ("PREPARE", {}),
    ("PLAN", {"active": "cand_seed", "spent": {"tokens": 100}, "elapsed": 1000}),
    ("IMPLEMENT", {"active": "cand_seed", "spent": {"tokens": 200, "tool_calls": 1},
                   "elapsed": 2000}),
    ("WAITING", {"active": "cand_seed", "spent": {"tokens": 200, "tool_calls": 1},
                 "elapsed": 3000, "resume": "IMPLEMENT",
                 "jobs": [job("job_model_1", "71", None, tokens=100)]}),
    ("IMPLEMENT", {"active": "cand_seed", "spent": {"tokens": 300, "tool_calls": 2},
                   "elapsed": 4000}),
    ("DEV_CHECK", {"active": "cand_v1", "spent": {"tokens": 300, "tool_calls": 3,
                                                  "candidate_versions": 1, "sim_jobs": 1},
                   "elapsed": 5000}),
    ("TRIAGE", {"active": "cand_v1", "spent": {"tokens": 400, "tool_calls": 4,
                                               "candidate_versions": 1, "sim_jobs": 1},
                "elapsed": 6000}),
    ("REPAIR", {"active": "cand_v1", "spent": {"tokens": 500, "tool_calls": 5,
                                               "candidate_versions": 1, "sim_jobs": 1,
                                               "repair_attempts": 1}, "elapsed": 7000}),
    ("DEV_CHECK", {"active": "cand_v2", "spent": {"tokens": 600, "tool_calls": 6,
                                                  "candidate_versions": 2, "sim_jobs": 2,
                                                  "formal_ms": 100000, "repair_attempts": 1},
                   "elapsed": 8000, "jobs": [job("job_sim_2", "72", "cand_v2", sim_jobs=1)]}),
    ("SUBMIT", {"active": "cand_v2", "spent": {"tokens": 600, "tool_calls": 8,
                                               "candidate_versions": 2, "sim_jobs": 3,
                                               "formal_ms": 100000, "repair_attempts": 1},
                "elapsed": 9000}),
    ("JUDGE", {"active": "cand_v2", "spent": {"tokens": 600, "tool_calls": 9,
                                              "candidate_versions": 2, "sim_jobs": 3,
                                              "formal_ms": 200000, "repair_attempts": 1},
               "elapsed": 10000}),
    ("RECORD", {"active": "cand_v2", "spent": {"tokens": 600, "tool_calls": 10,
                                               "candidate_versions": 2, "sim_jobs": 3,
                                               "formal_ms": 200000, "repair_attempts": 1},
                "elapsed": 11000}),
    # Exact-limit spending: tool_calls == limit 10 is within budget (<=, not <).
    ("COMPLETED", {"active": "cand_v2", "best": "cand_v2",
                   "spent": {"tokens": 600, "tool_calls": 10, "candidate_versions": 2,
                             "sim_jobs": 3, "formal_ms": 200000, "repair_attempts": 1},
                   "elapsed": 12000}),
]

E2_PLAN: list[tuple[str, dict[str, Any]]] = [
    ("PREPARE", {}),
    ("PLAN", {"spent": {"tool_calls": 2}, "elapsed": 1000}),
    ("IMPLEMENT", {"spent": {"tool_calls": 4}, "elapsed": 2000}),
    # Truthful and exempt: tool_calls 6 >= its positive limit 5 (zero-limit dimensions disabled).
    ("ABORTED", {"spent": {"tool_calls": 6}, "elapsed": 3000, "abort": "budget_exhausted"}),
]


def episode(spec: Spec, episode_id: str, plan: list[tuple[str, dict[str, Any]]],
            budget_ref: str, **common: Any) -> None:
    """(Re)write one episode chain: items `<episode>_s<n>` linked in order."""
    for name in [n for n in spec if n.startswith(f"{episode_id}_s")]:
        del spec[name]
    prev = None
    for seq, (status, kwargs) in enumerate(copy.deepcopy(plan)):
        name = f"{episode_id}_s{seq}"
        add(spec, name, EpisodeState,
            state(episode_id, seq, prev, status, budget_ref=budget_ref, **{**common, **kwargs}))
        prev = name


def positive_spec() -> Spec:
    """A fresh, fully coherent spec. Every test that edits it gets its own copy."""
    spec: Spec = {}
    add(spec, "task_v1", TaskManifest, task("fifo_0001", 1, H("a1")))
    add(spec, "task_v2", TaskManifest,
        task("fifo_0001", 2, H("a2"), supersedes=Ref("task_v1")))
    add(spec, "task_m1", TaskManifest, task(
        "fifo_0001_m1", 1, H("a3"), variant_id="w-d-matrix-m1", contract_id="ct_fifo_0001_m1",
        source={"kind": "mutation", "parent_task_id": "fifo_0001", "operator": "invert_full"},
        requirement_ids=["R03"]))

    add(spec, "req_r03", Requirement, requirement("fifo_0001", "R03"))
    scope = {"kind": "parameter_scope", "parameters": [{"name": "WIDTH", "values": [8, 32]}]}
    add(spec, "req_r17_v1", Requirement, requirement("fifo_0001", "R17", applicability=scope))
    add(spec, "req_r17_v2", Requirement, requirement(
        "fifo_0001", "R17", 2, supersedes=Ref("req_r17_v1"), applicability=copy.deepcopy(scope),
        normalized_semantics="R17 normalized semantics, revised wording"))
    add(spec, "req_m1_r03", Requirement, requirement("fifo_0001_m1", "R03"))

    add(spec, "pol_v1", EvaluationPolicy, policy("ep_fifo_main", 1, "fifo_0001", H("a1")))
    add(spec, "pol_v2", EvaluationPolicy, policy(
        "ep_fifo_main", 2, "fifo_0001", H("a2"), supersedes=Ref("pol_v1")))

    add(spec, "cand_seed", CandidateManifest,
        candidate("c_fifo_0001_seed", "reconstructor", None, None, H("f1")))
    add(spec, "cand_v1", CandidateManifest,
        candidate("c_fifo_0001_e1_v1", "solver", "e1", "c_fifo_0001_seed", H("f2")))
    add(spec, "cand_v2", CandidateManifest,
        candidate("c_fifo_0001_e1_v2", "solver", "e1", "c_fifo_0001_e1_v1", H("f3")))
    add(spec, "cand_oracle", CandidateManifest,
        candidate("c_fifo_0001_oracle", "architecture_explorer", None, None, H("f4")))
    add(spec, "cand_explorer", CandidateManifest,
        candidate("c_fifo_0001_e1_x", "architecture_explorer", "e1", "c_fifo_0001_e1_v1",
                  H("f5")))

    add(spec, "ob_simv2", Observation,
        observation("ob_simv2", "cand_v2", "chk_sim", "cfg_w8_d4", "directed_sim", "PASS",
                    SIM_PASS))
    add(spec, "ob_formalv2", Observation, formal_obs("ob_formalv2", "cand_v2", "PASS"))
    add(spec, "ob_formalv1fail", Observation, formal_obs("ob_formalv1fail", "cand_v1", "FAIL"))
    add(spec, "ob_simtimeout", Observation,
        observation("ob_simtimeout", "cand_v2", "chk_sim", "cfg_w32_d8", "directed_sim",
                    "TIMEOUT", None, duration_ms=600000))

    # F1: proposes an existing obligated check, confirmed by a matching PASS.
    add(spec, "F1", Finding, finding("F1", "cand_v2", "R17", model_producer("triage"),
                                     [citation("ob_simv2", "ob_simv2")]))
    add(spec, "tr_F1_1", FindingTransition, transition(
        "F1", "F1", 1, None, "hypothesis", "check_proposed", proposed_check=existing_check()))
    add(spec, "tr_F1_2", FindingTransition, transition(
        "F1", "F1", 2, "tr_F1_1", "check_proposed", "confirmed",
        deciding_citations=[citation("ob_formalv2", "ob_formalv2")]))
    # F2: solver finding; a development probe, then dropped (never decided).
    add(spec, "F2", Finding, finding("F2", "cand_v2", "R03", model_producer("solver"),
                                     [citation("ob_simv2", "ob_simv2")]))
    add(spec, "tr_F2_1", FindingTransition, transition(
        "F2", "F2", 1, None, "hypothesis", "check_proposed",
        proposed_check={"proposal_kind": "development_probe", "policy_hash": Ref("pol_v2"),
                        "action": "run_sim", "configuration_id": "cfg_w8_d4",
                        "test_ids": ["t_stall"], "property_ids": [],
                        "rationale": "hold out_ready low for 8 cycles"}))
    add(spec, "tr_F2_2", FindingTransition, transition(
        "F2", "F2", 2, "tr_F2_1", "check_proposed", "dropped", drop_reason="no_executable_check"))
    # F3 (reviewer, may cite hidden evidence) superseded by F4, which is derived from it.
    add(spec, "F3", Finding, finding(
        "F3", "cand_v1", "R17",
        {"kind": "human", "role": "reviewer", "reviewer_ref": "reviewer:fifo-owner",
         "provenance_ref": "review:fifo/12", "training_allowed": False},
        [citation("ob_formalv1fail", "ob_formalv1fail")]))
    add(spec, "F4", Finding, finding(
        "F4", "cand_v2", "R17",
        {"kind": "component", "role": "critic", "component": "lint-critic",
         "component_version": "0.1.0", "component_hash": H("cc"),
         "provenance_ref": "component:lint-critic/1", "training_allowed": False},
        [], derived_from="F3"))
    add(spec, "tr_F3_1", FindingTransition, transition(
        "F3", "F3", 1, None, "hypothesis", "dropped", drop_reason="superseded", superseded_by="F4"))

    add(spec, "budget_main", EpisodeBudget, budget(
        tokens=1000, tool_calls=10, candidate_versions=3, sim_jobs=4, formal_ms=600000,
        repair_attempts=2))
    add(spec, "budget_mixed", EpisodeBudget, budget(
        tool_calls=5, candidate_versions=2, sim_jobs=2, repair_attempts=1, wall=100000))
    episode(spec, "e1", E1_PLAN, "budget_main")
    episode(spec, "e2", E2_PLAN, "budget_mixed")
    return spec


# ---- optional extra structure used by several mutations ----------------------------------------


def add_m1_candidate(spec: Spec) -> None:
    add_after(spec, "cand_explorer", "cand_m1", CandidateManifest, candidate(
        "c_fifo_0001_m1_seed", "reconstructor", None, None, H("f9"), task_id="fifo_0001_m1"))


def add_m1_policy(spec: Spec) -> None:
    body = policy("ep_fifo_m1", 1, "fifo_0001_m1", H("a3"))
    body["obligations"] = [body["obligations"][0]]  # R03 only
    add_after(spec, "pol_v2", "pol_m1", EvaluationPolicy, body)


def add_read_only_task(spec: Spec) -> None:
    add(spec, "task_ro", TaskManifest, task(
        "fifo_0002", 1, H("b1"), family_id="fifo-ro", task_type="comprehension",
        allowed_edit_paths=[], requirement_ids=["R03"], contract_id="ct_fifo_0002"))
    add(spec, "req_ro_r03", Requirement, requirement("fifo_0002", "R03"))
