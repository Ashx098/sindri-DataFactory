"""SIN-P1.1-009 CT-1: every ContentId field in the P1.1 schemas is classified exactly once.

H1 is resolved by XR-B2; H2 is deferred to a named later owner (packet table D); H3 is computed
in-record or compared by XR-O1. A new ContentId field fails this test until it is classified,
so no hash reference can silently escape the cross-record contract.
"""

import typing
from collections.abc import Iterable, Iterator

from pydantic import BaseModel

import sindri.schemas as schemas
from sindri.core.ids import ContentId

H1 = {
    "TaskManifest.supersedes", "Requirement.supersedes", "EvaluationPolicy.supersedes",
    "Observation.candidate_manifest_hash", "Observation.policy_hash",
    "ObservationCitation.observation_hash",
    "FindingTransition.finding_hash", "FindingTransition.previous_transition_hash",
    "ExistingPolicyCheck.policy_hash", "DevelopmentProbeRequest.policy_hash",
    "Finding.candidate_manifest_hash",
    "EpisodeState.previous_state_hash", "EpisodeState.policy_hash", "EpisodeState.budget_hash",
    "CandidateBinding.candidate_manifest_hash",
}
H2 = {  # owner per packet table D
    "TaskManifest.approved_contract_hash": "D6",
    "EvaluationPolicy.contract_hash": "D6",
    "TaskManifest.golden_hash": "D7",
    "CandidateManifest.patch_hash": "D7",
    "CandidateFile.hash": "D7",
    "CandidateManifest.dependency_hash": "D8",
    "Observation.tool_profile_hash": "D5",
    "Observation.tool_image_digest": "D5",
    "Observation.adapter_hash": "D5",
    "Observation.evaluator_bundle_hash": "D4",
    "Observation.log_ref": "D7",
    "EvidenceRef.hash": "D7",
    "SupportingArtifact.hash": "D7",
    "ComponentProducer.component_hash": "D13",
    "PendingJob.request_hash": "D3",
    "EpisodeState.solver_config_hash": "D9",
    "EpisodeState.checkpoint_ref": "D7",
    "EpisodeState.last_failure_signature": "D12",
}
H3 = {
    "CandidateManifest.source_hash", "Observation.execution_key",
    "Observation.source_hash", "Observation.dependency_hash",
}


def _mentions_content_id(annotation: object) -> bool:
    return annotation is ContentId or any(
        _mentions_content_id(a) for a in typing.get_args(annotation)
    )


def _nested_models(annotation: object) -> Iterator[type[BaseModel]]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        yield annotation
    for arg in typing.get_args(annotation):
        yield from _nested_models(arg)


def content_id_fields(roots: Iterable[type[BaseModel]]) -> list[str]:
    seen: set[type[BaseModel]] = set()
    found: list[str] = []

    def walk(model: type[BaseModel]) -> None:
        if model in seen:
            return
        seen.add(model)
        for name, field in model.model_fields.items():
            if _mentions_content_id(field.annotation):
                found.append(f"{model.__name__}.{name}")
            for nested in _nested_models(field.annotation):
                walk(nested)

    for root in roots:
        walk(root)
    return found


def _p1_1_models() -> list[type[BaseModel]]:
    exported = (getattr(schemas, n) for n in schemas.__all__)
    return [m for m in exported if isinstance(m, type) and issubclass(m, BaseModel)
            and m is not schemas.Violation]


def unclassified(fields: Iterable[str]) -> list[str]:
    return sorted(f for f in fields if f not in H1 | set(H2) | H3)


def test_classes_are_disjoint() -> None:
    assert not (H1 & set(H2)) and not (H1 & H3) and not (set(H2) & H3)


def test_every_content_id_field_is_classified_exactly_once() -> None:
    fields = content_id_fields(_p1_1_models())
    assert len(fields) == len(set(fields)) == 37
    assert unclassified(fields) == []
    assert set(fields) == H1 | set(H2) | H3  # nothing stale either


def test_an_unclassified_field_fails() -> None:
    class Observation(schemas.Observation):  # same name: only the new field is unknown
        new_artifact_hash: ContentId

    assert unclassified(content_id_fields([Observation])) == ["Observation.new_artifact_hash"]
