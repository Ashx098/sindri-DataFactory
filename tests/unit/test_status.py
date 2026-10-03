import enum

import pytest

from sindri.core.status import (
    AuthorityMode,
    CheckStatus,
    EvidenceLevel,
    Tier,
    ToolStatus,
    Verdict,
)


def test_only_pass_and_fail_are_labels() -> None:
    labels = {s for s in ToolStatus if s.is_label}
    assert labels == {ToolStatus.PASS, ToolStatus.FAIL}


def test_infrastructure_outcomes_are_never_pass() -> None:
    for status in (ToolStatus.TIMEOUT, ToolStatus.TOOL_ERROR, ToolStatus.UNSUPPORTED):
        assert status != ToolStatus.PASS
        assert not status.is_label


def test_check_status_covers_every_tool_status() -> None:
    assert {s.value for s in ToolStatus} <= {s.value for s in CheckStatus}


def test_evidence_levels_are_ordered() -> None:
    assert EvidenceLevel.Q3_FORMAL_QUALIFIED >= EvidenceLevel.Q2_BEHAVIOURAL
    assert max(EvidenceLevel) is EvidenceLevel.Q5_ENGINEERING_ACCEPTED


# ---- SIN-P1.1-001: no coercion between statuses (ADR-0002) ------------------------------------

ALL_ENUMS = [ToolStatus, CheckStatus, Verdict, Tier, EvidenceLevel, AuthorityMode]
NON_LABELS = [
    ToolStatus.TIMEOUT, ToolStatus.TOOL_ERROR, ToolStatus.INCONCLUSIVE, ToolStatus.UNSUPPORTED,
]


@pytest.mark.parametrize("status", NON_LABELS)
def test_non_label_statuses_never_equal_pass_or_fail(status: ToolStatus) -> None:
    assert status not in (ToolStatus.PASS, ToolStatus.FAIL)
    assert status not in ("PASS", "FAIL")
    assert ToolStatus(status.value) is status  # a round trip keeps the raw status


@pytest.mark.parametrize("cls", ALL_ENUMS)
def test_enums_have_no_aliases(cls: type[enum.Enum]) -> None:
    assert len(cls.__members__) == len(list(cls)), f"{cls.__name__} has an alias"


@pytest.mark.parametrize("raw", ["BOGUS", "pass", "Fail", "", "TIMEOUT_AS_FAIL"])
def test_unknown_or_miscased_status_strings_are_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        ToolStatus(raw)
    with pytest.raises(ValueError):
        CheckStatus(raw)


def test_unknown_values_rejected_for_every_enum() -> None:
    for cls in (Verdict, Tier, AuthorityMode):
        with pytest.raises(ValueError):
            cls("not-a-member")
    with pytest.raises(ValueError):
        EvidenceLevel(6)


def test_taxonomy_matches_master_architecture() -> None:
    """J2 statuses, Appendix A outcomes, G2 tiers, G3 levels, section 4 authority modes."""
    assert {s.value for s in CheckStatus} == {
        "PASS", "FAIL", "INCONCLUSIVE", "TIMEOUT", "TOOL_ERROR", "UNSUPPORTED",
        "INVALID_SUBMISSION", "INVALID_TASK",
    }
    assert {v.value for v in Verdict} == {
        "ACCEPTED", "FUNCTIONAL_FAIL", "CORRECT_INFEASIBLE", "INCONCLUSIVE", "INVALID_TASK",
        "TOOL_ERROR", "BUDGET_EXHAUSTED", "REVIEW_REQUIRED",
    }
    assert {t.value for t in Tier} == {"gold", "silver", "quarantine", "retired"}
    assert [int(e) for e in EvidenceLevel] == [0, 1, 2, 3, 4, 5]
    assert {a.value for a in AuthorityMode} == {
        "reference_behavior", "engineering_intent", "correct_by_construction",
    }
