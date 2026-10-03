"""TaskManifest: what a task is, where it came from, and where it may be used.

Immutable and versioned (decision D1): identity, authority, provenance, rights, split, contract
and edit scope only. Lifecycle state (tier, evidence level, difficulty, status history) lives in the
task registry/event log, not here. Budgets are episode-scoped (D6). A change is a new manifest
version that supersedes the previous one by content ID; cross-version identity rules are checked in
SIN-P1.1-009.
"""

from enum import StrEnum, unique
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictBool, StrictStr, model_validator

from sindri.core.ids import (
    ContentId,
    ContractId,
    FamilyId,
    LineageId,
    RequirementId,
    TaskId,
    VariantId,
)
from sindri.core.status import AuthorityMode
from sindri.schemas._base import (
    NonEmptyText,
    PositiveVersion,
    Record,
    StrictModel,
    check_version_chain,
)


@unique
class Split(StrEnum):
    """Assigned at family level before any variant exists (master §4 principle 8, §9 T5)."""

    TRAIN = "train"
    DEV = "dev"
    FINAL = "final"


@unique
class TaskType(StrEnum):
    """Master §20.1 task types plus `comprehension` (§9 T1; decision D7)."""

    SPEC_TO_RTL = "spec_to_rtl"
    COMPLETION = "completion"
    MODIFICATION = "modification"
    DEBUG = "debug"
    TESTBENCH = "testbench"
    ASSERTION = "assertion"
    SPEC_TASK = "spec_task"
    COMPREHENSION = "comprehension"


# Read-only task types must have an empty edit scope; every other type needs one (C3, D7).
READ_ONLY_TASK_TYPES = frozenset({TaskType.COMPREHENSION, TaskType.SPEC_TASK})


def _commit_sha(value: str) -> str:
    """Full commit hash only (SHA-1 or SHA-256 object format); abbreviations are ambiguous."""
    if len(value) not in (40, 64) or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("commit must be a full lowercase 40- or 64-hex git object id")
    return value


CommitSha = Annotated[StrictStr, AfterValidator(_commit_sha)]


class RepoSource(StrictModel):
    """Cut from real RTL or derived from a real commit (master §9 T1)."""

    kind: Literal["repo_cut", "commit_feature", "commit_fix"]
    repo: NonEmptyText
    commit: CommitSha


class MutationSource(StrictModel):
    """Derived by mutating another task's golden design (§9 T2)."""

    kind: Literal["mutation"]
    parent_task_id: TaskId
    operator: NonEmptyText


class GeneratorSource(StrictModel):
    """Produced by a human-reviewed generator family (§9 T3)."""

    kind: Literal["generator"]
    generator_id: NonEmptyText
    generator_version: NonEmptyText


class UseCaseSource(StrictModel):
    """From an approved use case (§9 T4)."""

    kind: Literal["use_case"]
    intake_ref: NonEmptyText


TaskSource = Annotated[
    RepoSource | MutationSource | GeneratorSource | UseCaseSource,
    Field(discriminator="kind"),
]


class SourceRights(StrictModel):
    """Explicit usage rights (C2). Every field is required; nothing defaults to allowed.

    `licence` is an SPDX expression; it may be null only when a written agreement covers the use.
    """

    licence: NonEmptyText | None
    written_agreement_ref: NonEmptyText | None
    training_allowed: StrictBool
    evaluation_allowed: StrictBool
    redistribution_allowed: StrictBool
    customer_restricted: StrictBool

    @model_validator(mode="after")
    def _has_a_basis(self) -> Self:
        if self.licence is None and self.written_agreement_ref is None:
            raise ValueError("rights need a licence or a written agreement reference")
        return self


def _safe_relative_path(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError(f"edit path must be a relative POSIX path: {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"edit path has an empty, '.' or '..' segment: {value!r}")
    return value


EditPath = Annotated[StrictStr, AfterValidator(_safe_relative_path)]


class TaskManifest(Record):
    task_id: TaskId
    family_id: FamilyId
    lineage_id: LineageId
    variant_id: VariantId
    manifest_version: PositiveVersion
    supersedes: ContentId | None

    authority_mode: AuthorityMode
    split: Split
    task_type: TaskType
    source: TaskSource
    rights: SourceRights

    golden_hash: ContentId | None
    contract_id: ContractId
    approved_contract_hash: ContentId

    allowed_edit_paths: tuple[EditPath, ...]
    requirement_ids: Annotated[tuple[RequirementId, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        check_version_chain(self.manifest_version, self.supersedes, "manifest")
        if self.authority_mode is AuthorityMode.REFERENCE_BEHAVIOR and self.golden_hash is None:
            raise ValueError("reference_behavior tasks must name their golden_hash")
        if len(set(self.allowed_edit_paths)) != len(self.allowed_edit_paths):
            raise ValueError("allowed_edit_paths contains duplicates")
        read_only = self.task_type in READ_ONLY_TASK_TYPES
        if read_only and self.allowed_edit_paths:
            raise ValueError(f"{self.task_type} is read-only and must have an empty edit scope")
        if not read_only and not self.allowed_edit_paths:
            raise ValueError(f"{self.task_type} edits files and needs a non-empty edit scope")
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("requirement_ids contains duplicates")
        return self
