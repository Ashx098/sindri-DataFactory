from sindri.core.status import CheckStatus, EvidenceLevel, ToolStatus


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
