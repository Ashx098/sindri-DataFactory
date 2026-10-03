"""Shared status taxonomy.

Every tool observation, judge check and dataset record uses these enums instead of ad-hoc
strings. Master architecture: F1 result normaliser, J2 status taxonomy, G2 tiers, G3 evidence
levels, 4 authority rule; Appendix A outcomes. Semantics: ADR-0002.

Every enum is @unique: no member may alias another's value, so no status can be silently
coerced into a different one. Parsing an unknown string raises ValueError.
"""

from enum import IntEnum, StrEnum, unique


@unique
class ToolStatus(StrEnum):
    """Normalised outcome of one tool run (an Observation)."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    TIMEOUT = "TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    UNSUPPORTED = "UNSUPPORTED"

    @property
    def is_label(self) -> bool:
        """True only for statuses that carry a correctness label by default (ADR-0002).

        TOOL_ERROR, UNSUPPORTED and INCONCLUSIVE never carry a label: a crash, expired license or
        unsupported construct says nothing about the candidate. TIMEOUT carries no label here
        either. The raw status always stays TIMEOUT and is never rewritten to FAIL; only a
        downstream judge/training policy whose EvaluationPolicy declares the runtime limit as a
        task requirement may derive a negative outcome from it, referencing this Observation.
        """
        return self in (ToolStatus.PASS, ToolStatus.FAIL)


@unique
class CheckStatus(StrEnum):
    """Status of one judge check; extends ToolStatus with judge-only outcomes."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    TIMEOUT = "TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_SUBMISSION = "INVALID_SUBMISSION"
    INVALID_TASK = "INVALID_TASK"


@unique
class Verdict(StrEnum):
    """Final acceptance outcome (master architecture Appendix A)."""

    ACCEPTED = "ACCEPTED"
    FUNCTIONAL_FAIL = "FUNCTIONAL_FAIL"
    CORRECT_INFEASIBLE = "CORRECT_INFEASIBLE"
    INCONCLUSIVE = "INCONCLUSIVE"
    INVALID_TASK = "INVALID_TASK"
    TOOL_ERROR = "TOOL_ERROR"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@unique
class Tier(StrEnum):
    """Where a task may be used (G2)."""

    GOLD = "gold"  # evaluation only; human-signed
    SILVER = "silver"  # training
    QUARANTINE = "quarantine"
    RETIRED = "retired"


@unique
class EvidenceLevel(IntEnum):
    """Strongest evidence attached to a record (G3). Ordered: compare with >=."""

    Q0_GENERATED = 0
    Q1_STRUCTURAL = 1
    Q2_BEHAVIOURAL = 2
    Q3_FORMAL_QUALIFIED = 3
    Q4_EQUIVALENCE_PROVED = 4
    Q5_ENGINEERING_ACCEPTED = 5


@unique
class AuthorityMode(StrEnum):
    """What counts as truth for a task (ADR-0002)."""

    REFERENCE_BEHAVIOR = "reference_behavior"
    ENGINEERING_INTENT = "engineering_intent"
    CORRECT_BY_CONSTRUCTION = "correct_by_construction"
