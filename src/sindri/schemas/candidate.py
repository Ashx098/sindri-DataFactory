"""CandidateManifest: one exact, immutable candidate design version.

Every observation and judgement binds to a candidate identity (master principle 9). The manifest
records which files with which content hashes make up the candidate, the context it was built
against, its ancestry, and the model configuration and provenance that produced it (SIN-P1.1-004,
decisions F1–F8). It does not record lifecycle state: submission is a controller event (F2).
"""

from collections.abc import Iterable
from enum import StrEnum, unique
from typing import Annotated, Self

from pydantic import Field, StrictBool, StrictInt, model_validator

from sindri.core.ids import CandidateId, ContentId, EpisodeId, TaskId, canonical_json_id
from sindri.schemas._base import NonEmptyText, Record, StrictModel
from sindri.schemas.task import EditPath

SOURCE_HASH_KIND = "candidate_file_set_v1"


@unique
class ProducerRole(StrEnum):
    """Who produced the candidate (F6). Human-written goldens are not candidates."""

    SOLVER = "solver"
    RECONSTRUCTOR = "reconstructor"
    ARCHITECTURE_EXPLORER = "architecture_explorer"


class CandidateFile(StrictModel):
    path: EditPath
    hash: ContentId


class ModelAuthor(StrictModel):
    """Model configuration and provenance, recorded at the source (F7).

    `temperature_millis` is the sampling temperature scaled by 1000 (0.8 -> 800), an exact integer
    because records carry no binary floats (D5, F1). `provenance_ref` will resolve to the model
    gateway's call/provider/terms record; `training_allowed` is never defaulted.
    """

    model: NonEmptyText
    model_version: NonEmptyText
    temperature_millis: Annotated[StrictInt, Field(ge=0)]
    seed: StrictInt
    provenance_ref: NonEmptyText
    training_allowed: StrictBool


def candidate_source_hash(files: Iterable[CandidateFile]) -> ContentId:
    """The candidate's source identity (F3); the only implementation of the construction.

    canonical_json_id({"kind": "candidate_file_set_v1",
                       "files": [{"path": p, "hash": h}, ...]})  # sorted by path

    Paths sort by Unicode code point. The `kind` tag domain-separates this hash from every other
    canonical JSON ID; a different construction must use a new tag.
    """
    ordered = sorted(files, key=lambda f: str(f.path))
    return canonical_json_id(
        {
            "kind": SOURCE_HASH_KIND,
            "files": [{"path": str(f.path), "hash": str(f.hash)} for f in ordered],
        }
    )


class CandidateManifest(Record):
    candidate_id: CandidateId
    task_id: TaskId
    producer_role: ProducerRole
    episode_id: EpisodeId | None

    parent_candidate_id: CandidateId | None
    patch_hash: ContentId | None

    files: Annotated[tuple[CandidateFile, ...], Field(min_length=1)]
    source_hash: ContentId
    # None means this task explicitly has no external dependency bundle (F4). It never means
    # "unknown" or "not computed yet".
    dependency_hash: ContentId | None

    author: ModelAuthor

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        paths = [str(f.path) for f in self.files]
        if len(set(paths)) != len(paths):
            raise ValueError("files contains duplicate paths")
        if self.source_hash != candidate_source_hash(self.files):
            raise ValueError(f"source_hash does not match the {SOURCE_HASH_KIND} hash of files")
        if (self.parent_candidate_id is None) != (self.patch_hash is None):
            raise ValueError("parent_candidate_id and patch_hash must be both set or both null")
        if self.parent_candidate_id == self.candidate_id:
            raise ValueError("a candidate cannot be its own parent")
        is_solver = self.producer_role is ProducerRole.SOLVER
        if is_solver and self.episode_id is None:
            raise ValueError("solver candidates must name their episode_id")
        if not is_solver and self.episode_id is not None:
            raise ValueError(f"{self.producer_role} candidates are produced outside an episode")
        return self
