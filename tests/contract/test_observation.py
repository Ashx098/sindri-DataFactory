"""Contract tests for Observation (SIN-P1.1-005; decisions O1–O15, R1–R5; ADR-0002, ADR-0005)."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.schemas import (
    ACTION_FOR_KIND,
    Observation,
    ObservationAction,
    observation_execution_key,
)
from sindri.schemas.policy import CheckKind, FormalMode

EXAMPLE = json.loads((Path(__file__).parent / "examples/observation.json").read_text())


def H(byte: str) -> str:
    return "sha256:" + byte * 32


KEY_FIELDS = (
    "candidate_manifest_hash", "source_hash", "dependency_hash", "policy_hash", "check_id",
    "configuration_id", "action", "tool_profile_hash", "tool_image_digest", "adapter_hash",
    "evaluator_bundle_hash", "seed", "formal_mode", "formal_depth", "wall_time_limit_ms",
)


def rekey(data: dict[str, Any]) -> dict[str, Any]:
    """Recompute execution_key from the request fields of `data`."""
    args = {f: data[f] for f in KEY_FIELDS}
    try:
        args["action"] = ObservationAction(args["action"])
        mode = args["formal_mode"]
        args["formal_mode"] = None if mode is None else FormalMode(mode)
    except ValueError:
        return data  # an invalid enum: the record is rejected on that field anyway
    data["execution_key"] = observation_execution_key(**args)
    return data


def diag(category: str = "candidate", severity: str = "error", code: str | None = None,
         message: str = "something happened") -> dict[str, Any]:
    return {"severity": severity, "category": category, "code": code, "message": message,
            "path": None, "line": None}


def sim_report(expected: list[str], results: list[tuple[str, str]]) -> dict[str, Any]:
    return {"report_kind": "simulation", "expected_test_ids": expected,
            "test_results": [{"test_id": t, "outcome": o} for t, o in results]}


def formal_report(results: list[tuple[str, str]], expected: list[str] | None = None,
                  mode: str = "bmc", requested: int | None = 40, reached: int | None = 40,
                  closed: bool | None = None) -> dict[str, Any]:
    return {"report_kind": "formal", "mode": mode, "requested_depth": requested,
            "reached_depth": reached, "proof_closed": closed,
            "expected_property_ids": expected or ["R03_sva", "R17_sva"],
            "property_results": [{"property_id": p, "outcome": o} for p, o in results]}


def structural(errors: int = 0, latches: int | None = None, blackboxes: int | None = None
               ) -> dict[str, Any]:
    return {"report_kind": "structural", "error_count": errors, "warning_count": 0,
            "latch_count": latches, "blackbox_count": blackboxes}


def obs(kind: str = "formal", status: str = "FAIL", **changes: Any) -> dict[str, Any]:
    """A valid-by-default Observation for `kind`, with the execution key recomputed."""
    data = copy.deepcopy(EXAMPLE)
    data.update(check_kind=kind, action=ACTION_FOR_KIND[CheckKind(kind)].value, status=status)
    if (kind, status) != ("formal", "FAIL"):  # otherwise keep the example's valid FAIL evidence
        data.update(diagnostics=[], evidence_refs=[], execution_report=None)
    if kind != "formal":
        data.update(formal_mode=None, formal_depth=None)
    data["seed"] = 7 if kind in ("directed_sim", "random_sim") else None
    data.update(changes)
    return rekey(data)


def rejects(data: dict[str, Any], match: str | None = None) -> None:
    with pytest.raises(ValidationError, match=match):
        Observation.model_validate(data)


def accepts(data: dict[str, Any]) -> Observation:
    return Observation.model_validate(data)


SIM_PASS = sim_report(["t_a", "t_b"], [("t_a", "PASS"), ("t_b", "PASS")])
CEX = [{"kind": "counterexample_trace", "hash": H("8e")}]


# ---- the example and the execution key ---------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    o = accepts(EXAMPLE)
    assert Observation.model_validate_json(o.model_dump_json()) == o
    assert json.loads(o.model_dump_json()) == EXAMPLE
    assert o.status == "FAIL"  # a partial report: R17_sva never checked, depth 23 of 40 (R3)


def test_execution_key_matches_independent_byte_level_vector() -> None:
    """Pins the construction without going through canonical_json_id."""
    raw = (
        '{"action":"run_formal",'
        '"adapter_hash":"' + H("ad") + '",'
        '"candidate_manifest_hash":"' + H("c1") + '",'
        '"check_id":"chk_formal_core",'
        '"configuration_id":"cfg_w8_d8",'
        '"dependency_hash":"' + H("d0") + '",'
        '"evaluator_bundle_hash":"' + H("eb") + '",'
        '"formal_depth":40,'
        '"formal_mode":"bmc",'
        '"kind":"observation_execution_key_v1",'
        '"policy_hash":"' + H("b9") + '",'
        '"seed":null,'
        '"source_hash":"' + H("7e") + '",'
        '"tool_image_digest":"' + H("0f") + '",'
        '"tool_profile_hash":"' + H("a4") + '",'
        '"wall_time_limit_ms":600000}'
    ).encode()
    assert EXAMPLE["execution_key"] == "sha256:" + hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_manifest_hash", H("c2")),
        ("source_hash", H("7f")),
        ("dependency_hash", None),
        ("policy_hash", H("ba")),
        ("check_id", "chk_formal_other"),
        ("configuration_id", "cfg_w8_d3"),
        ("tool_profile_hash", H("a5")),
        ("tool_image_digest", H("10")),
        ("adapter_hash", H("ae")),
        ("evaluator_bundle_hash", H("ec")),
        ("formal_depth", 41),
        ("wall_time_limit_ms", 600001),
    ],
)
def test_every_request_input_changes_the_key(field: str, value: Any) -> None:
    changed = accepts(obs(**{field: value}) if field != "formal_depth" else obs(
        formal_depth=value, execution_report=formal_report(
            [("R03_sva", "FAIL")], requested=value, reached=23), evidence_refs=CEX))
    assert changed.execution_key != EXAMPLE["execution_key"]


def test_formal_mode_changes_the_key() -> None:
    prove = accepts(obs(formal_mode="prove", formal_depth=None, evidence_refs=CEX,
                        execution_report=formal_report([("R03_sva", "FAIL")], mode="prove",
                                                       requested=None, reached=None,
                                                       closed=False)))
    assert prove.execution_key != EXAMPLE["execution_key"]


def test_random_runs_differing_only_in_seed_have_different_keys() -> None:
    a = accepts(obs("random_sim", "PASS", seed=17, execution_report=SIM_PASS))
    b = accepts(obs("random_sim", "PASS", seed=44, execution_report=SIM_PASS))
    assert a.execution_key != b.execution_key


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observation_id", "ob_99999"),
        ("candidate_id", "c_other_v1"),
        ("policy_id", "ep_other_001"),
        ("tool_profile_id", "tp_other_v0"),
        ("adapter_version", "sby-adapter 0.2.0"),
        ("started_at", "2026-10-05T00:00:00Z"),
        ("duration_ms", 1),
        ("summary", "different words"),
        ("log_ref", H("20")),
        ("visibility", "development"),
    ],
)
def test_result_and_handle_fields_do_not_change_the_key(field: str, value: Any) -> None:
    data = copy.deepcopy(EXAMPLE)
    data[field] = value
    assert accepts(data).execution_key == EXAMPLE["execution_key"]


@pytest.mark.parametrize(
    "wrong",
    [
        H("00"),
        "tag",  # recompute without the domain tag
        "candidate_manifest_hash",  # tampered input below
        "adapter_hash",
    ],
)
def test_stored_key_must_match_recomputation(wrong: str) -> None:
    from sindri.core.ids import canonical_json_id

    data = copy.deepcopy(EXAMPLE)
    if wrong == "tag":
        args = {f: data[f] for f in KEY_FIELDS}
        data["execution_key"] = canonical_json_id(args)
    elif wrong in ("candidate_manifest_hash", "adapter_hash"):
        data[wrong] = H("99")  # input changed, stored key not recomputed
    else:
        data["execution_key"] = wrong
    rejects(data, match="execution_key")


# ---- required, closed, kinds, request shape -----------------------------------------------------


@pytest.mark.parametrize("field", sorted(EXAMPLE))
def test_every_field_is_required(field: str) -> None:
    data = copy.deepcopy(EXAMPLE)
    del data[field]
    rejects(data)


@pytest.mark.parametrize("field", ["producer", "seeds", "duration_s", "tool", "executed",
                                   "supersedes", "observation_version"])
def test_unknown_or_rejected_design_fields(field: str) -> None:
    rejects({**EXAMPLE, field: "x"})


def test_quality_is_not_an_observation_kind() -> None:
    data = obs("synthesis", "PASS", execution_report=structural(latches=0, blackboxes=0))
    data["check_kind"] = "quality"
    rejects(rekey(data), match="quality")


@pytest.mark.parametrize(("kind", "action"), [("formal", "run_sim"), ("lint", "compile"),
                                               ("parse_elaborate", "lint"), ("synthesis", "lint")])
def test_action_must_match_kind(kind: str, action: str) -> None:
    rejects(obs(kind, "TOOL_ERROR", action=action, diagnostics=[diag("infrastructure")]))


def test_action_map_is_closed_and_one_to_one_per_kind() -> None:
    assert CheckKind.QUALITY not in ACTION_FOR_KIND
    assert set(ACTION_FOR_KIND) == set(CheckKind) - {CheckKind.QUALITY}


@pytest.mark.parametrize(("kind", "report"), [("lint", SIM_PASS), ("directed_sim", structural()),
                                               ("equivalence", structural())])
def test_report_variant_must_match_kind(kind: str, report: dict[str, Any]) -> None:
    rejects(obs(kind, "PASS", execution_report=report), match="report")


@pytest.mark.parametrize(
    ("kind", "seed"),
    [("directed_sim", None), ("random_sim", None), ("lint", 7), ("formal", 7)],
)
def test_seed_rule(kind: str, seed: Any) -> None:
    rejects(obs(kind, "TOOL_ERROR", seed=seed, diagnostics=[diag("infrastructure")]),
            match="seed")


@pytest.mark.parametrize("value", [None])
def test_evaluator_bundle_hash_is_always_required(value: Any) -> None:
    rejects(obs("lint", "PASS", evaluator_bundle_hash=value, execution_report=structural()))


@pytest.mark.parametrize("limit", [0, -1, 1.0, "600000", True])
def test_wall_time_limit_is_a_positive_strict_int(limit: Any) -> None:
    data = copy.deepcopy(EXAMPLE)
    data["wall_time_limit_ms"] = limit
    rejects(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"formal_mode": None, "formal_depth": None},
        {"formal_mode": "bmc", "formal_depth": None},
        {"formal_mode": "prove", "formal_depth": 40},
        {"formal_mode": "cover", "formal_depth": 40},
    ],
)
def test_formal_request_rules(changes: dict[str, Any]) -> None:
    rejects(obs(**changes, evidence_refs=CEX))


def test_formal_fields_only_on_formal() -> None:
    rejects(obs("lint", "PASS", formal_mode="bmc", formal_depth=10, execution_report=structural()))


def test_report_must_echo_the_requested_formal_depth() -> None:
    rejects(obs(evidence_refs=CEX, execution_report=formal_report(
        [("R03_sva", "FAIL")], requested=39, reached=23)), match="requested depth")


# ---- PASS ---------------------------------------------------------------------------------------


def test_sim_pass_with_every_expected_test_passed() -> None:
    assert accepts(obs("directed_sim", "PASS", execution_report=SIM_PASS)).status == "PASS"


@pytest.mark.parametrize(
    "results",
    [
        [("t_a", "PASS")],  # t_b silently missing
        [("t_a", "PASS"), ("t_b", "FAIL")],
        [("t_a", "PASS"), ("t_b", "TIMEOUT")],
    ],
)
def test_sim_pass_needs_complete_all_pass_results(results: list[tuple[str, str]]) -> None:
    rejects(obs("random_sim", "PASS", execution_report=sim_report(["t_a", "t_b"], results)))


@pytest.mark.parametrize(
    "results",
    [
        [("t_a", "PASS"), ("t_b", "PASS"), ("t_c", "PASS")],  # extra test
        [("t_a", "PASS"), ("t_a", "PASS"), ("t_b", "PASS")],  # duplicated test
    ],
)
def test_results_outside_or_duplicating_the_inventory_rejected(
    results: list[tuple[str, str]],
) -> None:
    rejects(obs("random_sim", "PASS", execution_report=sim_report(["t_a", "t_b"], results)))


def test_formal_pass_bmc_and_prove() -> None:
    bmc = formal_report([("R03_sva", "PASS"), ("R17_sva", "PASS")])
    assert accepts(obs(status="PASS", execution_report=bmc)).status == "PASS"
    prove = formal_report([("R03_sva", "PASS"), ("R17_sva", "PASS")], mode="prove",
                          requested=None, reached=None, closed=True)
    assert accepts(obs(status="PASS", formal_mode="prove", formal_depth=None,
                       execution_report=prove)).status == "PASS"


@pytest.mark.parametrize(
    "report",
    [
        formal_report([("R03_sva", "PASS")]),  # R17_sva never checked
        formal_report([("R03_sva", "PASS"), ("R17_sva", "PASS")], reached=39),  # bound unmet
        formal_report([("R03_sva", "PASS"), ("R17_sva", "INCONCLUSIVE")]),
    ],
)
def test_formal_pass_needs_all_properties_and_the_bound(report: dict[str, Any]) -> None:
    rejects(obs(status="PASS", execution_report=report))


def test_prove_pass_needs_a_closed_proof() -> None:
    report = formal_report([("R03_sva", "PASS"), ("R17_sva", "PASS")], mode="prove",
                           requested=None, reached=None, closed=False)
    rejects(obs(status="PASS", formal_mode="prove", formal_depth=None, execution_report=report))


def test_pass_needs_a_report() -> None:
    rejects(obs("lint", "PASS"), match="complete execution report")


@pytest.mark.parametrize(
    "changes",
    [
        {"diagnostics": [diag("candidate", "error")]},
        {"diagnostics": [diag("infrastructure", "error")]},
        {"evidence_refs": CEX},
    ],
)
def test_pass_cannot_carry_errors_or_counterexamples(changes: dict[str, Any]) -> None:
    rejects(obs("directed_sim", "PASS", execution_report=SIM_PASS, **changes))


def test_pass_may_carry_warnings() -> None:
    o = accepts(obs("lint", "PASS", execution_report=structural(),
                    diagnostics=[diag("candidate", "warning")]))
    assert o.diagnostics[0].severity == "warning"


def test_structural_and_equivalence_pass() -> None:
    accepts(obs("synthesis", "PASS", execution_report=structural(latches=0, blackboxes=0)))
    accepts(obs("equivalence", "PASS", execution_report={"report_kind": "equivalence",
                                                         "proved": True}))
    rejects(obs("lint", "PASS", execution_report=structural(errors=1)))
    rejects(obs("equivalence", "PASS", execution_report={"report_kind": "equivalence",
                                                         "proved": False}))


@pytest.mark.parametrize(("kind", "latches", "blackboxes"),
                         [("synthesis", None, None), ("synthesis", 0, None), ("lint", 0, 0)])
def test_latch_counts_only_for_synthesis(kind: str, latches: Any, blackboxes: Any) -> None:
    rejects(obs(kind, "PASS", execution_report=structural(latches=latches, blackboxes=blackboxes)))


# ---- FAIL ---------------------------------------------------------------------------------------


def test_sim_fail_with_partial_report_is_valid() -> None:
    """R3: test_2 fails, the runner aborts, tests 3-20 never run: still a valid FAIL."""
    expected = [f"t_{i:02d}" for i in range(1, 21)]
    report = sim_report(expected, [("t_01", "PASS"), ("t_02", "FAIL")])
    assert accepts(obs("directed_sim", "FAIL", execution_report=report)).status == "FAIL"


def test_fail_needs_a_report() -> None:
    rejects(obs("lint", "FAIL", diagnostics=[diag("candidate")]), match="report")


@pytest.mark.parametrize(
    ("kind", "changes"),
    [
        ("directed_sim", {"execution_report": sim_report(["t_a"], [("t_a", "PASS")])}),
        ("directed_sim", {"execution_report": sim_report(["t_a", "t_b"], [("t_a", "PASS")])}),
        ("formal", {"evidence_refs": [],  # failing property but no counterexample
                    "execution_report": formal_report([("R03_sva", "FAIL")], reached=23)}),
        ("formal", {"evidence_refs": CEX,
                    "execution_report": formal_report([("R03_sva", "PASS")], reached=23)}),
        ("equivalence", {"execution_report": {"report_kind": "equivalence", "proved": False}}),
        ("equivalence", {"evidence_refs": CEX,
                         "execution_report": {"report_kind": "equivalence", "proved": True}}),
        ("lint", {"execution_report": structural(errors=1)}),
        ("lint", {"execution_report": structural(errors=1),
                  "diagnostics": [diag("infrastructure")]}),
        ("lint", {"execution_report": structural(errors=0), "diagnostics": [diag("candidate")]}),
    ],
)
def test_fail_needs_candidate_attributed_failure_evidence(
    kind: str, changes: dict[str, Any]
) -> None:
    rejects(obs(kind, "FAIL", **changes))


def test_structural_and_equivalence_fail() -> None:
    accepts(obs("lint", "FAIL", execution_report=structural(errors=1),
                diagnostics=[diag("candidate")]))
    accepts(obs("equivalence", "FAIL", evidence_refs=CEX,
                execution_report={"report_kind": "equivalence", "proved": False}))


# ---- non-verdict statuses -----------------------------------------------------------------------


def test_timeout_without_report_is_valid() -> None:
    o = accepts(obs("random_sim", "TIMEOUT", duration_ms=600000))
    assert o.status == "TIMEOUT" and o.execution_report is None


@pytest.mark.parametrize(
    "changes",
    [
        {"duration_ms": 599999},
        {"duration_ms": 600000,
         "execution_report": sim_report(["t_a", "t_b"], [("t_a", "FAIL")])},  # timeout != fail
        {"duration_ms": 600000, "evidence_refs": CEX},
        {"duration_ms": 600000, "diagnostics": [diag("candidate")]},
    ],
)
def test_timeout_rules(changes: dict[str, Any]) -> None:
    rejects(obs("random_sim", "TIMEOUT", **changes))


def test_timeout_with_partial_passing_report_is_not_evidence_but_allowed() -> None:
    o = accepts(obs("random_sim", "TIMEOUT", duration_ms=600000,
                    execution_report=sim_report(["t_a", "t_b"], [("t_a", "PASS")])))
    assert o.status == "TIMEOUT"  # raw status kept; never re-expressed as PASS or FAIL


def test_tool_error_without_report_is_valid() -> None:
    o = accepts(obs("formal", "TOOL_ERROR", diagnostics=[diag("infrastructure",
                                                               message="license expired")]))
    assert o.execution_report is None


@pytest.mark.parametrize(
    "changes",
    [
        {"diagnostics": []},
        {"diagnostics": [diag("evaluator")]},
        {"diagnostics": [diag("infrastructure"), diag("candidate")]},
        {"diagnostics": [diag("infrastructure")], "evidence_refs": CEX},
        {"diagnostics": [diag("infrastructure")],
         "execution_report": formal_report([("R03_sva", "FAIL")], reached=3)},
    ],
)
def test_tool_error_identifies_infrastructure_without_labelling_rtl(
    changes: dict[str, Any],
) -> None:
    rejects(obs("formal", "TOOL_ERROR", **changes))


def test_formal_inconclusive_with_unmet_depth() -> None:
    o = accepts(obs(status="INCONCLUSIVE", execution_report=formal_report(
        [("R03_sva", "PASS"), ("R17_sva", "PASS")], reached=31)))
    assert o.status == "INCONCLUSIVE"


@pytest.mark.parametrize(
    ("kind", "changes"),
    [
        ("formal", {}),  # no report
        ("formal", {"execution_report": formal_report(
            [("R03_sva", "PASS"), ("R17_sva", "PASS")])}),  # bound met
        ("equivalence", {"execution_report": {"report_kind": "equivalence", "proved": True}}),
        ("directed_sim", {"execution_report": SIM_PASS}),
        ("formal", {"evidence_refs": CEX, "execution_report": formal_report(
            [("R03_sva", "FAIL")], reached=3)}),
    ],
)
def test_inconclusive_rules(kind: str, changes: dict[str, Any]) -> None:
    rejects(obs(kind, "INCONCLUSIVE", **changes))


def test_unsupported_needs_a_capability_code() -> None:
    accepts(obs("parse_elaborate", "UNSUPPORTED",
                diagnostics=[diag("evaluator", "error", code="sv_interface_class")]))
    rejects(obs("parse_elaborate", "UNSUPPORTED", diagnostics=[diag("evaluator", "error")]))


@pytest.mark.parametrize("status", ["INVALID_SUBMISSION", "INVALID_TASK", "pass", "ERROR"])
def test_only_raw_tool_statuses(status: str) -> None:
    rejects({**EXAMPLE, "status": status})


# ---- result fields ------------------------------------------------------------------------------


def test_diagnostics_cap_and_truncation_flag() -> None:
    many = [diag("candidate", "warning") for _ in range(200)]
    accepts(obs("lint", "PASS", execution_report=structural(), diagnostics=many,
                diagnostics_truncated=True))
    rejects(obs("lint", "PASS", execution_report=structural(), diagnostics=[*many, diag()]))
    rejects(obs("lint", "PASS", execution_report=structural(), diagnostics=many[:3],
                diagnostics_truncated=True))


@pytest.mark.parametrize("summary", ["", "   ", "x" * 501])
def test_summary_is_short_and_non_blank(summary: str) -> None:
    rejects({**EXAMPLE, "summary": summary})


@pytest.mark.parametrize(
    "started_at",
    ["2026-10-04 09:15:00Z", "2026-10-04T09:15:00", "2026-10-04T09:15:00.5Z",
     "2026-1-4T09:15:00Z", "2026-13-04T09:15:00Z", "2026-10-04T09:15:00+00:00"],
)
def test_started_at_is_exact_utc_seconds(started_at: str) -> None:
    rejects({**EXAMPLE, "started_at": started_at})


@pytest.mark.parametrize("duration", [41.2, -1, "41200"])
def test_duration_is_non_negative_strict_int(duration: Any) -> None:
    rejects({**EXAMPLE, "duration_ms": duration})


def test_floats_rejected_with_the_records_message() -> None:
    rejects({**EXAMPLE, "duration_ms": 41.2}, match="binary floats")


def test_records_are_immutable() -> None:
    o = accepts(EXAMPLE)
    with pytest.raises(ValidationError):
        o.status = "PASS"  # type: ignore[assignment]
    assert isinstance(o.diagnostics, tuple) and isinstance(o.evidence_refs, tuple)
