"""Shared status taxonomy.

Every tool observation, judge check and dataset record uses these enums instead of ad-hoc
strings. Master architecture: F1 result normaliser, J2 status taxonomy, G2 tiers, G3 evidence
levels, 4 authority rule.
"""

from enum import IntEnum, StrEnum


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
        """True only when the result may become a training label.

        Infrastructure outcomes are never labels: a crash, expired license or unsupported
        construct says nothing about the candidate. TIMEOUT is a label only when the contract sets
        a performance bound; that decision belongs to the judge policy, not to this enum.
        """
        return self in (ToolStatus.PASS, ToolStatus.FAIL)


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


class Tier(StrEnum):
    """Where a task may be used (G2)."""

    GOLD = "gold"  # evaluation only; human-signed
    SILVER = "silver"  # training
    QUARANTINE = "quarantine"
    RETIRED = "retired"


class EvidenceLevel(IntEnum):
    """Strongest evidence attached to a record (G3). Ordered: compare with >=."""

    Q0_GENERATED = 0
    Q1_STRUCTURAL = 1
    Q2_BEHAVIOURAL = 2
    Q3_FORMAL_QUALIFIED = 3
    Q4_EQUIVALENCE_PROVED = 4
    Q5_ENGINEERING_ACCEPTED = 5


class AuthorityMode(StrEnum):
    """What counts as truth for a task (ADR-0002)."""

    REFERENCE_BEHAVIOR = "reference_behavior"
    ENGINEERING_INTENT = "engineering_intent"
    CORRECT_BY_CONSTRUCTION = "correct_by_construction"
