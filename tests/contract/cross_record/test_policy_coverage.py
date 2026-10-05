"""SIN-P1.1-009 P: task <-> requirement <-> policy, incl. PR #9 mandatory coverage (X6/X11/X12)."""

from typing import Any

import pytest

from sindri.schemas import EvaluationPolicy, InvariantCode, Requirement, check_records
from tests.contract.cross_record._bundle import (
    H,
    Ref,
    Spec,
    add,
    check,
    data,
    policy,
    positive_spec,
    records,
    requirement,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids

C = InvariantCode


def _obligation(spec: Spec, ob_id: str) -> dict[str, Any]:
    return next(o for o in data(spec, "pol_v2")["obligations"] if o["obligation_id"] == ob_id)


def _p1_policy_for_absent_task(spec: Spec) -> None:
    add(spec, "pol_x", EvaluationPolicy, policy("ep_fifo_x", 1, "fifo_9999", H("a1")))


def _p2a_unknown_contract(spec: Spec) -> None:
    """Non-head revision with an unknown contract; its head revision is valid."""
    add(spec, "pol_x_v1", EvaluationPolicy, policy("ep_fifo_x", 1, "fifo_0001", H("a9")))
    add(spec, "pol_x_v2", EvaluationPolicy,
        policy("ep_fifo_x", 2, "fifo_0001", H("a2"), supersedes=Ref("pol_x_v1")))


def _p2b_stale_head(spec: Spec) -> None:
    data(spec, "pol_v2")["contract_hash"] = H("a1")


def _p3_head_unknown_requirement(spec: Spec) -> None:
    data(spec, "pol_v2")["obligations"].append(
        {"obligation_id": "ob_r99", "requirement_id": "R99", "check_ids": ["chk_sim"]})


def _p3_historical_unknown_requirement(spec: Spec) -> None:
    data(spec, "pol_v1")["obligations"].append(
        {"obligation_id": "ob_r44", "requirement_id": "R44", "check_ids": ["chk_sim"]})


def _p4_missing_requirement(spec: Spec) -> None:
    data(spec, "task_v2")["requirement_ids"].append("R18")


def _p4_orphan_requirement(spec: Spec) -> None:
    add(spec, "req_r42", Requirement, requirement("fifo_0001", "R42"))


def _p8_drop_depth(spec: Spec) -> None:
    cfg = data(spec, "pol_v2")["configurations"][2]
    cfg["assignments"] = [a for a in cfg["assignments"] if a["name"] != "DEPTH"]


def _p5_unknown_scope_name(spec: Spec) -> None:
    data(spec, "req_r17_v2")["applicability"]["parameters"][0]["name"] = "WIDTHX"


def _p6_excluded(spec: Spec) -> None:
    data(spec, "pol_v2")["exceptions"][0]["excludes"].append(
        {"check_id": "chk_sim", "configuration_id": "cfg_w1_d2"})


def _p6_optional_only(spec: Spec) -> None:
    body = data(spec, "pol_v2")
    body["checks"].append(check("chk_sim_opt", "directed_sim", ["cfg_w8_d4", "cfg_w32_d8",
                                                               "cfg_w1_d2"], mandatory=False))
    _obligation(spec, "ob_r03")["check_ids"] = ["chk_sim_opt"]


def _p6_quality_only(spec: Spec) -> None:
    body = data(spec, "pol_v2")
    area = next(c for c in body["checks"] if c["check_id"] == "chk_area")
    area["configuration_ids"] = ["cfg_w8_d4", "cfg_w32_d8"]
    _obligation(spec, "ob_r17")["check_ids"] = ["chk_area", "chk_formal"]


def _p6_untargeted(spec: Spec) -> None:
    data(spec, "pol_v2")["checks"].append(
        check("chk_sim_two", "directed_sim", ["cfg_w8_d4", "cfg_w32_d8"]))
    _obligation(spec, "ob_r03")["check_ids"] = ["chk_sim_two"]


def _exact_type_setup(spec: Spec, scope_values: list[Any]) -> None:
    """cfg_w1_d2 assigns WIDTH=true; R17 is enforced on w8_d4 and w32_d8 only."""
    body = data(spec, "pol_v2")
    body["configurations"][2]["assignments"][0]["value"] = True
    body["checks"].append(check("chk_sim_w32", "directed_sim", ["cfg_w32_d8"]))
    _obligation(spec, "ob_r17")["check_ids"] = ["chk_formal", "chk_sim_w32"]
    data(spec, "req_r17_v2")["applicability"]["parameters"][0]["values"] = scope_values


def _p6_true_is_not_one(spec: Spec) -> None:
    _exact_type_setup(spec, [8, 32, True])  # applies to WIDTH=true, which nothing enforces


def _p7_applies_nowhere(spec: Spec) -> None:
    data(spec, "req_r17_v2")["applicability"]["parameters"][0]["values"] = [64]


CASES = [
    Case("policy for an absent task", C.P1, 1, _p1_policy_for_absent_task),
    Case("contract hash on no task revision", C.P2A, 1, _p2a_unknown_contract),
    Case("head policy on revision 1's contract", C.P2B, 1, _p2b_stale_head),
    Case("head obligation for unlisted R99", C.P3, 1, _p3_head_unknown_requirement),
    Case("historical obligation for unlisted R44", C.P3, 1, _p3_historical_unknown_requirement),
    Case("task lists R18 with no Requirement", C.P4, 1, _p4_missing_requirement),
    Case("orphan Requirement R42", C.P4, 1, _p4_orphan_requirement),
    Case("one configuration omits DEPTH", C.P8, 1, _p8_drop_depth),
    Case("scope names WIDTHX", C.P5, 1, _p5_unknown_scope_name),
    Case("only covering check excluded on w1_d2", C.P6, 1, _p6_excluded),
    Case("R03 obligation uses an optional check only", C.P6, 3, _p6_optional_only),
    Case("only a quality check applies on w32_d8", C.P6, 1, _p6_quality_only),
    Case("covering check does not target w1_d2", C.P6, 1, _p6_untargeted),
    Case("scope true applies to WIDTH=true only", C.P6, 1, _p6_true_is_not_one),
    Case("R17 scope matches no configuration", C.P7, 1, _p7_applies_nowhere),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_scope_one_does_not_apply_to_true() -> None:
    """Exact-type applicability: scope value 1 does not select WIDTH=true, so no gap there."""
    spec = positive_spec()
    _exact_type_setup(spec, [8, 32, 1])
    assert check_records(records(spec)) == ()


def test_zero_parameter_policy_with_all_supported_requirements_is_clean() -> None:
    spec = positive_spec()
    for name in ("pol_v1", "pol_v2"):
        body = data(spec, name)
        body["configurations"] = [{"configuration_id": "cfg_default", "assignments": []}]
        for c in body["checks"]:
            c["configuration_ids"] = ["cfg_default"]
        body["exceptions"] = []
    for name in ("req_r17_v1", "req_r17_v2"):
        data(spec, name)["applicability"] = {"kind": "all_supported_configs"}
    for name in ("ob_simv2", "ob_simtimeout", "ob_formalv2", "ob_formalv1fail"):
        data(spec, name)["configuration_id"] = "cfg_default"
    data(spec, "tr_F1_1")["proposed_check"]["configuration_id"] = "cfg_default"
    data(spec, "tr_F2_1")["proposed_check"]["configuration_id"] = "cfg_default"
    assert check_records(records(spec)) == ()


def test_gap_detail_names_policy_requirement_and_configuration() -> None:
    spec = positive_spec()
    _p6_excluded(spec)
    (v,) = check_records(records(spec))
    assert v.subject == "EvaluationPolicy:ep_fifo_main@v2"
    assert "R03" in v.detail and "cfg_w1_d2" in v.detail
