"""Contract tests for EvaluationPolicy (SIN-P1.1-003 acceptance criteria, decisions E1–E9)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.schemas import CheckKind, EvaluationPolicy

EXAMPLE = json.loads((Path(__file__).parent / "examples/evaluation_policy.json").read_text())
SHA = "sha256:" + "ef" * 32
ALL_CFGS = ["cfg_w1_d1", "cfg_w8_d3", "cfg_w8_d8", "cfg_w32_d8"]


def policy(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    return data


def check(check_id: str, kind: str = "directed_sim", **changes: Any) -> dict[str, Any]:
    base = {
        "check_id": check_id,
        "kind": kind,
        "mandatory": True,
        "visibility": "hidden",
        "tool_profile_id": "tp_verilator_v0",
        "configuration_ids": ["cfg_w8_d8"],
        "formal_mode": None,
        "depth": None,
    }
    base.update(changes)
    return base


def with_check(new: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return policy(checks=[*EXAMPLE["checks"], new], **changes)


def with_check_changed(check_id: str, **changes: Any) -> dict[str, Any]:
    checks = [dict(c, **changes) if c["check_id"] == check_id else c for c in EXAMPLE["checks"]]
    return policy(checks=checks)


def rejects(data: dict[str, Any], match: str | None = None) -> None:
    with pytest.raises(ValidationError, match=match):
        EvaluationPolicy.model_validate(data)


# ---- positive ---------------------------------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    p = EvaluationPolicy.model_validate(EXAMPLE)
    assert EvaluationPolicy.model_validate_json(p.model_dump_json()) == p
    assert json.loads(p.model_dump_json()) == EXAMPLE


def test_example_covers_the_positive_shapes() -> None:
    p = EvaluationPolicy.model_validate(EXAMPLE)
    assert {c.visibility.value for c in p.checks} == {"development", "hidden"}
    by_req: dict[str, int] = {}
    for ob in p.obligations:
        by_req[ob.requirement_id] = by_req.get(ob.requirement_id, 0) + 1
    assert by_req["R01"] == 2  # one requirement, several obligations
    assert any(len(ob.check_ids) > 1 for ob in p.obligations)  # one obligation, several checks
    assert p.exceptions[0].excludes[0].configuration_id == "cfg_w32_d8"  # narrow exclusion


def test_prove_check_without_depth_validates() -> None:
    p = EvaluationPolicy.model_validate(
        with_check(check("chk_prove", "formal", formal_mode="prove", tool_profile_id="tp_sby_v0"))
    )
    assert p.checks[-1].depth is None


def test_later_version_with_supersedes_validates() -> None:
    assert EvaluationPolicy.model_validate(policy(policy_version=2, supersedes=SHA)).policy_version


# ---- negative: required, closed, vocabulary (E3, E4) ------------------------------------------


@pytest.mark.parametrize("field", sorted(EXAMPLE))
def test_every_field_is_required(field: str) -> None:
    data = policy()
    del data[field]
    rejects(data)


@pytest.mark.parametrize("field", sorted(EXAMPLE["checks"][0]))
def test_every_check_field_is_required(field: str) -> None:
    broken = dict(EXAMPLE["checks"][0])
    del broken[field]
    rejects(policy(checks=[broken, *EXAMPLE["checks"][1:]]))


@pytest.mark.parametrize(
    "path",
    [(), ("checks", 0), ("configurations", 0), ("obligations", 0), ("exceptions", 0)],
    ids=["top", "check", "configuration", "obligation", "exception"],
)
def test_unknown_fields_rejected_at_every_level(path: tuple[Any, ...]) -> None:
    data = policy()
    target: Any = data
    for key in path:
        target = target[key]
    target["waiver"] = "yes"
    rejects(data)


@pytest.mark.parametrize("kind", ["mutation_qualification", "clean_replay", "cover", "Formal"])
def test_non_candidate_check_kinds_rejected(kind: str) -> None:
    rejects(with_check(check("chk_x", kind)))


def test_check_kind_vocabulary_is_exactly_e3() -> None:
    assert {k.value for k in CheckKind} == {
        "integrity_scan", "parse_elaborate", "lint", "synthesis", "directed_sim",
        "random_sim", "formal", "equivalence", "quality",
    }


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"formal_mode": "cover", "depth": None}, None),  # E4: covers never satisfy obligations
        ({"formal_mode": "bmc", "depth": None}, "bmc needs a depth"),
        ({"formal_mode": "prove", "depth": 10}, "bmc needs a depth"),
        ({"formal_mode": "bmc", "depth": 0}, None),
        ({"formal_mode": None, "depth": None}, "formal checks need formal_mode"),
    ],
)
def test_formal_mode_rules(changes: dict[str, Any], match: str | None) -> None:
    rejects(with_check_changed("chk_formal_core", **changes), match=match)


@pytest.mark.parametrize("changes", [{"formal_mode": "bmc", "depth": 10}, {"depth": 10}])
def test_formal_fields_only_on_formal_checks(changes: dict[str, Any]) -> None:
    rejects(with_check_changed("chk_directed", **changes), match="only formal checks")


# ---- negative: configurations (E5) ------------------------------------------------------------


@pytest.mark.parametrize("ref", [0, 2, "cfg_unknown"])
def test_checks_reference_configurations_by_existing_id_only(ref: Any) -> None:
    rejects(with_check_changed("chk_directed", configuration_ids=[ref]))


def test_duplicate_configuration_ids_rejected() -> None:
    cfgs = [*EXAMPLE["configurations"], dict(EXAMPLE["configurations"][0])]
    rejects(policy(configurations=cfgs), match="configuration_ids contains duplicates")


def test_same_assignment_set_under_two_ids_rejected() -> None:
    clone = {
        "configuration_id": "cfg_w8_d8_again",
        "assignments": list(reversed(EXAMPLE["configurations"][2]["assignments"])),
    }
    rejects(policy(configurations=[*EXAMPLE["configurations"], clone]), match="assignments")


def no_parameter_policy(*configs: str) -> dict[str, Any]:
    first = configs[0]
    return policy(
        configurations=[{"configuration_id": c, "assignments": []} for c in configs],
        checks=[check("chk_sim", configuration_ids=[first])],
        obligations=[{"obligation_id": "sim_basic", "requirement_id": "R01",
                      "check_ids": ["chk_sim"]}],
        exceptions=[],
    )


def test_zero_parameter_design_has_one_explicit_default_configuration() -> None:
    p = EvaluationPolicy.model_validate(no_parameter_policy("cfg_default"))
    assert p.configurations[0].assignments == ()
    assert p.checks[0].configuration_ids == ("cfg_default",)


def test_two_empty_configurations_are_the_same_assignment_set() -> None:
    rejects(no_parameter_policy("cfg_default", "cfg_other"), match="assignments")


def test_policy_still_needs_at_least_one_configuration() -> None:
    rejects(policy(configurations=[]))


def test_duplicate_parameter_in_one_configuration_rejected() -> None:
    bad = {
        "configuration_id": "cfg_bad",
        "assignments": [{"name": "WIDTH", "value": 8}, {"name": "WIDTH", "value": 16}],
    }
    rejects(policy(configurations=[*EXAMPLE["configurations"], bad]))


def test_true_and_one_are_different_configurations() -> None:
    a = {"configuration_id": "cfg_mode_bool", "assignments": [{"name": "MODE", "value": True}]}
    b = {"configuration_id": "cfg_mode_int", "assignments": [{"name": "MODE", "value": 1}]}
    p = EvaluationPolicy.model_validate(policy(configurations=[*EXAMPLE["configurations"], a, b]))
    assert [type(c.assignments[0].value) for c in p.configurations[-2:]] == [bool, int]


@pytest.mark.parametrize("value", [8.0, None, [8], {"v": 8}])
def test_configuration_values_are_exact_scalars(value: Any) -> None:
    bad = {"configuration_id": "cfg_bad", "assignments": [{"name": "WIDTH", "value": value}]}
    rejects(policy(configurations=[*EXAMPLE["configurations"], bad]))


# ---- negative: checks, obligations (E6, E8) ---------------------------------------------------


def test_duplicate_check_ids_rejected() -> None:
    rejects(with_check(dict(EXAMPLE["checks"][0])), match="check_ids contains duplicates")


def test_mandatory_quality_check_rejected() -> None:
    rejects(with_check_changed("chk_area", mandatory=True), match="never be mandatory")


def test_policy_needs_a_mandatory_check() -> None:
    checks = [dict(c, mandatory=False) for c in EXAMPLE["checks"]]
    rejects(policy(checks=checks), match="at least one mandatory")


@pytest.mark.parametrize(
    ("ob_changes", "match"),
    [
        ({"check_ids": []}, None),
        ({"check_ids": ["chk_missing"]}, "unknown checks"),
        ({"check_ids": ["chk_directed", "chk_directed"]}, "duplicates"),
        ({"check_ids": ["chk_area"]}, "non-quality check"),  # E8
        ({"requirement_id": "r01"}, None),
    ],
)
def test_bad_obligations_rejected(ob_changes: dict[str, Any], match: str | None) -> None:
    obligations = [dict(EXAMPLE["obligations"][0], **ob_changes), *EXAMPLE["obligations"][1:]]
    rejects(policy(obligations=obligations), match=match)


def test_duplicate_obligation_ids_rejected() -> None:
    obs = [*EXAMPLE["obligations"], dict(EXAMPLE["obligations"][0])]
    rejects(policy(obligations=obs), match="obligation_ids contains duplicates")


def test_policy_needs_obligations() -> None:
    rejects(policy(obligations=[]))


# ---- negative: exceptions (E7, E9) ------------------------------------------------------------


def exception(*pairs: tuple[str, str], exception_id: str = "ex_extra") -> dict[str, Any]:
    return {
        "exception_id": exception_id,
        "excludes": [{"check_id": c, "configuration_id": g} for c, g in pairs],
        "justification": "state space",
        "approved_by": "Avinash",
    }


@pytest.mark.parametrize(
    ("exc", "match"),
    [
        (exception(("chk_missing", "cfg_w8_d8")), "unknown check"),
        (exception(("chk_directed", "cfg_w1_d1")), "never targets"),
        (exception(("chk_formal_core", "cfg_w32_d8")), "pairs contains duplicates"),
        (exception(), None),
    ],
)
def test_bad_exceptions_rejected(exc: dict[str, Any], match: str | None) -> None:
    rejects(policy(exceptions=[*EXAMPLE["exceptions"], exc]), match=match)


def test_exception_needs_justification_and_approver() -> None:
    for field in ("justification", "approved_by"):
        exc = dict(exception(("chk_random", "cfg_w1_d1")), **{field: "  "})
        rejects(policy(exceptions=[exc]))


def test_exceptions_may_not_remove_a_mandatory_check_entirely() -> None:
    # E9: excluding the remaining formal configurations would silently delete the check.
    exc = exception(("chk_formal_core", "cfg_w1_d1"), ("chk_formal_core", "cfg_w8_d3"))
    rejects(policy(exceptions=[*EXAMPLE["exceptions"], exc]), match="every configuration")


def test_exceptions_may_fully_exclude_an_optional_check() -> None:
    exc = exception(("chk_area", "cfg_w8_d8"))
    p = EvaluationPolicy.model_validate(policy(exceptions=[*EXAMPLE["exceptions"], exc]))
    assert len(p.exceptions) == 2


def test_duplicate_exception_ids_rejected() -> None:
    exc = exception(("chk_random", "cfg_w1_d1"), exception_id="ex_formal_w32")
    rejects(policy(exceptions=[*EXAMPLE["exceptions"], exc]), match="exception_ids")


# ---- negative: misc -------------------------------------------------------------------------


def test_assumption_needs_a_source() -> None:
    rejects(policy(environment_assumptions=[{"text": "reset first", "source_ref": ""}]))
    rejects(policy(environment_assumptions=[{"text": "reset first"}]))


@pytest.mark.parametrize(("version", "supersedes"), [(2, None), (1, SHA)])
def test_version_chain_is_enforced(version: int, supersedes: str | None) -> None:
    rejects(policy(policy_version=version, supersedes=supersedes))


@pytest.mark.parametrize("depth", [24.0, True, "24"])
def test_depth_is_a_strict_integer(depth: Any) -> None:
    rejects(with_check_changed("chk_formal_core", depth=depth))


@pytest.mark.parametrize("value", [1, "true"])
def test_mandatory_is_a_strict_boolean(value: Any) -> None:
    rejects(with_check_changed("chk_directed", mandatory=value))


def test_floats_rejected_with_the_records_message() -> None:
    rejects(with_check_changed("chk_formal_core", depth=24.0), match="binary floats")


def test_records_are_immutable() -> None:
    p = EvaluationPolicy.model_validate(EXAMPLE)
    with pytest.raises(ValidationError):
        p.checks[0].mandatory = False  # type: ignore[misc]
    assert isinstance(p.checks, tuple) and isinstance(p.configurations[0].assignments, tuple)


def test_all_configurations_listed_in_example() -> None:
    assert [c["configuration_id"] for c in EXAMPLE["configurations"]] == ALL_CFGS
