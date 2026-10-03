"""Requirement: what must be true, in the source's words and in normalized form.

A requirement is identified by (task_id, requirement_id) (decision D3). It is immutable and
versioned (C1): any change to meaning or disposition is a new version that supersedes the previous
one by content ID, while the logical RequirementId stays stable. It does not own verification
obligations (ADR-0004); EvaluationPolicy / VerificationPlan map obligations to requirements.
"""

from enum import StrEnum, unique
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictBool, StrictStr, model_validator

from sindri.core.ids import ContentId, RequirementId, TaskId
from sindri.schemas._base import (
    ExactScalar,
    NonEmptyText,
    PositiveVersion,
    Record,
    StrictModel,
    check_version_chain,
)


@unique
class RequirementDisposition(StrEnum):
    """Decision D4. `ambiguous` blocks qualification; only `approved` may be verified against."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"
    REJECTED = "rejected"


class EnvironmentRule(StrictModel):
    """One rule of the legal input environment, with where it came from."""

    text: NonEmptyText
    source_ref: NonEmptyText


class Assumption(StrictModel):
    """An assumption is only admissible with a source (master §11.10: never source-less)."""

    text: NonEmptyText
    source_ref: NonEmptyText


class AllSupportedConfigs(StrictModel):
    kind: Literal["all_supported_configs"]


def _parameter_name(value: str) -> str:
    if not value or not (value[0].isascii() and value[0].isupper()):
        raise ValueError(f"parameter name must look like DEPTH or MAX_LEN: {value!r}")
    if any(not (c.isascii() and (c.isupper() or c.isdigit() or c == "_")) for c in value):
        raise ValueError(f"parameter name must look like DEPTH or MAX_LEN: {value!r}")
    return value


ParameterName = Annotated[StrictStr, AfterValidator(_parameter_name)]


def _distinct_exact_values(values: tuple[ExactScalar, ...]) -> tuple[ExactScalar, ...]:
    # Compare type and value together: True == 1 in Python, but they are different parameter values.
    keyed = [(type(v).__name__, v) for v in values]
    if len(set(keyed)) != len(keyed):
        raise ValueError("parameter values contain duplicates")
    return values


class ParameterValues(StrictModel):
    name: ParameterName
    values: Annotated[
        tuple[ExactScalar, ...], Field(min_length=1), AfterValidator(_distinct_exact_values)
    ]


class ParameterScope(StrictModel):
    """Explicit parameter configurations a requirement applies to (C4: typed, no Any, no floats).

    A tuple of named value lists rather than a dict, so the record stays fully immutable.
    """

    kind: Literal["parameter_scope"]
    parameters: Annotated[tuple[ParameterValues, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _unique_names(self) -> Self:
        names = [p.name for p in self.parameters]
        if len(set(names)) != len(names):
            raise ValueError("parameter_scope names a parameter twice")
        return self


Applicability = Annotated[AllSupportedConfigs | ParameterScope, Field(discriminator="kind")]


class Requirement(Record):
    task_id: TaskId
    requirement_id: RequirementId
    requirement_version: PositiveVersion
    supersedes: ContentId | None

    source_ref: NonEmptyText
    original_text: NonEmptyText
    normalized_semantics: NonEmptyText
    legal_environment: tuple[EnvironmentRule, ...]
    assumptions: tuple[Assumption, ...]
    applicability: Applicability
    mandatory: StrictBool
    disposition: RequirementDisposition

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        check_version_chain(self.requirement_version, self.supersedes, "requirement")
        return self
