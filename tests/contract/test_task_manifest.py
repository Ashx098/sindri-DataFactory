"""Contract tests for TaskManifest (SIN-P1.1-002 acceptance criteria)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.core.status import AuthorityMode
from sindri.schemas import READ_ONLY_TASK_TYPES, TaskManifest, TaskType

EXAMPLE = json.loads((Path(__file__).parent / "examples/task_manifest.json").read_text())
SHA = "sha256:" + "ab" * 32
COMMIT = "c" * 40


def manifest(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    return data


def rejects(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        TaskManifest.model_validate(data)


# ---- positive ---------------------------------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    m = TaskManifest.model_validate(EXAMPLE)
    assert TaskManifest.model_validate_json(m.model_dump_json()) == m
    assert json.loads(m.model_dump_json()) == EXAMPLE


@pytest.mark.parametrize(
    "source",
    [
        {"kind": "repo_cut", "repo": "https://x/y", "commit": COMMIT},
        {"kind": "commit_feature", "repo": "https://x/y", "commit": "d" * 64},
        {"kind": "commit_fix", "repo": "https://x/y", "commit": COMMIT},
        {"kind": "mutation", "parent_task_id": "pktfr_0193", "operator": "reset_polarity_flip"},
        {"kind": "generator", "generator_id": "fifo_sync", "generator_version": "1.2.0"},
        {"kind": "use_case", "intake_ref": "use_case:12"},
    ],
)
def test_every_source_kind_validates(source: dict[str, Any]) -> None:
    assert TaskManifest.model_validate(manifest(source=source)).source.kind == source["kind"]


def test_restrictive_rights_combination_validates() -> None:
    rights = {
        "licence": None,
        "written_agreement_ref": "agreement:client-7/2026-09",
        "training_allowed": False,
        "evaluation_allowed": True,
        "redistribution_allowed": False,
        "customer_restricted": True,
    }
    m = TaskManifest.model_validate(manifest(rights=rights))
    assert m.rights.training_allowed is False and m.rights.customer_restricted is True


@pytest.mark.parametrize("task_type", sorted(READ_ONLY_TASK_TYPES))
def test_read_only_task_with_empty_edit_scope_validates(task_type: TaskType) -> None:
    m = TaskManifest.model_validate(manifest(task_type=task_type.value, allowed_edit_paths=[]))
    assert m.allowed_edit_paths == ()


def test_read_only_and_mutating_types_partition_task_types() -> None:
    assert READ_ONLY_TASK_TYPES == {TaskType.COMPREHENSION, TaskType.SPEC_TASK}
    mutating = set(TaskType) - READ_ONLY_TASK_TYPES
    assert {t.value for t in mutating} == {
        "spec_to_rtl", "completion", "modification", "debug", "testbench", "assertion",
    }


def test_non_reference_modes_may_omit_golden() -> None:
    for mode in (AuthorityMode.ENGINEERING_INTENT, AuthorityMode.CORRECT_BY_CONSTRUCTION):
        m = TaskManifest.model_validate(manifest(authority_mode=mode.value, golden_hash=None))
        assert m.golden_hash is None


def test_later_version_with_supersedes_validates() -> None:
    m = TaskManifest.model_validate(manifest(manifest_version=2, supersedes=SHA))
    assert m.manifest_version == 2


def test_content_id_ignores_key_order_and_tracks_every_field() -> None:
    base = TaskManifest.model_validate(EXAMPLE)
    reordered = TaskManifest.model_validate(dict(reversed(list(EXAMPLE.items()))))
    assert reordered.content_id() == base.content_id()
    variants = [
        manifest(split="dev"),
        manifest(variant_id="maxlen4-64_ticket"),
        manifest(allowed_edit_paths=["rtl/pkt_framer.sv", "rtl/pkt_pkg.sv"]),
        manifest(rights={**EXAMPLE["rights"], "training_allowed": False}),
    ]
    ids = {TaskManifest.model_validate(v).content_id() for v in variants}
    assert base.content_id() not in ids and len(ids) == len(variants)


# ---- negative: no silent defaults -------------------------------------------------------------

REQUIRED = [
    "authority_mode", "split", "family_id", "lineage_id", "variant_id", "task_id", "rights",
    "source", "task_type", "supersedes", "golden_hash", "allowed_edit_paths", "schema_version",
    "manifest_version", "contract_id", "approved_contract_hash", "requirement_ids",
]


@pytest.mark.parametrize("field", REQUIRED)
def test_every_field_is_required(field: str) -> None:
    data = manifest()
    del data[field]
    rejects(data)


@pytest.mark.parametrize("field", sorted(EXAMPLE["rights"]))
def test_every_rights_field_is_required(field: str) -> None:
    rights = dict(EXAMPLE["rights"])
    del rights[field]
    rejects(manifest(rights=rights))


def test_rights_need_a_licence_or_agreement() -> None:
    rejects(manifest(rights={**EXAMPLE["rights"], "licence": None, "written_agreement_ref": None}))


@pytest.mark.parametrize("value", ["yes", 1, "true", None])
def test_rights_flags_are_strict_booleans(value: Any) -> None:
    rejects(manifest(rights={**EXAMPLE["rights"], "training_allowed": value}))


# ---- negative: closed records -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [(), ("source",), ("rights",)],
    ids=["top-level", "source", "rights"],
)
def test_unknown_fields_rejected_at_every_level(path: tuple[str, ...]) -> None:
    data = manifest()
    target = data
    for key in path:
        target = target[key]
    target["tier"] = "silver"
    rejects(data)


@pytest.mark.parametrize("field", ["tier", "evidence_level", "difficulty", "status_history"])
def test_lifecycle_fields_are_not_part_of_the_manifest(field: str) -> None:
    rejects(manifest(**{field: "x"}))  # D1: lifecycle state lives in the registry


@pytest.mark.parametrize("version", [2, 0, True, 1.0, "1"])
def test_schema_version_must_be_exactly_integer_1(version: Any) -> None:
    rejects(manifest(schema_version=version))


# ---- negative: authority, source and versioning -----------------------------------------------


def test_reference_behavior_requires_golden_hash() -> None:
    rejects(manifest(authority_mode="reference_behavior", golden_hash=None))


@pytest.mark.parametrize(
    "source",
    [
        {"kind": "repo_cut", "repo": "https://x/y"},
        {"kind": "repo_cut", "commit": COMMIT},
        {"kind": "repo_cut", "repo": "https://x/y", "commit": "abc1234"},
        {"kind": "repo_cut", "repo": "https://x/y", "commit": "C" * 40},
        {"kind": "mutation", "operator": "flip"},
        {"kind": "mutation", "parent_task_id": "pktfr_0193"},
        {"kind": "generator", "generator_id": "fifo_sync"},
        {"kind": "use_case"},
        {"kind": "use_case", "intake_ref": "   "},
        {"kind": "scraped", "repo": "https://x/y", "commit": COMMIT},
    ],
)
def test_source_kinds_require_their_fields(source: dict[str, Any]) -> None:
    rejects(manifest(source=source))


@pytest.mark.parametrize(
    ("version", "supersedes"), [(2, None), (1, SHA), (0, None), (3, "sha256:bad")]
)
def test_version_chain_is_enforced(version: int, supersedes: str | None) -> None:
    rejects(manifest(manifest_version=version, supersedes=supersedes))


# ---- negative: edit scope (C3) ----------------------------------------------------------------


@pytest.mark.parametrize("task_type", sorted(set(TaskType) - READ_ONLY_TASK_TYPES))
def test_mutating_types_require_edit_scope(task_type: TaskType) -> None:
    rejects(manifest(task_type=task_type.value, allowed_edit_paths=[]))


@pytest.mark.parametrize("task_type", sorted(READ_ONLY_TASK_TYPES))
def test_read_only_types_reject_edit_scope(task_type: TaskType) -> None:
    rejects(manifest(task_type=task_type.value, allowed_edit_paths=["rtl/x.sv"]))


@pytest.mark.parametrize(
    "paths",
    [
        ["/etc/passwd"],
        ["rtl/../tests/hidden.py"],
        [".."],
        ["rtl//x.sv"],
        ["rtl/./x.sv"],
        ["rtl\\x.sv"],
        [""],
        ["rtl/x.sv", "rtl/x.sv"],
    ],
)
def test_unsafe_or_duplicate_edit_paths_rejected(paths: list[str]) -> None:
    rejects(manifest(allowed_edit_paths=paths))


# ---- negative: enums, requirements, floats, immutability --------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("split", "holdout"),
        ("split", "Train"),
        ("task_type", "refactor"),
        ("authority_mode", "golden"),
    ],
)
def test_unknown_enum_values_rejected(field: str, value: str) -> None:
    rejects(manifest(**{field: value}))


@pytest.mark.parametrize("ids", [[], ["R03", "R03"], ["r03"]])
def test_requirement_ids_non_empty_unique_and_valid(ids: list[str]) -> None:
    rejects(manifest(requirement_ids=ids))


@pytest.mark.parametrize(
    "changes",
    [
        {"manifest_version": 1.0},
        {"rights": {**EXAMPLE["rights"], "training_allowed": 1.0}},
        {"source": {**EXAMPLE["source"], "repo": 0.5}},
        {"difficulty": {"pass_rate": 0.25}},
    ],
)
def test_binary_floats_rejected_at_any_depth(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="binary floats"):
        TaskManifest.model_validate(manifest(**changes))


def test_records_are_immutable() -> None:
    m = TaskManifest.model_validate(EXAMPLE)
    with pytest.raises(ValidationError):
        m.split = "final"  # type: ignore[assignment]
    with pytest.raises(ValidationError):
        m.rights.training_allowed = False  # type: ignore[misc]
    assert isinstance(m.allowed_edit_paths, tuple)
