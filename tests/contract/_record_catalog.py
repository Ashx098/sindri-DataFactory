"""Catalog of every P1.1 top-level record for the SIN-P1.1-008 serialization tests.

Each entry is one valid record as JSON-native data: the adapted master §20 fixtures plus generated
variants that exercise every discriminated-union branch and the edge shapes named in the packet
(zero-parameter configuration, candidate-less WAITING job, ABORTED, first/derived candidates, ...).
Every entry is validated at import time, so a broken variant fails loudly instead of being skipped.
"""

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sindri.core.ids import ContentId
from sindri.schemas import (
    CandidateFile,
    CandidateManifest,
    EpisodeBudget,
    EpisodeState,
    EvaluationPolicy,
    Finding,
    FindingTransition,
    Observation,
    ObservationAction,
    Requirement,
    TaskManifest,
    candidate_source_hash,
    observation_execution_key,
)
from sindri.schemas.policy import FormalMode

EXAMPLES = Path(__file__).parent / "examples"

# S6: records with a domain revision chain (revision field + supersedes).
# schema_version is 1 for every record.
DOMAIN_REVISION_FIELD: dict[type[BaseModel], str] = {
    TaskManifest: "manifest_version",
    Requirement: "requirement_version",
    EvaluationPolicy: "policy_version",
}
TOP_LEVEL_RECORDS: tuple[type[BaseModel], ...] = (
    TaskManifest, Requirement, EvaluationPolicy, CandidateManifest, Observation, Finding,
    FindingTransition, EpisodeBudget, EpisodeState,
)


def H(byte: str) -> str:
    return "sha256:" + byte * 32


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / f"{name}.json").read_text())
    return data


@dataclass(frozen=True)
class Entry:
    name: str
    model: type[BaseModel]
    data: dict[str, Any]

    def build(self) -> BaseModel:
        return self.model.model_validate(copy.deepcopy(self.data))


def _variant(base: dict[str, Any], **changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(base)
    data.update(changes)
    return data


def _rekey_observation(data: dict[str, Any]) -> dict[str, Any]:
    mode = data["formal_mode"]
    data["execution_key"] = observation_execution_key(
        candidate_manifest_hash=ContentId(data["candidate_manifest_hash"]),
        source_hash=ContentId(data["source_hash"]),
        dependency_hash=(
            None if data["dependency_hash"] is None else ContentId(data["dependency_hash"])
        ),
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
    return data


def source_hash_of(files: list[dict[str, str]]) -> str:
    return str(candidate_source_hash(CandidateFile.model_validate(f) for f in files))


def _task_variants() -> list[Entry]:
    base = load("task_manifest")
    sources = {
        "commit_feature": {"kind": "commit_feature", "repo": "https://x/y", "commit": "d" * 64},
        "commit_fix": {"kind": "commit_fix", "repo": "https://x/y", "commit": "c" * 40},
        "mutation": {"kind": "mutation", "parent_task_id": "pktfr_0193", "operator": "flip"},
        "generator": {"kind": "generator", "generator_id": "fifo", "generator_version": "1.0"},
        "use_case": {"kind": "use_case", "intake_ref": "use_case:12"},
    }
    out = [Entry(f"TaskManifest/source={k}", TaskManifest, _variant(base, source=v))
           for k, v in sources.items()]
    out.append(Entry("TaskManifest/read-only-empty-edit-scope", TaskManifest,
                     _variant(base, task_type="comprehension", allowed_edit_paths=[])))
    out.append(Entry("TaskManifest/revision-2", TaskManifest,
                     _variant(base, manifest_version=2, supersedes=H("a1"))))
    return out


def _requirement_variants() -> list[Entry]:
    base = load("requirement")
    return [
        Entry("Requirement/all-supported-configs", Requirement, _variant(
            base, applicability={"kind": "all_supported_configs"}, legal_environment=[],
            assumptions=[])),
        Entry("Requirement/exact-scalars", Requirement, _variant(
            base, applicability={"kind": "parameter_scope",
                                 "parameters": [{"name": "MODE", "values": [True, 1, "1"]}]})),
        Entry("Requirement/revision-2", Requirement, _variant(
            base, requirement_version=2, supersedes=H("a2"), disposition="ambiguous")),
    ]


def _policy_variants() -> list[Entry]:
    base = load("evaluation_policy")
    zero = _variant(
        base,
        configurations=[{"configuration_id": "cfg_default", "assignments": []}],
        checks=[{"check_id": "chk_sim", "kind": "directed_sim", "mandatory": True,
                 "visibility": "development", "tool_profile_id": "tp_verilator_v0",
                 "configuration_ids": ["cfg_default"], "formal_mode": None, "depth": None},
                {"check_id": "chk_prove", "kind": "formal", "mandatory": False,
                 "visibility": "hidden", "tool_profile_id": "tp_sby_v0",
                 "configuration_ids": ["cfg_default"], "formal_mode": "prove", "depth": None}],
        obligations=[{"obligation_id": "sim_basic", "requirement_id": "R01",
                      "check_ids": ["chk_sim", "chk_prove"]}],
        exceptions=[], environment_assumptions=[],
    )
    return [
        Entry("EvaluationPolicy/zero-parameter-cfg_default", EvaluationPolicy, zero),
        Entry("EvaluationPolicy/revision-2", EvaluationPolicy,
              _variant(base, policy_version=2, supersedes=H("a3"))),
    ]


def _candidate_variants() -> list[Entry]:
    base = load("candidate_manifest")
    return [
        Entry("CandidateManifest/first-no-parent", CandidateManifest,
              _variant(base, parent_candidate_id=None, patch_hash=None, dependency_hash=None)),
        Entry("CandidateManifest/reconstructor", CandidateManifest, _variant(
            base, producer_role="reconstructor", episode_id=None, parent_candidate_id=None,
            patch_hash=None)),
        Entry("CandidateManifest/oracle-explorer", CandidateManifest, _variant(
            base, producer_role="architecture_explorer", episode_id=None)),
    ]


def _observation_variants() -> list[Entry]:
    base = load("observation")

    def obs(name: str, **changes: Any) -> Entry:
        data = _variant(base, **changes)
        return Entry(f"Observation/{name}", Observation, _rekey_observation(data))

    non_formal = {"formal_mode": None, "formal_depth": None}
    sim_pass = {"report_kind": "simulation", "expected_test_ids": ["t_a", "t_b"],
                "test_results": [{"test_id": "t_a", "outcome": "PASS"},
                                 {"test_id": "t_b", "outcome": "PASS"}]}
    return [
        obs("sim-pass", check_kind="random_sim", action="run_sim", seed=17, status="PASS",
            diagnostics=[], evidence_refs=[], execution_report=sim_pass, **non_formal),
        obs("synth-pass", check_kind="synthesis", action="synth", seed=None, status="PASS",
            diagnostics=[], evidence_refs=[], **non_formal,
            execution_report={"report_kind": "structural", "error_count": 0, "warning_count": 0,
                              "latch_count": 2, "blackbox_count": 0}),
        obs("equivalence-pass", check_kind="equivalence", action="check_equiv", seed=None,
            status="PASS", diagnostics=[], evidence_refs=[], **non_formal,
            execution_report={"report_kind": "equivalence", "proved": True}),
        obs("tool-error-no-report", status="TOOL_ERROR", evidence_refs=[], execution_report=None,
            diagnostics=[{"severity": "error", "category": "infrastructure", "code": None,
                          "message": "license expired", "path": None, "line": None}]),
        obs("prove-inconclusive", status="INCONCLUSIVE", formal_mode="prove", formal_depth=None,
            diagnostics=[], evidence_refs=[],
            execution_report={"report_kind": "formal", "mode": "prove", "requested_depth": None,
                              "reached_depth": None, "proof_closed": False,
                              "expected_property_ids": ["R03_sva"],
                              "property_results": [{"property_id": "R03_sva",
                                                    "outcome": "INCONCLUSIVE"}]}),
    ]


def _finding_variants() -> list[Entry]:
    base = load("finding")
    return [
        Entry("Finding/component-producer", Finding, _variant(base, producer={
            "kind": "component", "role": "triage", "component": "triage-normalizer",
            "component_version": "0.1.0", "component_hash": H("cc"), "provenance_ref": "b:42",
            "training_allowed": True})),
        Entry("Finding/human-producer-with-citation", Finding, _variant(
            base, producer={"kind": "human", "role": "reviewer", "reviewer_ref": "reviewer:a",
                            "provenance_ref": "review:1", "training_allowed": False},
            correctness_citations=[{"observation_id": "ob_88121", "observation_hash": H("0b")}],
            derived_from="F41")),
    ]


def _transition_variants() -> list[Entry]:
    base = load("finding_transition_check_proposed")
    existing = _variant(base, proposed_check={
        "proposal_kind": "existing_policy_check", "policy_hash": H("b9"), "check_id": "chk_stall",
        "configuration_id": "cfg_w8_d8", "confirming_status": "FAIL"})
    formal_probe = _variant(base, proposed_check={
        "proposal_kind": "development_probe", "policy_hash": H("b9"), "action": "run_formal",
        "configuration_id": "cfg_w8_d8", "test_ids": [], "property_ids": ["R17_sva"],
        "rationale": "prove stall stability"})
    dropped = _variant(base, to_status="dropped", proposed_check=None,
                       drop_reason="superseded", superseded_by="F43")
    return [
        Entry("FindingTransition/existing-policy-check", FindingTransition, existing),
        Entry("FindingTransition/formal-probe", FindingTransition, formal_probe),
        Entry("FindingTransition/dropped-superseded", FindingTransition, dropped),
    ]


def _episode_variants() -> list[Entry]:
    base = load("episode_state")
    zero = dict.fromkeys(base["reserved"], 0)
    job = copy.deepcopy(base["pending_jobs"][0])
    job["candidate"] = None
    return [
        Entry("EpisodeState/waiting-plan-candidate-less-job", EpisodeState, _variant(
            base, resume_state="PLAN", active_candidate=None, best_candidate=None,
            pending_jobs=[job], reserved=job["reserved"])),
        Entry("EpisodeState/aborted", EpisodeState, _variant(
            base, state="ABORTED", resume_state=None, abort_reason="stagnation",
            pending_jobs=[], reserved=zero)),
        Entry("EpisodeState/prepare-head", EpisodeState, _variant(
            base, state="PREPARE", resume_state=None, sequence=0, previous_state_hash=None,
            active_candidate=None, best_candidate=None, pending_jobs=[], reserved=zero,
            last_failure_signature=None, failure_repeat_count=0, checkpoint_ref=None)),
    ]


def _budget_variants() -> list[Entry]:
    base = load("episode_budget")
    return [Entry("EpisodeBudget/zero-additive-limits", EpisodeBudget, _variant(
        base, limits=dict.fromkeys(base["limits"], 0)))]


FIXTURES: tuple[Entry, ...] = (
    Entry("TaskManifest/fixture", TaskManifest, load("task_manifest")),
    Entry("Requirement/fixture", Requirement, load("requirement")),
    Entry("EvaluationPolicy/fixture", EvaluationPolicy, load("evaluation_policy")),
    Entry("CandidateManifest/fixture", CandidateManifest, load("candidate_manifest")),
    Entry("Observation/fixture", Observation, load("observation")),
    Entry("Finding/fixture", Finding, load("finding")),
    Entry("FindingTransition/fixture-check-proposed", FindingTransition,
          load("finding_transition_check_proposed")),
    Entry("FindingTransition/fixture-confirmed", FindingTransition,
          load("finding_transition_confirmed")),
    Entry("EpisodeBudget/fixture", EpisodeBudget, load("episode_budget")),
    Entry("EpisodeState/fixture", EpisodeState, load("episode_state")),
)

_GENERATORS: tuple[Callable[[], list[Entry]], ...] = (
    _task_variants, _requirement_variants, _policy_variants, _candidate_variants,
    _observation_variants, _finding_variants, _transition_variants, _episode_variants,
    _budget_variants,
)
VARIANTS: tuple[Entry, ...] = tuple(e for gen in _GENERATORS for e in gen())
CATALOG: tuple[Entry, ...] = FIXTURES + VARIANTS

for _entry in CATALOG:  # fail loudly at import if any catalog entry is invalid
    _entry.build()

# Explicit raises, not `assert`: support modules are not rewritten by pytest, so a plain assert
# would vanish under `python -O` (P1.1-G B2).
if {e.model for e in CATALOG} != set(TOP_LEVEL_RECORDS):
    raise AssertionError("catalog must cover every record")
if len({e.name for e in CATALOG}) != len(CATALOG):
    raise AssertionError("catalog names must be unique")
