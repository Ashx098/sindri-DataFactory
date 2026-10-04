"""Versioned boundary records (master architecture ch. 20). Each record is closed, immutable,
float-free and coercion-free for identity-bearing scalars; see `_base.py`."""

from sindri.schemas.candidate import (
    CandidateFile,
    CandidateManifest,
    ModelAuthor,
    ProducerRole,
    candidate_source_hash,
)
from sindri.schemas.requirement import (
    AllSupportedConfigs,
    Assumption,
    EnvironmentRule,
    ParameterScope,
    ParameterValues,
    Requirement,
    RequirementDisposition,
)
from sindri.schemas.task import (
    READ_ONLY_TASK_TYPES,
    GeneratorSource,
    MutationSource,
    RepoSource,
    SourceRights,
    Split,
    TaskManifest,
    TaskType,
    UseCaseSource,
)

__all__ = [
    "CandidateFile",
    "CandidateManifest",
    "ModelAuthor",
    "ProducerRole",
    "candidate_source_hash",
    "READ_ONLY_TASK_TYPES",
    "AllSupportedConfigs",
    "Assumption",
    "EnvironmentRule",
    "GeneratorSource",
    "MutationSource",
    "ParameterScope",
    "ParameterValues",
    "RepoSource",
    "Requirement",
    "RequirementDisposition",
    "SourceRights",
    "Split",
    "TaskManifest",
    "TaskType",
    "UseCaseSource",
]
