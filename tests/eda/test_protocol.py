"""SIN-P1.6-001 F7: the seed result protocol fails closed (pure; needs no EDA tool)."""

import pytest

from tests.eda._protocol import verdict

EXPECTED = ["reset_state", "fill_to_full"]


def _t(*lines: str) -> str:
    return "\n".join(["noise before", *lines, "tb_fifo.v:99: $finish called at 1 (1ps)"])


def test_complete_passing_transcript_is_pass() -> None:
    v = verdict(_t("TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT PASS"), EXPECTED)
    assert v.status == "PASS" and v.reasons == ()


def test_consistent_failure_is_fail() -> None:
    v = verdict(_t("TEST reset_state PASS", "CHECK_FAIL ...", "TEST fill_to_full FAIL",
                   "RESULT FAIL", "FATAL: tb_fifo.v:1: boom"), EXPECTED)
    assert v.status == "FAIL"


@pytest.mark.parametrize(("name", "lines"), [
    ("missing test", ["TEST reset_state PASS", "RESULT PASS"]),
    ("unexpected test", ["TEST reset_state PASS", "TEST fill_to_full PASS", "TEST extra PASS",
                         "RESULT PASS"]),
    ("duplicate test", ["TEST reset_state PASS", "TEST reset_state PASS", "TEST fill_to_full PASS",
                        "RESULT PASS"]),
    ("no result (early $finish)", ["TEST reset_state PASS", "TEST fill_to_full PASS"]),
    ("two results", ["TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT PASS",
                     "RESULT PASS"]),
    ("result not terminal", ["TEST reset_state PASS", "RESULT PASS", "TEST fill_to_full PASS"]),
    ("RESULT PASS despite a failing test", ["TEST reset_state FAIL", "TEST fill_to_full PASS",
                                            "RESULT PASS"]),
    ("RESULT FAIL with all tests passing", ["TEST reset_state PASS", "TEST fill_to_full PASS",
                                            "RESULT FAIL"]),
    ("only a printed fake PASS", ["RESULT PASS"]),
    # malformed protocol-looking lines (PR #35 fix 3)
    ("malformed TEST status", ["TEST reset_state PASS", "TEST fill_to_full PASSED", "RESULT PASS"]),
    ("lower-case TEST status", ["TEST reset_state PASS", "TEST fill_to_full pass", "RESULT PASS"]),
    ("TEST with extra tokens", ["TEST reset_state PASS", "TEST fill_to_full PASS extra",
                                "RESULT PASS"]),
    ("TEST with empty id", ["TEST reset_state PASS", "TEST fill_to_full PASS", "TEST  PASS",
                            "RESULT PASS"]),
    ("TEST with invalid id", ["TEST reset_state PASS", "TEST fill_to_full PASS", "TEST 9bad PASS",
                              "RESULT PASS"]),
    ("bare TEST", ["TEST reset_state PASS", "TEST fill_to_full PASS", "TEST", "RESULT PASS"]),
    ("indented TEST", ["TEST reset_state PASS", "  TEST fill_to_full PASS", "RESULT PASS"]),
    ("malformed RESULT", ["TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT: PASS"]),
    ("RESULT with extra tokens", ["TEST reset_state PASS", "TEST fill_to_full PASS",
                                  "RESULT PASS now"]),
    ("malformed extra RESULT", ["TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT PASS",
                                "RESULT maybe"]),
])
def test_protocol_violations_fail_closed(name: str, lines: list[str]) -> None:
    v = verdict(_t(*lines), EXPECTED)
    assert v.status == "INVALID", (name, v)
    assert v.reasons


def test_an_inapplicable_test_is_not_expected_and_not_faked() -> None:
    """At DEPTH=1 R07's test is absent from the inventory: printing it would be unexpected."""
    v = verdict(_t("TEST reset_state PASS", "TEST simultaneous_push_pop PASS", "RESULT PASS"),
                ["reset_state"])
    assert v.status == "INVALID" and "unexpected" in v.reasons[0]


def test_non_protocol_lines_stay_noise() -> None:
    """Only lines whose first token is TEST or RESULT are protocol-looking."""
    v = verdict(_t("TESTING harness", "RESULTS follow", "SUMMARY failed_checks=0",
                   "TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT PASS"), EXPECTED)
    assert v.status == "PASS"


def test_a_spoofed_complete_transcript_is_indistinguishable() -> None:
    """Documented boundary: F7 checks completeness/consistency, not provenance (P1.4/P1.7)."""
    spoof = "\n".join(["TEST reset_state PASS", "TEST fill_to_full PASS", "RESULT PASS"])
    assert verdict(spoof, EXPECTED).status == "PASS"
