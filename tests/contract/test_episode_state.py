"""Contract tests for EpisodeState and EpisodeBudget (SIN-P1.1-007; ED1–ED15; ADR-0006)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.schemas import (
    ACTIVE_EPISODE_STATES,
    ALLOWED_EPISODE_TRANSITIONS,
    CANDIDATE_REQUIRED_STATES,
    BudgetVector,
    EpisodeBudget,
    EpisodeState,
    EpisodeStatus,
)

EX = Path(__file__).parent / "examples"
BUDGET = json.loads((EX / "episode_budget.json").read_text())
STATE = json.loads((EX / "episode_state.json").read_text())
ZERO = dict.fromkeys(BudgetVector.model_fields, 0)


def H(byte: str) -> str:
    return "sha256:" + byte * 32


def state(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(STATE)
    data.update(changes)
    return data


def settled(st: str, **changes: Any) -> dict[str, Any]:
    """A non-WAITING snapshot in state `st` with no pending jobs (valid by default)."""
    base = state(state=st, resume_state=None, pending_jobs=[], reserved=dict(ZERO),
                 abort_reason="cancelled" if st == "ABORTED" else None)
    base.update(changes)
    return base


def rejects(model: Any, data: dict[str, Any], match: str | None = None) -> None:
    with pytest.raises(ValidationError, match=match):
        model.model_validate(data)


# ---- examples, budget ---------------------------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    s = EpisodeState.model_validate(STATE)
    assert EpisodeState.model_validate_json(s.model_dump_json()) == s
    assert json.loads(s.model_dump_json()) == STATE
    assert s.state is EpisodeStatus.WAITING and len(s.pending_jobs) == 2


def test_budget_example_and_zero_additive_limits() -> None:
    assert EpisodeBudget.model_validate(BUDGET).wall_clock_limit_ms == 3600000
    zero_tokens = {**BUDGET, "limits": {**BUDGET["limits"], "tokens": 0, "formal_ms": 0}}
    assert EpisodeBudget.model_validate(zero_tokens).limits.tokens == 0  # disabled resource


@pytest.mark.parametrize("limit", [0, -1, 1.0, "3600000", True])
def test_wall_clock_limit_is_positive_strict_int(limit: Any) -> None:
    rejects(EpisodeBudget, {**BUDGET, "wall_clock_limit_ms": limit})


@pytest.mark.parametrize("field", ["budget_id", "remaining", "wall_clock_ms"])
def test_budget_has_no_id_or_stored_remaining(field: str) -> None:
    rejects(EpisodeBudget, {**BUDGET, field: 1})


def test_wall_clock_is_not_an_additive_dimension() -> None:
    assert "wall_clock_ms" not in BudgetVector.model_fields
    rejects(EpisodeBudget, {**BUDGET, "limits": {**BUDGET["limits"], "wall_clock_ms": 1}})


def test_remaining_is_derived_against_the_bound_budget() -> None:
    budget = EpisodeBudget.model_validate(BUDGET)
    rem = budget.remaining(EpisodeState.model_validate(STATE))
    assert rem.tokens == 200000 - 84211
    assert rem.formal_ms == 1800000 - 481000 - 600000  # spent and reserved both count
    assert rem.sim_jobs == 40 - 9 - 1
    assert rem.wall_clock_ms == 3600000 - 611000


def test_remaining_refuses_a_snapshot_of_another_budget() -> None:
    other = EpisodeBudget.model_validate({**BUDGET, "wall_clock_limit_ms": 1})
    with pytest.raises(ValueError, match="different EpisodeBudget"):
        other.remaining(EpisodeState.model_validate(STATE))


# ---- lifecycle data (ADR-0006) ------------------------------------------------------------------


def test_states_are_exactly_adr_0006() -> None:
    assert {s.value for s in EpisodeStatus} == {
        "PREPARE", "PLAN", "IMPLEMENT", "DEV_CHECK", "TRIAGE", "REPAIR", "SUBMIT", "JUDGE",
        "RECORD", "WAITING", "COMPLETED", "ABORTED",
    }


def test_transition_table_contains_the_lifecycle_and_no_shortcuts() -> None:
    s = EpisodeStatus
    for edge in [(s.PREPARE, s.PLAN), (s.DEV_CHECK, s.SUBMIT), (s.DEV_CHECK, s.TRIAGE),
                 (s.TRIAGE, s.REPAIR), (s.REPAIR, s.DEV_CHECK), (s.RECORD, s.COMPLETED),
                 (s.WAITING, s.DEV_CHECK), (s.JUDGE, s.WAITING), (s.WAITING, s.ABORTED)]:
        assert edge in ALLOWED_EPISODE_TRANSITIONS
    for edge in [(s.PREPARE, s.SUBMIT), (s.IMPLEMENT, s.JUDGE), (s.COMPLETED, s.PREPARE),
                 (s.ABORTED, s.PLAN), (s.WAITING, s.COMPLETED), (s.WAITING, s.WAITING),
                 (s.RECORD, s.PREPARE)]:
        assert edge not in ALLOWED_EPISODE_TRANSITIONS
    assert not any(a in (s.COMPLETED, s.ABORTED) for a, _ in ALLOWED_EPISODE_TRANSITIONS)


# ---- positive snapshots -------------------------------------------------------------------------


def test_first_snapshot_prepare_without_candidates() -> None:
    s = EpisodeState.model_validate(settled("PREPARE", sequence=0, previous_state_hash=None,
                                            active_candidate=None, best_candidate=None,
                                            checkpoint_ref=None))
    assert s.sequence == 0 and s.checkpoint_ref is None


def test_first_implement_snapshot_may_precede_the_candidate() -> None:
    EpisodeState.model_validate(settled("IMPLEMENT", active_candidate=None, best_candidate=None))


def test_waiting_resuming_to_plan_needs_no_candidate() -> None:
    EpisodeState.model_validate(state(resume_state="PLAN", active_candidate=None,
                                      best_candidate=None))


def test_candidate_less_waiting_to_plan_with_candidate_less_job() -> None:
    """PR #19 review: WAITING -> PLAN, no active candidate, pending job with candidate=None."""
    jobs = copy.deepcopy(STATE["pending_jobs"])[:1]
    jobs[0]["candidate"] = None
    s = EpisodeState.model_validate(state(resume_state="PLAN", active_candidate=None,
                                          best_candidate=None, pending_jobs=jobs,
                                          reserved=jobs[0]["reserved"]))
    assert s.pending_jobs[0].candidate is None and s.resume_state is EpisodeStatus.PLAN


@pytest.mark.parametrize("st", ["COMPLETED", "ABORTED"])
def test_terminal_snapshots_with_zero_jobs(st: str) -> None:
    EpisodeState.model_validate(settled(st))


def test_aborted_may_have_no_candidate() -> None:
    EpisodeState.model_validate(settled("ABORTED", active_candidate=None, best_candidate=None,
                                        abort_reason="budget_exhausted"))


def test_pending_jobs_allowed_in_active_states() -> None:
    EpisodeState.model_validate(state(state="DEV_CHECK", resume_state=None))


# ---- negative snapshots -------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(STATE))
def test_every_field_is_required(field: str) -> None:
    data = state()
    del data[field]
    rejects(EpisodeState, data)


@pytest.mark.parametrize("field", ["budget_id", "best_reason", "budget_remaining", "limits",
                                   "failure_signature_hash", "status"])
def test_removed_or_derived_fields_rejected(field: str) -> None:
    rejects(EpisodeState, state(**{field: "x"}))


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"pending_jobs": [], "reserved": ZERO}, "at least one pending job"),
        ({"resume_state": None}, "resumes to an active state"),
        ({"resume_state": "WAITING"}, "resumes to an active state"),
        ({"resume_state": "COMPLETED"}, "resumes to an active state"),
        ({"resume_state": "ABORTED"}, "resumes to an active state"),
    ],
)
def test_waiting_rules(changes: dict[str, Any], match: str) -> None:
    rejects(EpisodeState, state(**changes), match=match)


def test_only_waiting_has_a_resume_state() -> None:
    rejects(EpisodeState, settled("PLAN", resume_state="PLAN"), match="only WAITING")


@pytest.mark.parametrize("st", sorted(s.value for s in CANDIDATE_REQUIRED_STATES))
def test_candidate_required_states(st: str) -> None:
    rejects(EpisodeState, settled(st, active_candidate=None), match="requires an active_candidate")


def test_waiting_inherits_the_candidate_rule_of_its_resume_state() -> None:
    rejects(EpisodeState, state(resume_state="DEV_CHECK", active_candidate=None),
            match="requires an active_candidate")


@pytest.mark.parametrize("st", ["COMPLETED", "ABORTED"])
def test_terminal_states_have_no_pending_jobs(st: str) -> None:
    rejects(EpisodeState, state(state=st, resume_state=None,
                                abort_reason="cancelled" if st == "ABORTED" else None),
            match="no pending jobs")


def test_abort_reason_exactly_on_aborted() -> None:
    rejects(EpisodeState, settled("ABORTED", abort_reason=None), match="abort_reason")
    rejects(EpisodeState, settled("PLAN", abort_reason="cancelled"), match="abort_reason")
    rejects(EpisodeState, settled("ABORTED", abort_reason="bored"))


def test_pending_job_needs_request_hash_and_exact_candidate() -> None:
    jobs = copy.deepcopy(STATE["pending_jobs"])
    del jobs[0]["request_hash"]
    rejects(EpisodeState, state(pending_jobs=jobs))
    jobs = copy.deepcopy(STATE["pending_jobs"])
    del jobs[0]["candidate"]["candidate_manifest_hash"]
    rejects(EpisodeState, state(pending_jobs=jobs))


def test_pending_job_candidate_key_is_required_even_when_null() -> None:
    jobs = copy.deepcopy(STATE["pending_jobs"])
    del jobs[0]["candidate"]
    rejects(EpisodeState, state(pending_jobs=jobs))


def test_pending_job_has_no_action_field() -> None:
    """ADR-0005: jobs are broader than Observations; request_hash identifies the request."""
    jobs = copy.deepcopy(STATE["pending_jobs"])
    jobs[0]["action"] = "run_formal"
    rejects(EpisodeState, state(pending_jobs=jobs))


def test_candidate_bindings_need_manifest_hashes() -> None:
    rejects(EpisodeState, state(active_candidate={"candidate_id": "c_x_v1"}))
    rejects(EpisodeState, state(best_candidate={"candidate_id": "c_x_v1"}))


def test_duplicate_job_ids_rejected() -> None:
    jobs = copy.deepcopy(STATE["pending_jobs"])
    jobs[1]["job_id"] = jobs[0]["job_id"]
    rejects(EpisodeState, state(pending_jobs=jobs), match="unique")


@pytest.mark.parametrize(
    "reserved",
    [ZERO, {**ZERO, "formal_ms": 600000}, {**ZERO, "formal_ms": 600000, "sim_jobs": 2}],
)
def test_reserved_must_equal_sum_of_job_reservations(reserved: dict[str, int]) -> None:
    rejects(EpisodeState, state(reserved=reserved), match="sum of pending-job reservations")


@pytest.mark.parametrize(
    ("field", "value"),
    [("spent", {**STATE["spent"], "tokens": -1}), ("spent", {**STATE["spent"], "tokens": 1.5}),
     ("wall_clock_elapsed_ms", -1), ("wall_clock_elapsed_ms", 611.0),
     ("sequence", -1), ("spent", {**STATE["spent"], "wall_clock_ms": 1})],
)
def test_accounting_values_are_exact_non_negative(field: str, value: Any) -> None:
    rejects(EpisodeState, state(**{field: value}))


@pytest.mark.parametrize(
    "changes",
    [{"last_failure_signature": H("f5"), "failure_repeat_count": 0},
     {"last_failure_signature": None, "failure_repeat_count": 1}],
)
def test_failure_signature_and_repeat_count_agree(changes: dict[str, Any]) -> None:
    rejects(EpisodeState, state(**changes), match="repeat count")


def test_no_failure_yet() -> None:
    EpisodeState.model_validate(state(last_failure_signature=None, failure_repeat_count=0))


@pytest.mark.parametrize(
    "changes",
    [{"sequence": 0, "previous_state_hash": H("e6")},
     {"sequence": 7, "previous_state_hash": None}],
)
def test_chain_head_rules(changes: dict[str, Any]) -> None:
    rejects(EpisodeState, state(**changes), match="sequence 0")


def test_restart_fields_are_all_required() -> None:
    """ED13: every field a crash-restart reads must be present (none may be defaulted)."""
    restart = {"episode_id", "task_id", "sequence", "previous_state_hash", "policy_id",
               "policy_hash", "budget_hash", "solver_config_hash", "state", "resume_state",
               "active_candidate", "best_candidate", "pending_jobs", "spent", "reserved",
               "wall_clock_elapsed_ms", "last_failure_signature", "failure_repeat_count",
               "checkpoint_ref"}
    fields = EpisodeState.model_fields
    assert restart <= set(fields)
    assert all(fields[f].is_required() for f in restart)


def test_active_states_exclude_waiting_and_terminals() -> None:
    assert EpisodeStatus.WAITING not in ACTIVE_EPISODE_STATES
    assert not ACTIVE_EPISODE_STATES & {EpisodeStatus.COMPLETED, EpisodeStatus.ABORTED}


def test_records_are_immutable() -> None:
    s = EpisodeState.model_validate(STATE)
    with pytest.raises(ValidationError):
        s.state = EpisodeStatus.COMPLETED  # type: ignore[misc]
    with pytest.raises(ValidationError):
        s.spent.tokens = 0  # type: ignore[misc]
