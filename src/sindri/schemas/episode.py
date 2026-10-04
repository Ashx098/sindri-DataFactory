"""EpisodeState and EpisodeBudget: durable, immutable controller state for one solver episode.

`EpisodeState` is an immutable, hash-chained snapshot (ED3): every transition writes a new
snapshot; history is never overwritten. Together with the event log, CandidateManifests and pending
job IDs and request hashes it is sufficient to recover after a crash without asking a model to
reconstruct anything (master §8.8, ED13). The lifecycle and transition table follow ADR-0006.

`EpisodeBudget` is the immutable budget configuration (D6, ED6); its `content_id()` is its
identity. Additive resources (tokens, tool calls, candidate versions, sim jobs, formal ms, repair
attempts) are spent and reserved; wall-clock is tracked separately because concurrency makes it
non-additive (ED7). Remaining budget is derived, never stored (ED8).
Decisions: docs/tasks/SIN-P1.1-007.md.
"""

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import Annotated, Self

from pydantic import Field, StrictInt, model_validator

from sindri.core.ids import CandidateId, ContentId, EpisodeId, JobId, PolicyId, TaskId
from sindri.schemas._base import Record, StrictModel
from sindri.schemas.observation import ObservationAction

NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveInt = Annotated[StrictInt, Field(ge=1)]


@unique
class EpisodeStatus(StrEnum):
    """ADR-0006: master F3 lifecycle, the WAITING overlay of §8.8, and two terminal states."""

    PREPARE = "PREPARE"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    DEV_CHECK = "DEV_CHECK"
    TRIAGE = "TRIAGE"
    REPAIR = "REPAIR"
    SUBMIT = "SUBMIT"
    JUDGE = "JUDGE"
    RECORD = "RECORD"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


S = EpisodeStatus
TERMINAL_EPISODE_STATES = frozenset({S.COMPLETED, S.ABORTED})
# States that may enter WAITING and that WAITING may resume to.
ACTIVE_EPISODE_STATES = frozenset(set(S) - TERMINAL_EPISODE_STATES - {S.WAITING})
# ED4: from DEV_CHECK onwards the episode is working on a concrete candidate.
CANDIDATE_REQUIRED_STATES = frozenset(
    {S.DEV_CHECK, S.TRIAGE, S.REPAIR, S.SUBMIT, S.JUDGE, S.RECORD, S.COMPLETED}
)

_LIFECYCLE_EDGES = {
    (S.PREPARE, S.PLAN),
    (S.PLAN, S.IMPLEMENT),
    (S.IMPLEMENT, S.DEV_CHECK),
    (S.DEV_CHECK, S.TRIAGE),
    (S.DEV_CHECK, S.SUBMIT),
    (S.TRIAGE, S.REPAIR),
    (S.TRIAGE, S.ABORTED),
    (S.REPAIR, S.DEV_CHECK),
    (S.SUBMIT, S.JUDGE),
    (S.JUDGE, S.RECORD),
    (S.RECORD, S.COMPLETED),
}
# ADR-0006. WAITING may return only to its recorded resume_state; that per-snapshot rule is checked
# across snapshots (SIN-P1.1-009 / P1.5). Missing edges change only through controller/ADR review.
ALLOWED_EPISODE_TRANSITIONS: frozenset[tuple[EpisodeStatus, EpisodeStatus]] = frozenset(
    _LIFECYCLE_EDGES
    | {(state, S.WAITING) for state in ACTIVE_EPISODE_STATES}
    | {(S.WAITING, state) for state in ACTIVE_EPISODE_STATES}
    | {(state, S.ABORTED) for state in ACTIVE_EPISODE_STATES | {S.WAITING}}
)


@unique
class AbortReason(StrEnum):
    BUDGET_EXHAUSTED = "budget_exhausted"
    WALL_CLOCK_EXHAUSTED = "wall_clock_exhausted"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    STAGNATION = "stagnation"
    CANCELLED = "cancelled"


class BudgetVector(StrictModel):
    """Additive, reservable resources (ED7). Wall-clock is deliberately not here."""

    tokens: NonNegativeInt
    tool_calls: NonNegativeInt
    candidate_versions: NonNegativeInt
    sim_jobs: NonNegativeInt
    formal_ms: NonNegativeInt
    repair_attempts: NonNegativeInt

    def __add__(self, other: "BudgetVector") -> "BudgetVector":
        return BudgetVector(**{f: getattr(self, f) + getattr(other, f) for f in _DIMENSIONS})


_DIMENSIONS = tuple(BudgetVector.model_fields)
ZERO_BUDGET = BudgetVector(**dict.fromkeys(_DIMENSIONS, 0))


class CandidateBinding(StrictModel):
    """The exact candidate: handle plus CandidateManifest content identity (ED4)."""

    candidate_id: CandidateId
    candidate_manifest_hash: ContentId


class PendingJob(StrictModel):
    """An outstanding asynchronous job bound to the exact immutable request it represents (ED9)."""

    job_id: JobId
    request_hash: ContentId
    action: ObservationAction
    candidate: CandidateBinding
    reserved: BudgetVector


@dataclass(frozen=True)
class BudgetRemaining:
    """Derived remaining budget (ED8). Values may be negative when a budget has been overrun."""

    tokens: int
    tool_calls: int
    candidate_versions: int
    sim_jobs: int
    formal_ms: int
    repair_attempts: int
    wall_clock_ms: int


class EpisodeBudget(Record):
    """Immutable budget configuration; identified by its own `content_id()` (no budget_id, ED6).

    Additive limits may be zero (a disabled resource); the wall-clock limit must be positive (ED7).
    """

    limits: BudgetVector
    wall_clock_limit_ms: PositiveInt

    def remaining(self, state: "EpisodeState") -> BudgetRemaining:
        if state.budget_hash != self.content_id():
            raise ValueError("this snapshot is bound to a different EpisodeBudget")
        additive = {
            f: getattr(self.limits, f) - getattr(state.spent, f) - getattr(state.reserved, f)
            for f in _DIMENSIONS
        }
        return BudgetRemaining(
            **additive, wall_clock_ms=self.wall_clock_limit_ms - state.wall_clock_elapsed_ms
        )


class EpisodeState(Record):
    # identity and chain (ED3, ED15)
    episode_id: EpisodeId
    task_id: TaskId
    sequence: NonNegativeInt
    previous_state_hash: ContentId | None

    # evaluation context, budget and solver configuration (ED6, ED13, ED14)
    policy_id: PolicyId
    policy_hash: ContentId
    budget_hash: ContentId
    solver_config_hash: ContentId

    # lifecycle (ADR-0006, ED2)
    state: EpisodeStatus
    resume_state: EpisodeStatus | None
    abort_reason: AbortReason | None

    # candidates (ED4)
    active_candidate: CandidateBinding | None
    best_candidate: CandidateBinding | None

    # asynchronous work (ED9, ED10)
    pending_jobs: tuple[PendingJob, ...]

    # accounting (ED7, ED8)
    spent: BudgetVector
    reserved: BudgetVector
    wall_clock_elapsed_ms: NonNegativeInt

    # stagnation memory (ED11) and restart artefact (ED5)
    last_failure_signature: ContentId | None
    failure_repeat_count: NonNegativeInt
    checkpoint_ref: ContentId | None

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if (self.sequence == 0) != (self.previous_state_hash is None):
            raise ValueError("sequence 0 has no previous snapshot; later ones name it")

        waiting = self.state is S.WAITING
        if waiting:
            if self.resume_state not in ACTIVE_EPISODE_STATES:
                raise ValueError("WAITING resumes to an active state (never WAITING or terminal)")
            if not self.pending_jobs:
                raise ValueError("WAITING requires at least one pending job")
        elif self.resume_state is not None:
            raise ValueError("only WAITING carries a resume_state")

        if (self.state is S.ABORTED) != (self.abort_reason is not None):
            raise ValueError("abort_reason is set exactly when the episode is ABORTED")
        if self.state in TERMINAL_EPISODE_STATES and self.pending_jobs:
            raise ValueError("terminal states have no pending jobs")

        needs_candidate = self.state in CANDIDATE_REQUIRED_STATES or (
            waiting and self.resume_state in CANDIDATE_REQUIRED_STATES
        )
        if needs_candidate and self.active_candidate is None:
            raise ValueError(f"{self.state} requires an active_candidate")

        job_ids = [j.job_id for j in self.pending_jobs]
        if len(set(job_ids)) != len(job_ids):
            raise ValueError("pending job IDs must be unique")
        total = ZERO_BUDGET
        for job in self.pending_jobs:
            total = total + job.reserved
        if self.reserved != total:
            raise ValueError("reserved must equal the sum of pending-job reservations")

        if (self.last_failure_signature is None) != (self.failure_repeat_count == 0):
            raise ValueError("a failure signature has repeat count >= 1; no signature has count 0")
        return self
