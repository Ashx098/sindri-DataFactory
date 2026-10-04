"""Contract tests for Finding and FindingTransition (SIN-P1.1-006; FD1–FD12; ADR-0005)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.schemas import (
    ALLOWED_FINDING_TRANSITIONS,
    Finding,
    FindingStatus,
    FindingTransition,
)

EX = Path(__file__).parent / "examples"
FINDING = json.loads((EX / "finding.json").read_text())
CHECK_PROPOSED = json.loads((EX / "finding_transition_check_proposed.json").read_text())
CONFIRMED = json.loads((EX / "finding_transition_confirmed.json").read_text())


def H(byte: str) -> str:
    return "sha256:" + byte * 32


CITATION = {"observation_id": "ob_88121", "observation_hash": H("0b")}
EXISTING = {"proposal_kind": "existing_policy_check", "policy_hash": H("b9"),
            "check_id": "chk_stall", "configuration_id": "cfg_w8_d8"}


def finding(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(FINDING)
    data.update(changes)
    return data


def transition(frm: str, to: str, **changes: Any) -> dict[str, Any]:
    """A valid-by-default transition for the edge, as the second link of a chain unless frm is
    hypothesis (then it is the chain head)."""
    head = frm == "hypothesis"
    data = {
        "schema_version": 1, "finding_id": "F42", "finding_hash": H("f4"),
        "sequence": 1 if head else 2, "previous_transition_hash": None if head else H("7a"),
        "from_status": frm, "to_status": to,
        "proposed_check": EXISTING if to == "check_proposed" else None,
        "deciding_citations": [CITATION] if to in ("confirmed", "refuted") else [],
        "drop_reason": "no_executable_check" if to == "dropped" else None,
        "superseded_by": None,
    }
    data.update(changes)
    return data


def rejects(model: Any, data: dict[str, Any], match: str | None = None) -> None:
    with pytest.raises(ValidationError, match=match):
        model.model_validate(data)


# ---- Finding: positive --------------------------------------------------------------------------


def test_master_example_finding_validates_and_round_trips() -> None:
    f = Finding.model_validate(FINDING)
    assert Finding.model_validate_json(f.model_dump_json()) == f
    assert json.loads(f.model_dump_json()) == FINDING


def test_finding_with_only_supporting_evidence_is_a_hypothesis() -> None:
    assert Finding.model_validate(FINDING).correctness_citations == ()


def test_finding_with_observation_citation_validates() -> None:
    assert Finding.model_validate(finding(correctness_citations=[CITATION])).correctness_citations


@pytest.mark.parametrize(
    "producer",
    [
        {"kind": "model", "role": "critic", "model": "m", "model_version": "1",
         "provenance_ref": "gw:1", "training_allowed": False},
        {"kind": "component", "role": "triage", "component": "triage-normalizer",
         "component_version": "0.1.0", "component_hash": H("cc"), "provenance_ref": "build:42",
         "training_allowed": True},
        {"kind": "human", "role": "reviewer", "reviewer_ref": "reviewer:avinash",
         "provenance_ref": "review:pr17", "training_allowed": False},
    ],
    ids=["model", "component", "human"],
)
def test_every_producer_kind_validates(producer: dict[str, Any]) -> None:
    assert Finding.model_validate(finding(producer=producer)).producer.kind == producer["kind"]


# ---- Finding: negative --------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(FINDING))
def test_every_finding_field_is_required(field: str) -> None:
    data = finding()
    del data[field]
    rejects(Finding, data)


@pytest.mark.parametrize("field", ["status", "proposed_check", "rank", "actor"])
def test_lifecycle_and_removed_fields_are_not_on_finding(field: str) -> None:
    rejects(Finding, finding(**{field: "x"}))


def test_finding_must_name_evidence() -> None:
    rejects(Finding, finding(correctness_citations=[], supporting_evidence=[]), match="evidence")


def test_finding_cannot_derive_from_itself() -> None:
    rejects(Finding, finding(derived_from="F42"), match="derived")


def test_citation_needs_both_id_and_hash() -> None:
    rejects(Finding, finding(correctness_citations=[{"observation_id": "ob_1"}]))
    rejects(Finding, finding(correctness_citations=[CITATION, CITATION]), match="duplicates")


@pytest.mark.parametrize(
    "producer",
    [
        {"kind": "model", "role": "critic", "model": "m", "provenance_ref": "gw:1",
         "training_allowed": False},  # no model_version
        {"kind": "component", "role": "triage", "component": "c", "component_version": "1",
         "provenance_ref": "b", "training_allowed": True},  # no component_hash
        {"kind": "human", "role": "reviewer", "provenance_ref": "r",
         "training_allowed": False},  # no reviewer_ref
        {"kind": "model", "role": "critic", "model": "m", "model_version": "1",
         "provenance_ref": "gw:1"},  # training_allowed missing
        {"kind": "model", "role": "critic", "model": "m", "model_version": "1",
         "provenance_ref": "gw:1", "training_allowed": 1},  # not a strict bool
        {"kind": "agent", "role": "critic", "provenance_ref": "x", "training_allowed": True},
        {"kind": "model", "role": "oracle", "model": "m", "model_version": "1",
         "provenance_ref": "gw:1", "training_allowed": True},  # unknown role
    ],
)
def test_bad_producers_rejected(producer: dict[str, Any]) -> None:
    rejects(Finding, finding(producer=producer))


@pytest.mark.parametrize(("field", "value"), [("uncertainty", "0.7"), ("uncertainty", 0.7),
                                              ("claim", ""), ("claim", "x" * 501),
                                              ("requirement_id", ["R17", "R03"])])
def test_bad_claim_values_rejected(field: str, value: Any) -> None:
    rejects(Finding, finding(**{field: value}))


def test_cycle_window_must_be_ordered() -> None:
    art = {"kind": "trace", "hash": H("88"), "cycle_window": {"start": 48, "end": 40}}
    rejects(Finding, finding(supporting_evidence=[art]), match="cycle window")


def test_finding_is_immutable() -> None:
    f = Finding.model_validate(FINDING)
    with pytest.raises(ValidationError):
        f.claim = "changed"  # type: ignore[misc]


# ---- FindingTransition: positive ----------------------------------------------------------------


def test_example_transitions_validate_and_round_trip() -> None:
    for data in (CHECK_PROPOSED, CONFIRMED):
        t = FindingTransition.model_validate(data)
        assert json.loads(t.model_dump_json()) == data


def test_check_proposed_with_existing_policy_check_or_probe() -> None:
    FindingTransition.model_validate(transition("hypothesis", "check_proposed"))
    FindingTransition.model_validate(CHECK_PROPOSED)  # development probe


@pytest.mark.parametrize("to", ["confirmed", "refuted"])
def test_decisions_with_deciding_citations(to: str) -> None:
    assert FindingTransition.model_validate(transition("check_proposed", to)).deciding_citations


def test_drops() -> None:
    FindingTransition.model_validate(transition("hypothesis", "dropped"))
    FindingTransition.model_validate(transition("check_proposed", "dropped",
                                                drop_reason="superseded", superseded_by="F43"))


def test_edge_table_is_exactly_fd2() -> None:
    s = FindingStatus
    assert ALLOWED_FINDING_TRANSITIONS == {
        (s.HYPOTHESIS, s.CHECK_PROPOSED), (s.CHECK_PROPOSED, s.CONFIRMED),
        (s.CHECK_PROPOSED, s.REFUTED), (s.HYPOTHESIS, s.DROPPED), (s.CHECK_PROPOSED, s.DROPPED),
    }


# ---- FindingTransition: negative ----------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(CONFIRMED))
def test_every_transition_field_is_required(field: str) -> None:
    data = copy.deepcopy(CONFIRMED)
    del data[field]
    rejects(FindingTransition, data)


@pytest.mark.parametrize("field", ["actor", "direction", "rank", "supporting_evidence"])
def test_removed_fields_are_not_on_transitions(field: str) -> None:
    rejects(FindingTransition, {**CONFIRMED, field: "x"})


@pytest.mark.parametrize(
    ("frm", "to"),
    [("hypothesis", "confirmed"), ("hypothesis", "refuted"), ("confirmed", "refuted"),
     ("refuted", "check_proposed"), ("dropped", "hypothesis"), ("check_proposed", "hypothesis"),
     ("confirmed", "dropped")],
)
def test_edges_outside_the_table_rejected(frm: str, to: str) -> None:
    rejects(FindingTransition, transition(frm, to), match="not allowed")


def test_proposed_check_only_on_check_proposed() -> None:
    rejects(FindingTransition, transition("hypothesis", "check_proposed", proposed_check=None),
            match="proposed check")
    rejects(FindingTransition, transition("check_proposed", "confirmed", proposed_check=EXISTING),
            match="proposed check")


@pytest.mark.parametrize("to", ["confirmed", "refuted"])
def test_decisions_need_observation_citations(to: str) -> None:
    rejects(FindingTransition, transition("check_proposed", to, deciding_citations=[]),
            match="deciding")


def test_non_decisions_carry_no_deciding_citations() -> None:
    rejects(FindingTransition, transition("hypothesis", "dropped", deciding_citations=[CITATION]),
            match="deciding")
    rejects(FindingTransition,
            transition("hypothesis", "check_proposed", deciding_citations=[CITATION]),
            match="deciding")


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"drop_reason": None}, "drop_reason"),
        ({"drop_reason": "superseded"}, "superseded_by"),
        ({"drop_reason": "duplicate", "superseded_by": "F43"}, "superseded_by"),
        ({"drop_reason": "superseded", "superseded_by": "F42"}, "superseded by itself"),
        ({"drop_reason": "stale"}, None),
    ],
)
def test_drop_rules(changes: dict[str, Any], match: str | None) -> None:
    rejects(FindingTransition, transition("check_proposed", "dropped", **changes), match=match)


def test_drop_reason_only_on_drops() -> None:
    rejects(FindingTransition,
            transition("check_proposed", "confirmed", drop_reason="duplicate"), match="drop_reason")


@pytest.mark.parametrize(
    "proposal",
    [
        {**EXISTING, "check_id": None},
        {"proposal_kind": "development_probe", "action": "run_sim", "configuration_id": "cfg_a",
         "test_ids": [], "property_ids": [], "rationale": "r"},  # no targets
        {"proposal_kind": "development_probe", "action": "inspect_waveform",
         "configuration_id": "cfg_a", "test_ids": ["t_a"], "property_ids": [], "rationale": "r"},
        {"proposal_kind": "development_probe", "action": "run_sim", "configuration_id": "cfg_a",
         "test_ids": ["t_a", "t_a"], "property_ids": [], "rationale": "r"},
        {"proposal_kind": "new_policy_section", "check_id": "chk_x"},
    ],
)
def test_bad_proposals_rejected(proposal: dict[str, Any]) -> None:
    rejects(FindingTransition, transition("hypothesis", "check_proposed", proposed_check=proposal))


@pytest.mark.parametrize(
    "changes",
    [
        {"sequence": 1, "previous_transition_hash": H("7a")},
        {"sequence": 2, "previous_transition_hash": None},
        {"sequence": 0, "previous_transition_hash": None},
    ],
)
def test_chain_head_rules(changes: dict[str, Any]) -> None:
    rejects(FindingTransition, transition("check_proposed", "confirmed", **changes))


def test_first_transition_starts_from_hypothesis() -> None:
    rejects(FindingTransition, transition("check_proposed", "confirmed", sequence=1,
                                          previous_transition_hash=None), match="first transition")


def test_floats_rejected() -> None:
    rejects(FindingTransition, {**CONFIRMED, "sequence": 2.0}, match="binary floats")


def test_transition_is_immutable() -> None:
    t = FindingTransition.model_validate(CONFIRMED)
    with pytest.raises(ValidationError):
        t.to_status = FindingStatus.REFUTED  # type: ignore[misc]
