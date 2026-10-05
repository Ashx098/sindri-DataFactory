"""SIN-P1.1-009 O: Observation <-> exact candidate, policy, check, configuration and settings."""

import pytest

from sindri.schemas import InvariantCode as C
from tests.contract.cross_record._bundle import H, Ref, Spec, add_m1_policy, data
from tests.contract.cross_record._case import Case, assert_isolated, ids


def _o1_dependency_differs(spec: Spec) -> None:
    data(spec, "ob_simtimeout")["dependency_hash"] = H("d9")  # seal() re-keys execution_key


def _o2_policy_of_other_task(spec: Spec) -> None:
    add_m1_policy(spec)
    body = data(spec, "ob_simtimeout")
    body["policy_id"] = "ep_fifo_m1"
    body["policy_hash"] = Ref("pol_m1")


def _o3_unknown_check(spec: Spec) -> None:
    data(spec, "ob_simtimeout")["check_id"] = "chk_nope"


def _o3_untargeted(spec: Spec) -> None:
    body = data(spec, "ob_simtimeout")
    body["check_id"], body["configuration_id"] = "chk_formal", "cfg_w1_d2"


def _o3_excluded(spec: Spec) -> None:
    data(spec, "ob_simtimeout")["check_id"] = "chk_formal"  # (chk_formal, cfg_w32_d8) excluded


def _o4_visibility(spec: Spec) -> None:
    data(spec, "ob_simtimeout")["visibility"] = "hidden"


def _o4_depth(spec: Spec) -> None:
    body = data(spec, "ob_formalv1fail")
    body["formal_depth"] = 20
    body["execution_report"]["requested_depth"] = 20


def _o4_profile_and_kind(spec: Spec) -> None:
    body = data(spec, "ob_simtimeout")
    body["tool_profile_id"] = "tp_icarus_v0"
    body["check_kind"] = "random_sim"


CASES = [
    Case("dependency_hash differs from the manifest", C.O1, 1, _o1_dependency_differs),
    Case("policy of another task", C.O2, 1, _o2_policy_of_other_task),
    Case("unknown check", C.O3, 1, _o3_unknown_check),
    Case("check does not target the configuration", C.O3, 1, _o3_untargeted),
    Case("excluded (check, configuration) pair", C.O3, 1, _o3_excluded),
    Case("visibility differs from the policy check", C.O4, 1, _o4_visibility),
    Case("formal depth 20 vs policy 24", C.O4, 1, _o4_depth),
    Case("tool profile and kind differ (two fields)", C.O4, 2, _o4_profile_and_kind),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)
