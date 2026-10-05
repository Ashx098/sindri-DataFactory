"""SIN-P1.1-009 E: EpisodeState chains (ADR-0006 edges, WAITING resume, constants, accounting,
truthful abort reasons incl. N3 zero-limit semantics, candidate bindings, pending jobs)."""

import copy
from typing import Any

import pytest

from sindri.schemas import CandidateManifest, EpisodeBudget, EpisodeState, check_records
from sindri.schemas import InvariantCode as C
from tests.contract.cross_record._bundle import (
    E1_PLAN,
    E2_PLAN,
    H,
    Ref,
    Spec,
    add,
    add_after,
    add_m1_candidate,
    add_m1_policy,
    binding,
    budget,
    candidate,
    data,
    episode,
    job,
    positive_spec,
    records,
    state,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids

Plan = list[tuple[str, dict[str, Any]]]


def _e2(spec: Spec, plan: Plan, **common: Any) -> None:
    episode(spec, "e2", plan, common.pop("budget_ref", "budget_mixed"), **common)


def _e2_plan() -> Plan:
    return copy.deepcopy(E2_PLAN)


def _e1_gap(spec: Spec) -> None:
    data(spec, "e1_s12")["sequence"] = 13


def _e1_wrong_predecessor(spec: Spec) -> None:
    data(spec, "e1_s12")["previous_state_hash"] = Ref("e1_s10")


def _e2_plan_to_submit(spec: Spec) -> None:
    plan = _e2_plan()
    plan[2] = ("SUBMIT", {"active": "cand_seed", "spent": {"tool_calls": 4}, "elapsed": 2000})
    _e2(spec, plan)


def _waiting_plan(resume: str) -> Plan:
    plan = _e2_plan()
    plan.insert(2, ("WAITING", {"spent": {"tool_calls": 2}, "elapsed": 1500, "resume": resume,
                                "jobs": [job("job_wait_1", "73", None, tool_calls=1)]}))
    return plan


def _e3_resumes_elsewhere(spec: Spec) -> None:
    _e2(spec, _waiting_plan("PLAN"))  # PLAN -> WAITING(resume=PLAN) -> IMPLEMENT


def _e3_records_wrong_pause(spec: Spec) -> None:
    _e2(spec, _waiting_plan("IMPLEMENT"))  # paused in PLAN but records IMPLEMENT


def _e3_both(spec: Spec) -> None:
    data(spec, "e1_s3")["resume_state"] = "PLAN"  # entry and exit both wrong


def _after_completed(spec: Spec) -> None:
    final = copy.deepcopy(E1_PLAN[-1][1])
    final.pop("best")
    add(spec, "e1_s13", EpisodeState,
        state("e1", 13, "e1_s12", "RECORD", budget_ref="budget_main", **final))


def _e5_budget_changes(spec: Spec) -> None:
    add_after(spec, "budget_mixed", "budget_big", EpisodeBudget, budget(
        tokens=5000, tool_calls=50, candidate_versions=9, sim_jobs=20, formal_ms=900000,
        repair_attempts=5))
    data(spec, "e1_s3")["budget_hash"] = Ref("budget_big")


def _e6_policy_of_other_task(spec: Spec) -> None:
    add_m1_policy(spec)
    _e2(spec, _e2_plan(), policy_ref="pol_m1", policy_id="ep_fifo_m1")


def _e7_spent_decreases(spec: Spec) -> None:
    data(spec, "e1_s6")["spent"]["tool_calls"] = 2


def _e8_overspend(spec: Spec) -> None:
    data(spec, "e1_s12")["spent"]["sim_jobs"] = 5


def _e8_wrong_exemption(spec: Spec) -> None:
    body = data(spec, "e2_s3")
    body["abort_reason"], body["wall_clock_elapsed_ms"] = "wall_clock_exhausted", 100000


def _e9_other_episode(spec: Spec) -> None:
    add_after(spec, "cand_explorer", "cand_e9", CandidateManifest,
              candidate("c_fifo_0001_e9_v1", "solver", "e9", "c_fifo_0001_seed", H("f6")))
    data(spec, "e1_s12")["best_candidate"] = binding("cand_e9")


def _e9_other_task(spec: Spec) -> None:
    add_m1_candidate(spec)
    data(spec, "e1_s8")["pending_jobs"][0]["candidate"] = binding("cand_m1")


def _e10_request_changes(spec: Spec) -> None:
    body = data(spec, "e1_s9")
    body["pending_jobs"] = [job("job_sim_2", "79", "cand_v2", sim_jobs=1)]
    body["reserved"]["sim_jobs"] = 1


def _e10_reappears(spec: Spec) -> None:
    body = data(spec, "e1_s10")
    body["pending_jobs"] = [job("job_sim_2", "72", "cand_v2", sim_jobs=1)]
    body["reserved"]["sim_jobs"] = 1


def _e11_untruthful_budget(spec: Spec) -> None:
    data(spec, "e2_s3")["spent"]["tool_calls"] = 4  # only zero-limit dimensions are "at" limit


def _e11_untruthful_wall_clock(spec: Spec) -> None:
    body = data(spec, "e2_s3")
    body["abort_reason"] = "wall_clock_exhausted"
    body["spent"]["tool_calls"] = 4


CASES = [
    Case("sequence gap 11 -> 13", C.E1, 1, _e1_gap),
    Case("predecessor hash of n-2", C.E1, 1, _e1_wrong_predecessor),
    Case("PLAN -> SUBMIT", C.E2, 1, _e2_plan_to_submit),
    Case("WAITING(resume=PLAN) exits to IMPLEMENT", C.E3, 1, _e3_resumes_elsewhere),
    Case("paused in PLAN, records resume IMPLEMENT", C.E3, 1, _e3_records_wrong_pause),
    Case("wrong entry and wrong exit (two pairs)", C.E3, 2, _e3_both),
    Case("snapshot after COMPLETED", C.E4, 1, _after_completed),
    Case("budget_hash changes at sequence 3", C.E5, 1, _e5_budget_changes),
    Case("episode bound to another task's policy", C.E6, 4, _e6_policy_of_other_task),
    Case("spent.tool_calls decreases", C.E7, 1, _e7_spent_decreases),
    Case("sim_jobs overspend at COMPLETED", C.E8, 1, _e8_overspend),
    Case("additive overspend at wall_clock_exhausted", C.E8, 1, _e8_wrong_exemption),
    Case("best candidate from another episode", C.E9, 1, _e9_other_episode),
    Case("pending job bound to another task's candidate", C.E9, 1, _e9_other_task),
    Case("same JobId, new request_hash", C.E10, 1, _e10_request_changes),
    Case("job reappears after leaving", C.E10, 1, _e10_reappears),
    Case("budget_exhausted: only zero-limit dimensions at limit", C.E11, 1,
         _e11_untruthful_budget),
    Case("wall_clock_exhausted below the wall limit", C.E11, 1, _e11_untruthful_wall_clock),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_all_zero_budget_allows_budget_exhausted_at_zero_usage() -> None:
    """N3: with no additive budget at all, budget_exhausted is truthful at zero usage."""
    spec = positive_spec()
    add_after(spec, "budget_mixed", "budget_zero", EpisodeBudget, budget(wall=100000))
    plan: Plan = [("PREPARE", {}), ("PLAN", {}), ("IMPLEMENT", {}),
                  ("ABORTED", {"abort": "budget_exhausted"})]
    _e2(spec, plan, budget_ref="budget_zero")
    assert check_records(records(spec)) == ()


def test_reconstructor_seed_is_a_valid_episode_candidate() -> None:
    """E9 (relaxed by the coordinator): a candidate without an episode may seed any episode."""
    spec = positive_spec()
    assert data(spec, "cand_seed")["episode_id"] is None
    assert data(spec, "e1_s1")["active_candidate"] == binding("cand_seed")
    assert check_records(records(spec)) == ()


def test_waiting_may_abort() -> None:
    spec = positive_spec()
    plan = _waiting_plan("PLAN")
    del plan[3]  # WAITING -> ABORTED directly
    _e2(spec, plan)
    assert check_records(records(spec)) == ()
