"""Contract tests for CandidateManifest (SIN-P1.1-004 acceptance criteria)."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sindri.core.ids import canonical_json_id
from sindri.schemas import CandidateFile, CandidateManifest, candidate_source_hash

EXAMPLE = json.loads((Path(__file__).parent / "examples/candidate_manifest.json").read_text())
H1 = "sha256:" + "4f" * 32
H2 = "sha256:" + "a7" * 32
PATCH = "sha256:" + "5e" * 32


def files_of(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"path": p, "hash": h} for p, h in pairs]


def src(files: list[dict[str, str]]) -> str:
    return candidate_source_hash(CandidateFile.model_validate(f) for f in files)


def candidate(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    if "files" in changes and "source_hash" not in changes:
        data["source_hash"] = src(data["files"])
    return data


def rejects(data: dict[str, Any], match: str | None = None) -> None:
    with pytest.raises(ValidationError, match=match):
        CandidateManifest.model_validate(data)


# ---- source hash construction (F3) ------------------------------------------------------------


def test_source_hash_matches_independent_byte_level_vector() -> None:
    """Pins the exact construction without going through canonical_json_id."""
    raw = (
        '{"files":[{"hash":"' + H1 + '","path":"rtl/a.sv"},'
        '{"hash":"' + H2 + '","path":"rtl/b.sv"}],'
        '"kind":"candidate_file_set_v1"}'
    ).encode()
    expected = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert src(files_of(("rtl/b.sv", H2), ("rtl/a.sv", H1))) == expected


def test_source_hash_ignores_input_order() -> None:
    a = files_of(("rtl/a.sv", H1), ("rtl/b.sv", H2), ("tb/c.py", H1))
    assert src(a) == src(list(reversed(a)))


@pytest.mark.parametrize(
    "changed",
    [
        files_of(("rtl/a.sv", H2), ("rtl/b.sv", H2)),  # a hash changed
        files_of(("rtl/x.sv", H1), ("rtl/b.sv", H2)),  # a path changed
        files_of(("rtl/a.sv", H1)),  # a file removed
    ],
)
def test_source_hash_changes_with_any_path_or_hash(changed: list[dict[str, str]]) -> None:
    assert src(changed) != src(files_of(("rtl/a.sv", H1), ("rtl/b.sv", H2)))


def _plain_files(files: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(files, key=lambda f: f["path"])


@pytest.mark.parametrize(
    "wrong",
    [
        lambda fs: canonical_json_id({"files": _plain_files(fs)}),  # no domain tag
        lambda fs: canonical_json_id(
            {"kind": "candidate_file_set_v2", "files": _plain_files(fs)}
        ),
        lambda fs: canonical_json_id({"kind": "candidate_file_set_v1", "files": fs[::-1]}),
        lambda fs: canonical_json_id(_plain_files(fs)),
    ],
    ids=["no-tag", "other-tag", "unsorted", "bare-list"],
)
def test_source_hash_from_other_constructions_rejected(wrong: Any) -> None:
    files = files_of(("rtl/a.sv", H1), ("rtl/b.sv", H2))
    rejects(candidate(files=files, source_hash=wrong(files)), match="source_hash")


# ---- positive ---------------------------------------------------------------------------------


def test_master_example_validates_and_round_trips() -> None:
    c = CandidateManifest.model_validate(EXAMPLE)
    assert CandidateManifest.model_validate_json(c.model_dump_json()) == c
    assert json.loads(c.model_dump_json()) == EXAMPLE


def test_first_solver_candidate_has_no_parent_or_patch() -> None:
    c = CandidateManifest.model_validate(candidate(parent_candidate_id=None, patch_hash=None))
    assert c.parent_candidate_id is None and c.patch_hash is None


@pytest.mark.parametrize("role", ["reconstructor", "architecture_explorer"])
def test_oracle_side_candidates_have_no_episode(role: str) -> None:
    c = CandidateManifest.model_validate(
        candidate(producer_role=role, episode_id=None, parent_candidate_id=None, patch_hash=None)
    )
    assert c.episode_id is None


def test_no_dependency_bundle_is_explicit_none() -> None:
    assert CandidateManifest.model_validate(candidate(dependency_hash=None)).dependency_hash is None


def test_provenance_forbidding_training_is_representable() -> None:
    author = {**EXAMPLE["author"], "training_allowed": False}
    c = CandidateManifest.model_validate(candidate(author=author))
    assert c.author.training_allowed is False


# ---- negative: required, closed ---------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(EXAMPLE))
def test_every_field_is_required(field: str) -> None:
    data = candidate()
    del data[field]
    rejects(data)


@pytest.mark.parametrize("field", sorted(EXAMPLE["author"]))
def test_every_author_field_is_required(field: str) -> None:
    author = dict(EXAMPLE["author"])
    del author[field]
    rejects(candidate(author=author))


@pytest.mark.parametrize(
    "changes",
    [
        {"frozen": True},  # F2: lifecycle state, not part of the record
        {"author": {**EXAMPLE["author"], "temperature": 800}},  # F1: renamed to temperature_millis
        {"files": [{**EXAMPLE["files"][0], "mode": "0644"}, EXAMPLE["files"][1]]},
    ],
    ids=["frozen", "temperature", "nested-file"],
)
def test_unknown_fields_rejected(changes: dict[str, Any]) -> None:
    data = copy.deepcopy(EXAMPLE)
    data.update(changes)
    rejects(data)


# ---- negative: ancestry, producer -------------------------------------------------------------


@pytest.mark.parametrize(
    ("parent", "patch"),
    [("c_pktfr_0193_e17_v2", None), (None, PATCH)],
)
def test_parent_and_patch_come_together(parent: str | None, patch: str | None) -> None:
    rejects(candidate(parent_candidate_id=parent, patch_hash=patch), match="both set or both null")


def test_candidate_cannot_be_its_own_parent() -> None:
    rejects(candidate(parent_candidate_id=EXAMPLE["candidate_id"]), match="own parent")


def test_solver_needs_an_episode() -> None:
    rejects(candidate(episode_id=None), match="solver candidates")


@pytest.mark.parametrize("role", ["reconstructor", "architecture_explorer"])
def test_oracle_roles_reject_an_episode(role: str) -> None:
    rejects(candidate(producer_role=role), match="outside an episode")


def test_unknown_producer_role_rejected() -> None:
    rejects(candidate(producer_role="human"))


# ---- negative: files --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "files",
    [
        [],
        files_of(("rtl/a.sv", H1), ("rtl/a.sv", H2)),
        files_of(("/rtl/a.sv", H1)),
        files_of(("rtl/../tb/a.py", H1)),
        files_of(("rtl//a.sv", H1)),
        files_of(("rtl\\a.sv", H1)),
        files_of(("rtl/a.sv", "sha256:short")),
    ],
)
def test_bad_file_sets_rejected(files: list[dict[str, str]]) -> None:
    # Hash the raw dicts with the F3 construction, so the only defect is the file set itself.
    raw_hash = canonical_json_id(
        {"kind": "candidate_file_set_v1", "files": sorted(files, key=lambda f: f["path"])}
    )
    rejects(candidate(files=files, source_hash=raw_hash))


# ---- negative: author (F1, F7) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("temperature_millis", -1),
        ("temperature_millis", "800"),
        ("temperature_millis", True),
        ("temperature_millis", 0.8),
        ("seed", "1234"),
        ("seed", 1234.0),
        ("training_allowed", 1),
        ("training_allowed", "true"),
        ("provenance_ref", ""),
        ("provenance_ref", "   "),
        ("model", ""),
        ("model_version", " "),
    ],
)
def test_bad_author_values_rejected(field: str, value: Any) -> None:
    rejects(candidate(author={**EXAMPLE["author"], field: value}))


def test_floats_rejected_with_the_records_message() -> None:
    author = {**EXAMPLE["author"], "temperature_millis": 0.8}
    rejects(candidate(author=author), match="binary floats")


def test_records_are_immutable() -> None:
    c = CandidateManifest.model_validate(EXAMPLE)
    with pytest.raises(ValidationError):
        c.source_hash = "sha256:" + "0" * 64  # type: ignore[assignment]
    with pytest.raises(ValidationError):
        c.author.training_allowed = False  # type: ignore[misc]
    assert isinstance(c.files, tuple)
