"""SIN-P1.1-009 B (bundle structure, hash resolution), API boundary, and CT-3 (no cascades)."""

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from sindri.schemas import InvariantCode, TaskManifest, Violation, check_records
from tests.contract.cross_record._bundle import (
    H,
    Ref,
    Spec,
    clone,
    data,
    positive_spec,
    records,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids

C = InvariantCode


def _dup_observation(spec: Spec) -> None:
    clone(spec, "ob_simv2", "ob_dup", summary="same id, different content")


def _cite_unknown_hash(spec: Spec) -> None:
    data(spec, "F1")["correctness_citations"][0]["observation_hash"] = H("99")


def _cite_wrong_id(spec: Spec) -> None:
    data(spec, "F1")["correctness_citations"][0]["observation_id"] = "ob_other"


def _type_confusion(spec: Spec) -> None:
    data(spec, "ob_simtimeout")["policy_hash"] = Ref("cand_seed")


CASES = [
    Case("same observation_id, different content", C.B1, 1, _dup_observation),
    Case("citation hash names nothing", C.B2, 1, _cite_unknown_hash),
    Case("citation hash right, observation_id wrong", C.B2, 1, _cite_wrong_id),
    Case("policy_hash is a candidate's content_id", C.B2, 1, _type_confusion),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_positive_bundle_is_clean() -> None:
    assert check_records(records(positive_spec())) == ()


def test_positive_bundle_covers_every_record_type() -> None:
    kinds = {type(r).__name__ for r in records(positive_spec())}
    assert kinds == {"TaskManifest", "Requirement", "EvaluationPolicy", "CandidateManifest",
                     "Observation", "Finding", "FindingTransition", "EpisodeBudget",
                     "EpisodeState"}


# ---- X2/X3: API boundary, determinism, idempotence ---------------------------------------------


def test_non_record_values_raise_type_error() -> None:
    with pytest.raises(TypeError, match="Records only"):
        check_records([{"task_id": "fifo_0001"}])  # type: ignore[list-item]


class _ExtendedTask(TaskManifest):
    pass


def test_unsupported_record_subclass_raises_type_error() -> None:
    task = records(positive_spec())[0]
    sub = _ExtendedTask.model_validate(task.model_dump())
    with pytest.raises(TypeError, match="unsupported Record type"):
        check_records([sub])


def test_violation_is_a_frozen_strict_value_not_a_record() -> None:
    v = Violation(code=C.B1, subject="s", detail="d")
    assert not hasattr(v, "content_id") and "schema_version" not in Violation.model_fields
    with pytest.raises(ValidationError):
        Violation(code=C.B1, subject="s", detail="d", extra="x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Violation(code="XR-NOPE", subject="s", detail="d")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        v.detail = "changed"  # type: ignore[misc]


def test_input_records_are_not_mutated() -> None:
    rs = records(positive_spec())
    before = [r.content_id() for r in rs]
    check_records(rs)
    assert [r.content_id() for r in rs] == before


@settings(max_examples=25, deadline=None)
@given(st.randoms(use_true_random=False), st.integers(0, 5))
def test_result_is_order_independent_and_idempotent(rng: random.Random, dups: int) -> None:
    """Shuffled input with duplicated identical records yields an identical result."""
    case = CASES[0]  # a non-empty result makes ordering observable
    base = records(case.spec())
    expected = check_records(base)
    shuffled = list(base) + rng.sample(base, k=min(dups, len(base)))
    rng.shuffle(shuffled)
    assert check_records(shuffled) == expected


def test_results_are_sorted_by_code_subject_detail() -> None:
    spec = positive_spec()
    _dup_observation(spec)
    _cite_unknown_hash(spec)
    found = check_records(records(spec))
    assert list(found) == sorted(found, key=lambda v: (v.code.value, v.subject, v.detail))
    assert {v.code for v in found} == {C.B1, C.B2}


# ---- CT-3: dependency ordering (no cascades) ---------------------------------------------------


def test_ct3_unresolved_reference_reports_once_and_dependants_skip() -> None:
    """A dangling candidate hash on an Observation would otherwise also fail O1/O2/F3."""
    spec = positive_spec()
    data(spec, "ob_simv2")["candidate_manifest_hash"] = H("77")
    found = check_records(records(spec))
    # F1/F2 still cite ob_simv2 exactly (Ref follows its new content_id); F3 must not report
    # the cited Observation's broken binding a second time.
    assert [(v.code, v.subject) for v in found] == [(C.B2, "Observation:ob_simv2")]


def test_ct3_ambiguous_key_suppresses_dependants() -> None:
    """Two revision-2 tasks (B1) make the task head ambiguous: K/P/F rules skip, no cascade."""
    spec = positive_spec()
    clone(spec, "task_v2", "task_v2_fork", variant_id="w-d-matrix")  # identical: collapses
    assert check_records(records(spec)) == ()
    data(spec, "task_v2_fork")["allowed_edit_paths"] = ["rtl/other"]
    found = check_records(records(spec))
    assert {v.code for v in found} == {C.B1}


def test_ct3_terminal_ownership_t5_not_t4_and_e4_not_e2() -> None:
    from tests.contract.cross_record.test_episode_chains import _after_completed
    from tests.contract.cross_record.test_finding_bindings import _after_terminal

    spec = positive_spec()
    _after_terminal(spec)
    _after_completed(spec)
    assert {v.code for v in check_records(records(spec))} == {C.T5, C.E4}


def test_ct3_f4_owns_non_verdict_status_not_f5() -> None:
    from tests.contract.cross_record.test_finding_bindings import _decide_with_timeout

    spec = positive_spec()
    _decide_with_timeout(spec)
    assert {v.code for v in check_records(records(spec))} == {C.F4}


def test_ct3_sequence_gap_is_t2_and_e1_only() -> None:
    from tests.contract.cross_record.test_episode_chains import _e1_gap
    from tests.contract.cross_record.test_finding_bindings import _t2_gap

    spec = positive_spec()
    _t2_gap(spec)
    _e1_gap(spec)
    assert {v.code for v in check_records(records(spec))} == {C.T2, C.E1}


def test_ct3_policy_vocabulary_owner_suppresses_coverage() -> None:
    """P8 failing for the head policy means P5/P6/P7 skip it (no vocabulary to judge by)."""
    from tests.contract.cross_record.test_policy_coverage import _p8_drop_depth

    spec = positive_spec()
    _p8_drop_depth(spec)
    data(spec, "pol_v2")["exceptions"][0]["excludes"].append(
        {"check_id": "chk_sim", "configuration_id": "cfg_w1_d2"})  # would be a P6 gap
    assert {v.code for v in check_records(records(spec))} == {C.P8}


# ---- CT-3 review fixes (PR #28 coordinator comment 5988729778) ---------------------------------


def test_ct3_unknown_previous_transition_hash_is_b2_only() -> None:
    spec = positive_spec()
    data(spec, "tr_F1_2")["previous_transition_hash"] = H("ab")  # contiguous pair, hash broken
    assert {v.code for v in check_records(records(spec))} == {C.B2}


def test_ct3_unknown_previous_state_hash_is_b2_only() -> None:
    spec = positive_spec()
    data(spec, "e1_s12")["previous_state_hash"] = H("ab")  # contiguous pair, hash broken
    assert {v.code for v in check_records(records(spec))} == {C.B2}


def test_ct3_ambiguous_transition_key_does_not_drive_f5_f7() -> None:
    """Two contents at (F2, 2); one would make the probe-proposed F2 look decided."""
    spec = positive_spec()
    clone(spec, "tr_F2_2", "tr_F2_2_conflict", to_status="confirmed", drop_reason=None,
          deciding_citations=[{"observation_id": "ob_simv2", "observation_hash": Ref("ob_simv2")}])
    assert {v.code for v in check_records(records(spec))} == {C.B1}


def test_ct3_ambiguous_candidate_source_does_not_drive_k5() -> None:
    """A conflicting c_fifo_0001_seed whose parent is v1 would close seed -> v1 -> seed."""
    spec = positive_spec()
    clone(spec, "cand_seed", "cand_seed_conflict", parent_candidate_id="c_fifo_0001_e1_v1",
          patch_hash=H("5e"))
    assert {v.code for v in check_records(records(spec))} == {C.B1}


def test_ct3_ambiguous_finding_source_does_not_drive_f11() -> None:
    """A conflicting F3 derived from F4 (F4 derives from F3) would close a derived_from cycle."""
    spec = positive_spec()
    clone(spec, "F3", "F3_conflict", derived_from="F4")
    assert {v.code for v in check_records(records(spec))} == {C.B1}


def test_ct3_broken_transition_owner_does_not_drive_f11() -> None:
    """F4 superseded by F3 would close a superseded_by cycle, but its finding_hash is broken."""
    from sindri.schemas import FindingTransition
    from tests.contract.cross_record._bundle import add, transition

    spec = positive_spec()
    add(spec, "tr_F4_1", FindingTransition, transition(
        "F4", "F4", 1, None, "hypothesis", "dropped", drop_reason="superseded",
        superseded_by="F3"))
    data(spec, "tr_F4_1")["finding_hash"] = H("ab")
    assert {v.code for v in check_records(records(spec))} == {C.B2}
