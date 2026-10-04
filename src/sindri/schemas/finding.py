"""Finding: one structured claim about one exact candidate, and its controller-recorded lifecycle.

`Finding` is immutable: claim, requirement, exact candidate binding, initial uncertainty, producer
provenance and initial evidence (FD1, FD3, FD6, FD7, FD10, FD11). It carries no status. Its
lifecycle lives in immutable `FindingTransition` records: the initial status is implicitly
`hypothesis`, and the current status is derived from the transition chain (FD1, FD2).

The `hypothesis -> check_proposed` transition carries exactly one `ProposedCheck` (an existing
policy check, or a development probe request that is never correctness evidence, FD8). Confirm and
refute transitions cite deciding Observations (FD4, FD9). Supporting artifacts may support a
hypothesis but never decide one (FD5, ADR-0005). Controller-only transition authority is the
store/controller permission boundary (P1.2/P1.5), not a field (FD2).
Decisions: docs/tasks/SIN-P1.1-006.md.
"""

from enum import StrEnum, unique
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictBool, StrictInt, model_validator

from sindri.core.ids import (
    CandidateId,
    CheckId,
    ConfigurationId,
    ContentId,
    FindingId,
    ObservationId,
    PropertyId,
    RequirementId,
    TaskId,
    TestId,
)
from sindri.core.status import ToolStatus
from sindri.schemas._base import NonEmptyText, Record, StrictModel
from sindri.schemas.observation import ObservationAction

MAX_CLAIM_CHARS = 500


@unique
class FindingStatus(StrEnum):
    HYPOTHESIS = "hypothesis"
    CHECK_PROPOSED = "check_proposed"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    DROPPED = "dropped"


TERMINAL_FINDING_STATUSES = frozenset(
    {FindingStatus.CONFIRMED, FindingStatus.REFUTED, FindingStatus.DROPPED}
)
DECIDED_FINDING_STATUSES = frozenset({FindingStatus.CONFIRMED, FindingStatus.REFUTED})

# FD2: no hypothesis -> confirmed shortcut; terminal statuses have no outgoing edges.
ALLOWED_FINDING_TRANSITIONS: frozenset[tuple[FindingStatus, FindingStatus]] = frozenset(
    {
        (FindingStatus.HYPOTHESIS, FindingStatus.CHECK_PROPOSED),
        (FindingStatus.CHECK_PROPOSED, FindingStatus.CONFIRMED),
        (FindingStatus.CHECK_PROPOSED, FindingStatus.REFUTED),
        (FindingStatus.HYPOTHESIS, FindingStatus.DROPPED),
        (FindingStatus.CHECK_PROPOSED, FindingStatus.DROPPED),
    }
)


@unique
class Uncertainty(StrEnum):
    """The author's initial uncertainty (FD7). No probabilities: model confidence is uncalibrated.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@unique
class ProducerRole(StrEnum):
    SOLVER = "solver"
    CRITIC = "critic"
    TRIAGE = "triage"
    REVIEWER = "reviewer"


@unique
class DropReason(StrEnum):
    NO_EXECUTABLE_CHECK = "no_executable_check"  # F4: prose-only after one triage pass
    SUPERSEDED = "superseded"
    DUPLICATE = "duplicate"
    CANDIDATE_INVALIDATED = "candidate_invalidated"
    BUDGET_EXHAUSTED = "budget_exhausted"


# ---- evidence -----------------------------------------------------------------------------------


class ObservationCitation(StrictModel):
    """Correctness evidence: the Observation's handle and its exact content identity (FD4)."""

    observation_id: ObservationId
    observation_hash: ContentId


@unique
class SupportingArtifactKind(StrEnum):
    TRACE = "trace"
    WAVEFORM_WINDOW = "waveform_window"
    LOG_EXCERPT = "log_excerpt"
    REPRODUCER = "reproducer"


class CycleWindow(StrictModel):
    start: Annotated[StrictInt, Field(ge=0)]
    end: Annotated[StrictInt, Field(ge=0)]

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("cycle window start must not exceed end")
        return self


class SupportingArtifact(StrictModel):
    """Supporting evidence only: never decides a Finding (FD5, ADR-0005)."""

    kind: SupportingArtifactKind
    hash: ContentId
    cycle_window: CycleWindow | None


# ---- producer provenance (FD11) -----------------------------------------------------------------


class ModelProducer(StrictModel):
    kind: Literal["model"]
    role: ProducerRole
    model: NonEmptyText
    model_version: NonEmptyText
    provenance_ref: NonEmptyText
    training_allowed: StrictBool


class ComponentProducer(StrictModel):
    kind: Literal["component"]
    role: ProducerRole
    component: NonEmptyText
    component_version: NonEmptyText
    component_hash: ContentId
    provenance_ref: NonEmptyText
    training_allowed: StrictBool


class HumanProducer(StrictModel):
    kind: Literal["human"]
    role: ProducerRole
    reviewer_ref: NonEmptyText
    provenance_ref: NonEmptyText
    training_allowed: StrictBool


Producer = Annotated[
    ModelProducer | ComponentProducer | HumanProducer, Field(discriminator="kind")
]


# ---- proposed checks (FD8) ----------------------------------------------------------------------


def _verdict_status(value: ToolStatus) -> ToolStatus:
    if value not in (ToolStatus.PASS, ToolStatus.FAIL):
        raise ValueError("confirming_status must be PASS or FAIL")
    return value


class ExistingPolicyCheck(StrictModel):
    """A declared policy check; once executed, its Observation can decide the Finding.

    `confirming_status` makes the verdict mapping deterministic: claim prose cannot tell a
    controller whether PASS confirms or refutes. The opposite verdict-bearing status refutes.
    In SIN-P1.1-009, confirmed citations must all carry `confirming_status`, refuted citations
    all carry `refuting_status`, and mixed PASS/FAIL deciding citations are invalid.
    """

    proposal_kind: Literal["existing_policy_check"]
    policy_hash: ContentId
    check_id: CheckId
    configuration_id: ConfigurationId
    confirming_status: Annotated[ToolStatus, AfterValidator(_verdict_status)]

    @property
    def refuting_status(self) -> ToolStatus:
        return ToolStatus.FAIL if self.confirming_status is ToolStatus.PASS else ToolStatus.PASS


class DevelopmentProbeRequest(StrictModel):
    """A triage probe. Never executable correctness evidence: its result only supports (FD8).

    Pinned to an exact policy namespace by `policy_hash`. v1 payloads are strict: `run_sim` names
    tests only, `run_formal` names properties only; every other action is rejected.

    A Finding proposed with a probe can never be confirmed or refuted (a cross-transition rule
    enforced in SIN-P1.1-009 / P1.5): it is dropped or superseded. If the probe is promoted into a
    declared policy check, a new `derived_from` Finding proposes an `ExistingPolicyCheck`, and only
    that Finding may be decided. 006 defines no promotion relation.
    """

    proposal_kind: Literal["development_probe"]
    policy_hash: ContentId
    action: ObservationAction
    configuration_id: ConfigurationId
    test_ids: tuple[TestId, ...]
    property_ids: tuple[PropertyId, ...]
    rationale: NonEmptyText

    @model_validator(mode="after")
    def _payload(self) -> Self:
        if self.action is ObservationAction.RUN_SIM:
            if not self.test_ids or self.property_ids:
                raise ValueError("a run_sim probe names tests only (non-empty test_ids)")
        elif self.action is ObservationAction.RUN_FORMAL:
            if not self.property_ids or self.test_ids:
                raise ValueError("a run_formal probe names properties only (non-empty)")
        else:
            raise ValueError("development probes support only run_sim and run_formal in v1")
        _unique(self.test_ids, "test_ids")
        _unique(self.property_ids, "property_ids")
        return self


ProposedCheck = Annotated[
    ExistingPolicyCheck | DevelopmentProbeRequest, Field(discriminator="proposal_kind")
]


def _unique(values: tuple[object, ...], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} contains duplicates")


def _claim(value: str) -> str:
    if len(value) > MAX_CLAIM_CHARS:
        raise ValueError(f"claim exceeds {MAX_CLAIM_CHARS} characters")
    return value


# ---- records ------------------------------------------------------------------------------------


class Finding(Record):
    finding_id: FindingId
    task_id: TaskId
    candidate_id: CandidateId
    candidate_manifest_hash: ContentId
    requirement_id: RequirementId
    claim: Annotated[NonEmptyText, AfterValidator(_claim)]
    uncertainty: Uncertainty
    producer: Producer
    correctness_citations: tuple[ObservationCitation, ...]
    supporting_evidence: tuple[SupportingArtifact, ...]
    derived_from: FindingId | None

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if not self.correctness_citations and not self.supporting_evidence:
            raise ValueError("a finding names the evidence it concerns (F4)")
        cited = tuple(c.observation_id for c in self.correctness_citations)
        _unique(cited, "correctness_citations")
        if self.derived_from == self.finding_id:
            raise ValueError("a finding cannot be derived from itself")
        return self


class FindingTransition(Record):
    finding_id: FindingId
    finding_hash: ContentId
    sequence: Annotated[StrictInt, Field(ge=1)]
    previous_transition_hash: ContentId | None
    from_status: FindingStatus
    to_status: FindingStatus
    proposed_check: ProposedCheck | None
    deciding_citations: tuple[ObservationCitation, ...]
    drop_reason: DropReason | None
    superseded_by: FindingId | None

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        edge = (self.from_status, self.to_status)
        if edge not in ALLOWED_FINDING_TRANSITIONS:
            raise ValueError(f"transition {self.from_status} -> {self.to_status} is not allowed")
        if (self.sequence == 1) != (self.previous_transition_hash is None):
            raise ValueError("sequence 1 has no previous transition; later ones name it")
        if self.sequence == 1 and self.from_status is not FindingStatus.HYPOTHESIS:
            raise ValueError("a finding's first transition starts from hypothesis")

        proposing = self.to_status is FindingStatus.CHECK_PROPOSED
        if proposing != (self.proposed_check is not None):
            raise ValueError("exactly the transition into check_proposed carries a proposed check")

        deciding = self.to_status in DECIDED_FINDING_STATUSES
        if deciding != bool(self.deciding_citations):
            raise ValueError("confirm/refute need deciding Observation citations; others have none")
        _unique(tuple(c.observation_id for c in self.deciding_citations), "deciding_citations")

        dropping = self.to_status is FindingStatus.DROPPED
        if dropping != (self.drop_reason is not None):
            raise ValueError("exactly the transition into dropped carries a drop_reason")
        superseded = self.drop_reason is DropReason.SUPERSEDED
        if superseded != (self.superseded_by is not None):
            raise ValueError("superseded_by is set exactly when the drop reason is superseded")
        if self.superseded_by == self.finding_id:
            raise ValueError("a finding cannot be superseded by itself")
        return self
