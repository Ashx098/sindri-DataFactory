"""SIN-P1.1-009 C (domain revision chains, task lineage) and CT-2 (one set head per chain)."""

import pytest

from sindri.schemas import EvaluationPolicy, InvariantCode, check_records
from tests.contract.cross_record._bundle import (
    H,
    Ref,
    Spec,
    add,
    data,
    policy,
    positive_spec,
    records,
    remove,
)
from tests.contract.cross_record._case import Case, assert_isolated, ids

C = InvariantCode
MUTATION_OF_M1 = {"kind": "mutation", "parent_task_id": "fifo_0001_m1", "operator": "x"}


def _skip_version(spec: Spec) -> None:
    data(spec, "task_v2")["manifest_version"] = 3


def _variant_changes(spec: Spec) -> None:
    data(spec, "task_v2")["variant_id"] = "w-d-matrix-v2"


def _contract_and_source_change(spec: Spec) -> None:
    body = data(spec, "task_v2")
    body["contract_id"] = "ct_fifo_0001_b"
    body["source"] = dict(body["source"], commit="0" * 40)


def _split_changes(spec: Spec) -> None:
    remove(spec, "task_m1", "req_m1_r03")  # isolate from the family-level split rule (C6)
    data(spec, "task_v2")["split"] = "dev"


def _requirement_identity_changes(spec: Spec) -> None:
    data(spec, "req_r17_v2")["requirement_id"] = "R03"


def _policy_task_changes(spec: Spec) -> None:
    """A separate, otherwise valid policy chain whose revision 2 moves to another task."""
    first = policy("ep_fifo_x", 1, "fifo_0001", H("a1"))
    first["obligations"] = [first["obligations"][0]]
    second = policy("ep_fifo_x", 2, "fifo_0001_m1", H("a3"), supersedes=Ref("pol_x_v1"))
    second["obligations"] = [second["obligations"][0]]
    add(spec, "pol_x_v1", EvaluationPolicy, first)
    add(spec, "pol_x_v2", EvaluationPolicy, second)


def _family_split_differs(spec: Spec) -> None:
    data(spec, "task_m1")["split"] = "dev"


def _mutation_parent_missing(spec: Spec) -> None:
    data(spec, "task_m1")["source"]["parent_task_id"] = "fifo_9999"


def _mutation_child_invents_family(spec: Spec) -> None:
    data(spec, "task_m1")["family_id"] = "fifo-other"


def _mutation_cycle(spec: Spec) -> None:
    for name in ("task_v1", "task_v2"):
        data(spec, name)["source"] = dict(MUTATION_OF_M1)


CASES = [
    Case("revision 3 supersedes revision 1", C.C1, 1, _skip_version),
    Case("variant_id changes across revisions", C.C3, 1, _variant_changes),
    Case("contract_id and source change (two fields)", C.C3, 2, _contract_and_source_change),
    Case("split changes across revisions", C.C3, 1, _split_changes),
    Case("R17 v2 relabelled as R03", C.C4, 1, _requirement_identity_changes),
    Case("policy revision 2 bound to another task", C.C5, 1, _policy_task_changes),
    Case("family heads carry different splits", C.C6, 1, _family_split_differs),
    Case("mutation parent absent", C.C7, 1, _mutation_parent_missing),
    Case("mutation child invents another family", C.C7, 1, _mutation_child_invents_family),
    Case("mutation ancestry cycle", C.C8, 1, _mutation_cycle),
]


@pytest.mark.parametrize("case", CASES, ids=ids(CASES))
def test_negative_case_is_isolated(case: Case) -> None:
    assert_isolated(case)


def test_cycle_reported_at_smallest_member() -> None:
    spec = positive_spec()
    _mutation_cycle(spec)
    (v,) = check_records(records(spec))
    assert v.subject == "Task:fifo_0001" and "fifo_0001, fifo_0001_m1" in v.detail


# ---- CT-2: B1 + C1 imply one set head per chain key; a fork always trips B1 or C1 --------------


def test_ct2_valid_chains_have_exactly_one_set_head() -> None:
    from sindri.schemas.cross_record import _Bundle

    bundle = _Bundle(records(positive_spec()))
    for kind, chains in bundle.chains.items():
        for key in chains:
            assert bundle.head(kind, key) is not None, (kind.__name__, key)


@pytest.mark.parametrize("version", [2, 3])
def test_ct2_a_fork_trips_b1_or_c1(version: int) -> None:
    spec = positive_spec()
    fork = policy("ep_fifo_main", version, "fifo_0001", H("a2"), supersedes=Ref("pol_v1"))
    fork["exceptions"] = []
    add(spec, "pol_fork", EvaluationPolicy, fork)
    codes = {v.code for v in check_records(records(spec))}
    assert codes & {C.B1, C.C1}, codes
    assert codes <= {C.B1, C.C1}, codes
