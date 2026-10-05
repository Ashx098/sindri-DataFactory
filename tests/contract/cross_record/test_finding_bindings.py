"""SIN-P1.1-009 F (Finding bindings, verdict mapping, probe prohibition, lineage, hidden evidence)
and T (FindingTransition chains)."""

import pytest

from sindri.schemas import Finding, FindingTransition, Observation, check_records
from sindri.schemas import InvariantCode as C
from tests.contract.cross_record._bundle import (
    Ref,
    Spec,
    add,
    add_after,
    add_m1_candidate,
    citation,
    data,
    existing_check,
    finding,
    formal_obs,
    model_producer,
    positive_spec,
    records,
    transition,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids


def _deciding(spec: Spec, *obs: str) -> None:
    data(spec, "tr_F1_2")["deciding_citations"] = [citation(o, o) for o in obs]


def _add_obs(spec: Spec, name: str, cand: str, status: str) -> None:
    add_after(spec, "ob_simtimeout", name, Observation, formal_obs(name, cand, status))


def _f1_task_differs(spec: Spec) -> None:
    add(spec, "F5", Finding, finding("F5", "cand_v2", "R03", model_producer("triage"), [],
                                     task_id="fifo_0001_m1"))


def _f2_unlisted_requirement(spec: Spec) -> None:
    data(spec, "F4")["requirement_id"] = "R99"


def _f3_parent_candidate(spec: Spec) -> None:
    _add_obs(spec, "ob_formalv1pass", "cand_v1", "PASS")
    _deciding(spec, "ob_formalv1pass")


def _decide_with_timeout(spec: Spec) -> None:
    _deciding(spec, "ob_simtimeout")


def _f5_other_check(spec: Spec) -> None:
    _deciding(spec, "ob_simv2")


def _f5_wrong_verdict(spec: Spec) -> None:
    _add_obs(spec, "ob_formalv2fail", "cand_v2", "FAIL")
    _deciding(spec, "ob_formalv2fail")


def _f5_mixed(spec: Spec) -> None:
    _add_obs(spec, "ob_formalv2fail", "cand_v2", "FAIL")
    _deciding(spec, "ob_formalv2", "ob_formalv2fail")


def _f6_excluded_proposal(spec: Spec) -> None:
    data(spec, "tr_F1_1")["proposed_check"]["configuration_id"] = "cfg_w32_d8"


def _f6_probe_configuration_absent(spec: Spec) -> None:
    data(spec, "tr_F2_1")["proposed_check"]["configuration_id"] = "cfg_w64_d8"


def _f10_unrelated_requirement(spec: Spec) -> None:
    data(spec, "F1")["requirement_id"] = "R03"  # chk_formal is obligated for R17 only


def _f7_probe_decided(spec: Spec) -> None:
    body = data(spec, "tr_F2_2")
    body["to_status"], body["drop_reason"] = "confirmed", None
    body["deciding_citations"] = [citation("ob_simv2", "ob_simv2")]


def _f8_superseded_by_absent(spec: Spec) -> None:
    data(spec, "tr_F3_1")["superseded_by"] = "F77"


def _f8_derived_from_other_task(spec: Spec) -> None:
    add_m1_candidate(spec)
    add_after(spec, "F3", "F6", Finding, finding(
        "F6", "cand_m1", "R03", model_producer("triage"), [], task_id="fifo_0001_m1"))
    data(spec, "F4")["derived_from"] = "F6"


def _f11_derived_cycle(spec: Spec) -> None:
    data(spec, "F3")["derived_from"] = "F4"


def _f11_superseded_cycle(spec: Spec) -> None:
    add(spec, "tr_F4_1", FindingTransition, transition(
        "F4", "F4", 1, None, "hypothesis", "dropped", drop_reason="superseded",
        superseded_by="F3"))


def _f9_solver_cites_hidden(spec: Spec) -> None:
    data(spec, "F2")["correctness_citations"].append(citation("ob_formalv2", "ob_formalv2"))


def _t2_gap(spec: Spec) -> None:
    data(spec, "tr_F1_2")["sequence"] = 3


def _t3_wrong_predecessor(spec: Spec) -> None:
    data(spec, "tr_F2_2")["previous_transition_hash"] = Ref("tr_F1_1")


def _t4_from_status(spec: Spec) -> None:
    data(spec, "tr_F2_2")["from_status"] = "hypothesis"


def _after_terminal(spec: Spec) -> None:
    add(spec, "tr_F3_2", FindingTransition, transition(
        "F3", "F3", 2, "tr_F3_1", "hypothesis", "check_proposed",
        proposed_check=existing_check()))


CASES = [
    Case("finding task differs from its candidate's", C.F1, 1, _f1_task_differs),
    Case("finding requirement R99 not listed", C.F2, 1, _f2_unlisted_requirement),
    Case("deciding PASS on the parent candidate", C.F3, 1, _f3_parent_candidate),
    Case("confirm citing a TIMEOUT", C.F4, 1, _decide_with_timeout),
    Case("deciding observation of another check", C.F5, 1, _f5_other_check),
    Case("confirmed with FAIL where confirming is PASS", C.F5, 1, _f5_wrong_verdict),
    Case("mixed PASS + FAIL deciding citations", C.F5, 1, _f5_mixed),
    Case("proposal of an excluded pair", C.F6, 1, _f6_excluded_proposal),
    Case("probe configuration absent from its policy", C.F6, 1, _f6_probe_configuration_absent),
    Case("proposed check obligated for another requirement", C.F10, 1,
         _f10_unrelated_requirement),
    Case("probe-proposed finding confirmed", C.F7, 1, _f7_probe_decided),
    Case("superseded_by an absent finding", C.F8, 1, _f8_superseded_by_absent),
    Case("derived_from a finding of another task", C.F8, 1, _f8_derived_from_other_task),
    Case("derived_from cycle F3 <-> F4", C.F11, 1, _f11_derived_cycle),
    Case("superseded_by cycle F3 <-> F4", C.F11, 1, _f11_superseded_cycle),
    Case("solver finding cites a hidden observation", C.F9, 1, _f9_solver_cites_hidden),
    Case("transition sequences 1, 3", C.T2, 1, _t2_gap),
    Case("predecessor is another finding's transition", C.T3, 1, _t3_wrong_predecessor),
    Case("from_status differs from previous to_status", C.T4, 1, _t4_from_status),
    Case("transition after dropped", C.T5, 1, _after_terminal),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_refuted_with_the_refuting_status_is_clean() -> None:
    spec = positive_spec()
    _add_obs(spec, "ob_formalv2fail", "cand_v2", "FAIL")
    body = data(spec, "tr_F1_2")
    body["to_status"] = "refuted"
    body["deciding_citations"] = [citation("ob_formalv2fail", "ob_formalv2fail")]
    assert check_records(records(spec)) == ()


def test_confirming_status_fail_inverts_the_mapping() -> None:
    spec = positive_spec()
    _add_obs(spec, "ob_formalv2fail", "cand_v2", "FAIL")
    data(spec, "tr_F1_1")["proposed_check"]["confirming_status"] = "FAIL"
    _deciding(spec, "ob_formalv2fail")
    assert check_records(records(spec)) == ()
    _deciding(spec, "ob_formalv2")
    assert {v.code for v in check_records(records(spec))} == {C.F5}


def test_non_solver_roles_may_cite_hidden_evidence() -> None:
    """X13/D19: only definite solver provenance is restricted; F3 (reviewer) cites hidden."""
    spec = positive_spec()
    assert data(spec, "F3")["producer"]["role"] == "reviewer"
    data(spec, "F1")["correctness_citations"].append(citation("ob_formalv2", "ob_formalv2"))
    assert check_records(records(spec)) == ()


def test_solver_deciding_citation_of_hidden_evidence_is_f9() -> None:
    spec = positive_spec()
    data(spec, "F1")["producer"] = model_producer("solver")
    assert [v.code for v in check_records(records(spec))] == [C.F9]


# ---- CT-4 (agent deviation for review): packet XR-T1 is implied by XR-B1 + XR-B2 ---------------


@pytest.mark.parametrize("variant", ["other content, same id", "unknown hash"])
def test_ct4_a_mismatched_finding_hash_always_trips_b1_or_b2(variant: str) -> None:
    """Two transitions of one finding_id with different finding_hash values must resolve both
    hashes to Findings carrying that id (else XR-B2): two contents under one id are XR-B1. So
    a separate T1 code could never fire alone, and it cannot pass the isolation harness."""
    spec = positive_spec()
    if variant == "unknown hash":
        data(spec, "tr_F1_2")["finding_hash"] = "sha256:" + "ab" * 32
    else:
        add_after(spec, "F1", "F1_other", Finding, finding(
            "F1", "cand_v2", "R17", model_producer("triage"),
            [citation("ob_simv2", "ob_simv2")], claim="F1: a different claim"))
        data(spec, "tr_F1_2")["finding_hash"] = Ref("F1_other")
    codes = {v.code for v in check_records(records(spec))}
    assert codes and codes <= {C.B1, C.B2}, codes
