"""SIN-P1.6-001: the FIFO engineering seed's P1.1 records and fixture metadata are consistent.

Pure checks (no EDA tool). The Icarus reproduction lives in tests/eda/test_fifo_seed_icarus.py.
"""

import json
import re
from pathlib import Path
from typing import Any

from sindri.core.ids import content_id
from sindri.schemas import (
    AllSupportedConfigs,
    EvaluationPolicy,
    MutationSource,
    ParameterScope,
    Requirement,
    RequirementDisposition,
    TaskManifest,
    UseCaseSource,
    check_records,
)

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "evals" / "fixtures" / "fifo"
TASKS = ("fifo_seed", "fifo_seed_m4")


def _json(rel: str) -> Any:
    return json.loads((SEED / rel).read_text())


def _records(task: str) -> tuple[TaskManifest, list[Requirement], EvaluationPolicy]:
    base = f"records/{task}"
    return (TaskManifest.model_validate(_json(f"{base}/task_manifest.json")),
            [Requirement.model_validate(r) for r in _json(f"{base}/requirements.json")],
            EvaluationPolicy.model_validate(_json(f"{base}/evaluation_policy.json")))


def _all_records() -> list[Any]:
    out: list[Any] = []
    for task in TASKS:
        t, rs, p = _records(task)
        out += [t, *rs, p]
    return out


def test_records_validate_and_form_a_clean_closed_bundle() -> None:
    assert len(_all_records()) == 22
    assert check_records(_all_records()) == ()


def test_contract_hash_is_the_exact_contract_bytes() -> None:
    h = content_id((SEED / "contract" / "contract.md").read_bytes())
    for task in TASKS:
        t, _, p = _records(task)
        assert t.approved_contract_hash == h and p.contract_hash == h
        assert t.contract_id == "ct_fifo_seed_v1" and t.golden_hash is None
        assert t.authority_mode.value == "engineering_intent"


def test_contract_is_approved_for_development_but_uncertified() -> None:
    text = (SEED / "contract" / "contract.md").read_text()
    assert "Status: `engineering-seed-approved`" in text
    assert "Certification: `uncertified`" in text


def test_requirements_are_approved_mandatory_r01_to_r09() -> None:
    for task in TASKS:
        t, rs, _ = _records(task)
        assert [r.requirement_id for r in rs] == [f"R0{i}" for i in range(1, 10)]
        assert list(t.requirement_ids) == [r.requirement_id for r in rs]
        assert all(r.disposition is RequirementDisposition.APPROVED and r.mandatory for r in rs)


def _depths(policy: EvaluationPolicy) -> list[int]:
    return [next(a.value for a in c.assignments if a.name == "DEPTH")  # type: ignore[misc]
            for c in policy.configurations]


def test_r07_encodes_exact_finite_applicability() -> None:
    """Prose rule DEPTH >= 2, encoded exactly over the finite matrix (PR #33)."""
    for task in TASKS:
        _, rs, p = _records(task)
        r07 = next(r for r in rs if r.requirement_id == "R07")
        assert isinstance(r07.applicability, ParameterScope)
        (scope,) = r07.applicability.parameters
        assert scope.name == "DEPTH"
        assert list(scope.values) == sorted({d for d in _depths(p) if d >= 2}) == [2, 3, 4, 8]
        others = [r for r in rs if r.requirement_id != "R07"]
        assert all(isinstance(r.applicability, AllSupportedConfigs) for r in others)


def test_sources_follow_f9_and_f11() -> None:
    base, _, _ = _records("fifo_seed")
    debug, _, _ = _records("fifo_seed_m4")
    assert isinstance(base.source, UseCaseSource)
    assert base.source.intake_ref == "sindri:p1.6/fifo-seed-v1"
    assert isinstance(debug.source, MutationSource)
    assert debug.source.parent_task_id == "fifo_seed"
    assert (SEED / "mutants" / f"{debug.source.operator}.v").is_file()


def _applies(req: Requirement, assignments: dict[str, int]) -> bool:
    if isinstance(req.applicability, AllSupportedConfigs):
        return True
    return all(assignments[p.name] in p.values for p in req.applicability.parameters)


def test_inventory_is_configuration_scoped_by_requirement_applicability() -> None:
    inv = _json("tb/tests.json")
    _, rs, p = _records("fifo_seed")
    reqs = {r.requirement_id: r for r in rs}
    assert list(inv["configurations"]) == [c.configuration_id for c in p.configurations]
    all_tests = list(inv["test_requirements"])
    assert {r for v in inv["test_requirements"].values() for r in v} == set(reqs)
    for cfg in p.configurations:
        assignments = {a.name: a.value for a in cfg.assignments}
        entry = inv["configurations"][cfg.configuration_id]
        assert entry["assignments"] == assignments
        wanted = [t for t in all_tests
                  if all(_applies(reqs[r], assignments) for r in inv["test_requirements"][t])]
        assert entry["expected_tests"] == wanted
    assert "simultaneous_push_pop" not in inv["configurations"]["cfg_w8_d1"]["expected_tests"]


def test_testbench_emits_exactly_the_inventory_test_ids() -> None:
    source = (SEED / "tb" / "tb_fifo.v").read_text()
    emitted = re.findall(r'end_test\("([A-Za-z0-9_]+)"\)', source)
    assert sorted(emitted) == sorted(_json("tb/tests.json")["test_requirements"])


def test_mutant_manifest_is_complete_and_uncertified() -> None:
    m = _json("mutants/manifest.json")
    configs = list(_json("tb/tests.json")["configurations"])
    assert m["status"] == "uncertified" and m["configurations"] == configs
    ref = (SEED / m["base"]).read_text()
    assert len(m["mutants"]) == 5 and len({x["bug_class"] for x in m["mutants"]}) == 5
    for x in m["mutants"]:
        text = (SEED / x["file"]).read_text()
        assert text != ref and "UNCERTIFIED" in text
        assert set(x["kill_matrix"]) == set(configs)
        assert set(x["kill_matrix"].values()) <= {"killed", "survived"}
        assert "killed" in x["kill_matrix"].values(), x["id"]
        survived = {c for c, v in x["kill_matrix"].items() if v == "survived"}
        assert set(x["seed_analysis"]) == survived, x["id"]
        assert all("uncertified" in note for note in x["seed_analysis"].values())


def test_known_bad_testbench_is_quarantined_from_the_positive_path() -> None:
    positive = sorted(p.name for p in (SEED / "tb").glob("*.v"))
    assert positive == ["tb_fifo.v"]
    assert not list((SEED / "rtl").glob("*tb*")) and not list((SEED / "mutants").glob("*tb*"))
    assert (SEED / "known_bad" / "tb_fifo_xblind.v").is_file()


def test_xblind_is_the_documented_mechanical_transform_of_the_strict_testbench() -> None:
    strict = (SEED / "tb" / "tb_fifo.v").read_text()
    bad = (SEED / "known_bad" / "tb_fifo_xblind.v").read_text()
    def body(text: str) -> str:  # everything after the (differing) leading header lines
        return text[text.index("// Result protocol"):]

    expected = body(strict).replace("    if (cond !== 1'b1) begin", "    if (!cond) begin")
    assert body(bad) == expected.replace("===", "==")


def test_every_artifact_is_labelled_uncertified() -> None:
    for path in sorted(SEED.rglob("*")):
        if path.suffix in {".v", ".md"}:
            assert "uncertified" in path.read_text().lower(), path.relative_to(SEED)
    assert _json("tb/tests.json")["certification"] == "uncertified"
    assert "quarantined" in _json("known_bad/manifest.json")["status"]
