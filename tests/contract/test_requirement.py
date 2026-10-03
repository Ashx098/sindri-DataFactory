"""Contract tests for Requirement (SIN-P1.1-002 acceptance criteria)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.schemas import Requirement, RequirementDisposition

EXAMPLE = json.loads((Path(__file__).parent / "examples/requirement.json").read_text())
SHA = "sha256:" + "cd" * 32


def requirement(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    return data


def rejects(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Requirement.model_validate(data)


def scope(*parameters: tuple[str, list[Any]]) -> dict[str, Any]:
    return {
        "kind": "parameter_scope",
        "parameters": [{"name": n, "values": v} for n, v in parameters],
    }


# ---- positive ---------------------------------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    r = Requirement.model_validate(EXAMPLE)
    assert Requirement.model_validate_json(r.model_dump_json()) == r
    assert json.loads(r.model_dump_json()) == EXAMPLE


def test_all_supported_configs_and_empty_environment_validate() -> None:
    r = Requirement.model_validate(
        requirement(
            applicability={"kind": "all_supported_configs"},
            legal_environment=[],
            assumptions=[],
        )
    )
    assert r.applicability.kind == "all_supported_configs"


@pytest.mark.parametrize("disposition", list(RequirementDisposition))
def test_every_disposition_is_representable(disposition: RequirementDisposition) -> None:
    r = Requirement.model_validate(requirement(disposition=disposition.value))
    assert r.disposition is disposition


def test_original_text_kept_verbatim_and_separate() -> None:
    text = "  Data MUST remain stable while stalled.\n"
    r = Requirement.model_validate(requirement(original_text=text))
    assert r.original_text == text
    assert r.normalized_semantics == EXAMPLE["normalized_semantics"]


def test_later_version_with_supersedes_validates() -> None:
    r = Requirement.model_validate(
        requirement(requirement_version=2, supersedes=SHA, disposition="ambiguous")
    )
    assert (r.requirement_id, r.requirement_version) == ("R17", 2)


def test_content_id_changes_with_meaning_or_disposition() -> None:
    base = Requirement.model_validate(EXAMPLE).content_id()
    others = {
        Requirement.model_validate(requirement(**c)).content_id()
        for c in (
            {"disposition": "ambiguous"},
            {"normalized_semantics": "out_data may change while stalled"},
            {"mandatory": False},
        )
    }
    assert base not in others and len(others) == 3


# ---- negative: required fields, closed record, ADR-0004 ---------------------------------------


@pytest.mark.parametrize(
    "field", sorted(k for k in EXAMPLE if k not in ("legal_environment", "assumptions"))
)
def test_every_field_is_required(field: str) -> None:
    data = requirement()
    del data[field]
    rejects(data)


def test_obligation_ids_are_not_a_requirement_field() -> None:
    rejects(requirement(obligation_ids=["sim_stall_01"]))  # ADR-0004


def test_unknown_nested_fields_rejected() -> None:
    rejects(requirement(assumptions=[{"text": "t", "source_ref": "s", "confidence": "high"}]))
    rejects(requirement(applicability={"kind": "all_supported_configs", "extra": 1}))


@pytest.mark.parametrize("mandatory", ["yes", 1, None])
def test_mandatory_is_a_strict_boolean_without_default(mandatory: Any) -> None:
    rejects(requirement(mandatory=mandatory))


@pytest.mark.parametrize(
    ("version", "supersedes"), [(2, None), (1, SHA), (0, None)]
)
def test_version_chain_is_enforced(version: int, supersedes: str | None) -> None:
    rejects(requirement(requirement_version=version, supersedes=supersedes))


@pytest.mark.parametrize("field", ["original_text", "normalized_semantics", "source_ref"])
@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_texts_must_be_non_blank(field: str, value: str) -> None:
    rejects(requirement(**{field: value}))


@pytest.mark.parametrize("field", ["assumptions", "legal_environment"])
def test_rules_and_assumptions_need_a_source(field: str) -> None:
    rejects(requirement(**{field: [{"text": "reset first"}]}))
    rejects(requirement(**{field: [{"text": "reset first", "source_ref": ""}]}))


@pytest.mark.parametrize(
    ("field", "value"),
    [("disposition", "accepted"), ("disposition", "Approved"), ("requirement_id", "17")],
)
def test_unknown_or_malformed_values_rejected(field: str, value: str) -> None:
    rejects(requirement(**{field: value}))


# ---- negative: applicability (C4, C6, D5) -----------------------------------------------------


@pytest.mark.parametrize(
    "applicability",
    [
        scope(("DEPTH", [])),
        scope(("DEPTH", [8]), ("DEPTH", [16])),
        scope(("depth", [8])),
        scope(("1DEPTH", [8])),
        scope(("DEPTH", [8, 8])),
        scope(("DEPTH", [None])),
        scope(("DEPTH", [{"nested": 1}])),
        scope(("DEPTH", [[8]])),
        {"kind": "parameter_scope", "parameters": []},
        {"kind": "parameter_scope", "parameters": {"DEPTH": [8]}},
        {"kind": "some_configs"},
    ],
)
def test_bad_parameter_scopes_rejected(applicability: dict[str, Any]) -> None:
    rejects(requirement(applicability=applicability))


def test_parameter_values_are_never_coerced() -> None:
    r = Requirement.model_validate(requirement(applicability=scope(("MODE", ["8", 8, True]))))
    assert r.applicability.kind == "parameter_scope"
    values = r.applicability.parameters[0].values
    assert [type(v) for v in values] == [str, int, bool]
    # True == 1 in Python, but they are different parameter values and both are kept.
    r2 = Requirement.model_validate(requirement(applicability=scope(("MODE", [True, 1]))))
    assert r2.applicability.kind == "parameter_scope"
    assert [type(v) for v in r2.applicability.parameters[0].values] == [bool, int]


def test_parameter_values_survive_json_round_trip_with_types() -> None:
    r = Requirement.model_validate(requirement(applicability=scope(("MODE", ["8", 8, True]))))
    again = Requirement.model_validate_json(r.model_dump_json())
    assert again.applicability.kind == "parameter_scope"
    assert [type(v) for v in again.applicability.parameters[0].values] == [str, int, bool]


@pytest.mark.parametrize(
    "changes",
    [
        {"applicability": scope(("WIDTH", [8, 0.5]))},
        {"requirement_version": 1.0},
        {"mandatory": 1.0},
    ],
)
def test_binary_floats_rejected_at_any_depth(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="binary floats"):
        Requirement.model_validate(requirement(**changes))


def test_records_are_immutable() -> None:
    r = Requirement.model_validate(EXAMPLE)
    with pytest.raises(ValidationError):
        r.disposition = RequirementDisposition.REJECTED  # type: ignore[assignment]
    assert isinstance(r.assumptions, tuple)
