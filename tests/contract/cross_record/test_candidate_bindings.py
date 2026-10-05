"""SIN-P1.1-009 K: CandidateManifest <-> task (current authority, X7/X8) and parent ancestry."""

import pytest

from sindri.schemas import CandidateManifest, check_records
from sindri.schemas import InvariantCode as C
from tests.contract.cross_record._bundle import (
    H,
    Spec,
    add,
    add_m1_candidate,
    add_read_only_task,
    candidate,
    data,
    positive_spec,
    records,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids


def _k1_absent_task(spec: Spec) -> None:
    data(spec, "cand_oracle")["task_id"] = "fifo_9999"


def _k2_read_only(spec: Spec) -> None:
    add_read_only_task(spec)
    add(spec, "cand_ro", CandidateManifest,
        candidate("c_fifo_0002_x", "reconstructor", None, None, H("e1"), task_id="fifo_0002"))


def _k3_outside(spec: Spec) -> None:
    data(spec, "cand_oracle")["files"][0]["path"] = "tb/x.sv"


def _k3_raw_prefix(spec: Spec) -> None:
    data(spec, "cand_oracle")["files"][0]["path"] = "rtl/fifo_old.sv"


def _k4_parent_absent(spec: Spec) -> None:
    data(spec, "cand_explorer")["parent_candidate_id"] = "c_fifo_0001_missing"


def _k4_parent_other_task(spec: Spec) -> None:
    add_m1_candidate(spec)
    data(spec, "cand_explorer")["parent_candidate_id"] = "c_fifo_0001_m1_seed"


def _k5_cycle(spec: Spec) -> None:
    body = data(spec, "cand_seed")
    body["parent_candidate_id"] = "c_fifo_0001_e1_v1"
    body["patch_hash"] = H("5e")


def _k6_dependency_none(spec: Spec) -> None:
    data(spec, "cand_oracle")["dependency_hash"] = None


CASES = [
    Case("candidate for an absent task", C.K1, 1, _k1_absent_task),
    Case("candidate for a comprehension task", C.K2, 1, _k2_read_only),
    Case("tb/x.sv outside rtl/fifo", C.K3, 1, _k3_outside),
    Case("rtl/fifo_old.sv is not under rtl/fifo", C.K3, 1, _k3_raw_prefix),
    Case("parent absent", C.K4, 1, _k4_parent_absent),
    Case("parent from another task", C.K4, 1, _k4_parent_other_task),
    Case("seed -> v1 -> seed ancestry cycle", C.K5, 1, _k5_cycle),
    Case("one candidate None, others a bundle hash", C.K6, 1, _k6_dependency_none),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_segment_prefix_paths_are_inside() -> None:
    spec = positive_spec()
    data(spec, "cand_oracle")["files"][0]["path"] = "rtl/fifo/sub/deep.sv"
    assert check_records(records(spec)) == ()


def test_exact_entry_path_is_inside() -> None:
    spec = positive_spec()
    data(spec, "task_v2")["allowed_edit_paths"] = ["rtl/fifo/fifo.sv"]
    assert check_records(records(spec)) == ()


def test_edit_scope_uses_the_set_head_task_revision() -> None:
    """X8: revision 1's broader scope does not excuse a file outside the head's scope."""
    spec = positive_spec()
    data(spec, "task_v1")["allowed_edit_paths"] = ["rtl"]
    data(spec, "cand_oracle")["files"][0]["path"] = "rtl/top.sv"
    assert {v.code for v in check_records(records(spec))} == {C.K3}


def test_all_none_dependency_hashes_are_consistent() -> None:
    spec = positive_spec()
    for name in ("cand_seed", "cand_v1", "cand_v2", "cand_oracle", "cand_explorer"):
        data(spec, name)["dependency_hash"] = None
    assert check_records(records(spec)) == ()
