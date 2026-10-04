"""EvaluationPolicy: what must be checked for one task, and which checks cover which requirement.

Task-scoped (E1), versioned and immutable. The full record is judge-side protected (E2): a future
solver-safe projection may reveal development checks only, never hidden checks, hidden
configuration details, protected assumptions or tool profiles. It owns the requirement → obligation
mapping (ADR-0004). It holds per-candidate correctness checks only: evaluator qualification
(mutation, covers) and release behaviour (clean replay, waivers) live elsewhere (E3, E4, E7).
Decisions E1–E9: docs/tasks/SIN-P1.1-003.md.
"""

from enum import StrEnum, unique
from typing import Annotated, Self

from pydantic import Field, StrictBool, StrictInt, model_validator

from sindri.core.ids import (
    CheckId,
    ConfigurationId,
    ContentId,
    ExceptionId,
    ObligationId,
    PolicyId,
    RequirementId,
    TaskId,
    ToolProfileId,
)
from sindri.schemas._base import (
    ExactScalar,
    NonEmptyText,
    PositiveVersion,
    Record,
    StrictModel,
    check_version_chain,
)
from sindri.schemas.requirement import ParameterName


@unique
class CheckKind(StrEnum):
    """Per-candidate checks, in judge order (master §14 J1). `quality` is never correctness."""

    INTEGRITY_SCAN = "integrity_scan"
    PARSE_ELABORATE = "parse_elaborate"
    LINT = "lint"
    SYNTHESIS = "synthesis"
    DIRECTED_SIM = "directed_sim"
    RANDOM_SIM = "random_sim"
    FORMAL = "formal"
    EQUIVALENCE = "equivalence"
    QUALITY = "quality"


@unique
class Visibility(StrEnum):
    DEVELOPMENT = "development"
    HIDDEN = "hidden"


@unique
class FormalMode(StrEnum):
    """Correctness modes only (E4). Covers prove reachability, not behaviour, so they are absent."""

    BMC = "bmc"
    PROVE = "prove"


def _unique(values: tuple[object, ...], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} contains duplicates")


class ParameterAssignment(StrictModel):
    name: ParameterName
    value: ExactScalar


class Configuration(StrictModel):
    """One exact, finite parameter assignment (E5, master §11.14).

    `assignments` is empty for a design with no parameters: that design still has exactly one
    explicit configuration (e.g. `cfg_default`) so evidence stays configuration-scoped (E5a).
    """

    configuration_id: ConfigurationId
    assignments: tuple[ParameterAssignment, ...]

    @model_validator(mode="after")
    def _unique_names(self) -> Self:
        _unique(tuple(a.name for a in self.assignments), "configuration assignments")
        return self

    def assignment_key(self) -> frozenset[tuple[str, str, ExactScalar]]:
        """Order-independent identity of the assignment set. The type is part of the key, so
        `True` and `1` stay distinct."""
        return frozenset((a.name, type(a.value).__name__, a.value) for a in self.assignments)


DepthBound = Annotated[StrictInt, Field(ge=1)]


class Check(StrictModel):
    check_id: CheckId
    kind: CheckKind
    mandatory: StrictBool
    visibility: Visibility
    tool_profile_id: ToolProfileId
    configuration_ids: Annotated[tuple[ConfigurationId, ...], Field(min_length=1)]
    formal_mode: FormalMode | None
    depth: DepthBound | None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        _unique(self.configuration_ids, f"{self.check_id} configuration_ids")
        if self.kind is CheckKind.QUALITY and self.mandatory:
            raise ValueError(f"{self.check_id}: quality checks can never be mandatory")
        if self.kind is CheckKind.FORMAL:
            if self.formal_mode is None:
                raise ValueError(f"{self.check_id}: formal checks need formal_mode bmc or prove")
            if (self.formal_mode is FormalMode.BMC) != (self.depth is not None):
                raise ValueError(f"{self.check_id}: bmc needs a depth; prove takes none")
        elif self.formal_mode is not None or self.depth is not None:
            raise ValueError(f"{self.check_id}: only formal checks have formal_mode/depth")
        return self


class EnvironmentAssumption(StrictModel):
    text: NonEmptyText
    source_ref: NonEmptyText


class Obligation(StrictModel):
    """Covers exactly one requirement of this policy's task with one or more checks (E6)."""

    obligation_id: ObligationId
    requirement_id: RequirementId
    check_ids: Annotated[tuple[CheckId, ...], Field(min_length=1)]


class ExcludedPair(StrictModel):
    check_id: CheckId
    configuration_id: ConfigurationId


class PolicyException(StrictModel):
    """A not-applicable exclusion of exact (check, configuration) pairs (E7).

    It never turns an executed FAIL into PASS. An alternative checker, or dropping a mandatory
    check, requires a new policy version (E9). Release waivers belong to ReleaseManifest.
    """

    exception_id: ExceptionId
    excludes: Annotated[tuple[ExcludedPair, ...], Field(min_length=1)]
    justification: NonEmptyText
    approved_by: NonEmptyText


class EvaluationPolicy(Record):
    policy_id: PolicyId
    policy_version: PositiveVersion
    supersedes: ContentId | None
    task_id: TaskId
    contract_hash: ContentId

    configurations: Annotated[tuple[Configuration, ...], Field(min_length=1)]
    checks: Annotated[tuple[Check, ...], Field(min_length=1)]
    environment_assumptions: tuple[EnvironmentAssumption, ...]
    obligations: Annotated[tuple[Obligation, ...], Field(min_length=1)]
    exceptions: tuple[PolicyException, ...]

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        check_version_chain(self.policy_version, self.supersedes, "policy")

        config_ids = tuple(c.configuration_id for c in self.configurations)
        _unique(config_ids, "configuration_ids")
        _unique(tuple(c.assignment_key() for c in self.configurations), "configuration assignments")

        checks = {c.check_id: c for c in self.checks}
        _unique(tuple(c.check_id for c in self.checks), "check_ids")
        for check in self.checks:
            unknown_configs = set(check.configuration_ids) - set(config_ids)
            if unknown_configs:
                raise ValueError(
                    f"{check.check_id} references unknown configurations {unknown_configs}"
                )
        if not any(c.mandatory for c in self.checks):
            raise ValueError("a policy needs at least one mandatory correctness check")

        _unique(tuple(o.obligation_id for o in self.obligations), "obligation_ids")
        for ob in self.obligations:
            _unique(ob.check_ids, f"{ob.obligation_id} check_ids")
            unknown_checks = set(ob.check_ids) - set(checks)
            if unknown_checks:
                raise ValueError(f"{ob.obligation_id} references unknown checks {unknown_checks}")
            if all(checks[c].kind is CheckKind.QUALITY for c in ob.check_ids):
                raise ValueError(f"{ob.obligation_id} needs a non-quality check (E8)")

        _unique(tuple(e.exception_id for e in self.exceptions), "exception_ids")
        excluded = tuple(
            (p.check_id, p.configuration_id) for e in self.exceptions for p in e.excludes
        )
        _unique(excluded, "excluded (check, configuration) pairs")
        for check_id, config_id in excluded:
            if check_id not in checks:
                raise ValueError(f"exception excludes unknown check {check_id}")
            if config_id not in checks[check_id].configuration_ids:
                raise ValueError(f"exception excludes {config_id}, which {check_id} never targets")
        for check in self.checks:
            gone = {cfg for chk, cfg in excluded if chk == check.check_id}
            if check.mandatory and gone == set(check.configuration_ids):
                raise ValueError(
                    f"exceptions exclude every configuration of mandatory {check.check_id}; "
                    "use a new policy version (E9)"
                )
        return self
