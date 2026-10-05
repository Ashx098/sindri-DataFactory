import json
import math
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from mypy import api as mypy_api
from pydantic import BaseModel, ValidationError

from sindri.core.ids import (
    CandidateId,
    CheckId,
    ConfigurationId,
    ContentId,
    ContractId,
    EpisodeId,
    ExceptionId,
    FamilyId,
    FindingId,
    JobId,
    LineageId,
    ObligationId,
    ObservationId,
    PolicyId,
    PropertyId,
    RequirementId,
    TaskId,
    ToolProfileId,
    VariantId,
    canonical_json_bytes,
    canonical_json_id,
    content_id,
)

# Aliased so pytest does not try to collect the domain type `TestId` as a test class.
from sindri.core.ids import TestId as SimTestId

# ---- content IDs ------------------------------------------------------------------------------


@given(st.binary())
def test_content_id_is_deterministic(data: bytes) -> None:
    assert content_id(data) == content_id(bytes(data))
    assert ContentId.PATTERN.fullmatch(content_id(data))


@given(st.binary(min_size=1), st.data())
def test_any_single_changed_byte_changes_the_id(data: bytes, draw: st.DataObject) -> None:
    i = draw.draw(st.integers(0, len(data) - 1))
    new_byte = draw.draw(st.integers(0, 255).filter(lambda b: b != data[i]))
    mutated = data[:i] + bytes([new_byte]) + data[i + 1 :]
    assert content_id(mutated) != content_id(data)


@given(st.binary(), st.binary(min_size=1))
def test_appending_bytes_changes_the_id(data: bytes, extra: bytes) -> None:
    assert content_id(data + extra) != content_id(data)


def test_content_id_known_vector() -> None:
    assert content_id(b"") == (
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_content_id_rejects_text() -> None:
    with pytest.raises(TypeError):
        content_id("not bytes")  # type: ignore[arg-type]


# ---- canonical JSON IDs -----------------------------------------------------------------------

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(max_size=8), children, max_size=4),
    max_leaves=20,
)


def _reorder(value: Any) -> Any:
    """Same JSON value with every object's keys in reverse insertion order."""
    if isinstance(value, dict):
        return {k: _reorder(value[k]) for k in reversed(list(value))}
    if isinstance(value, list):
        return [_reorder(v) for v in value]
    return value


@given(json_values)
def test_canonical_id_ignores_key_order(value: Any) -> None:
    assert canonical_json_id(_reorder(value)) == canonical_json_id(value)


@given(json_values, st.sampled_from([None, 0, 2, 4]))
def test_canonical_id_ignores_formatting(value: Any, indent: int | None) -> None:
    text = json.dumps(value, indent=indent)
    assert canonical_json_id(json.loads(text)) == canonical_json_id(value)


@given(st.dictionaries(st.text(max_size=8), st.integers(), min_size=1), st.data())
def test_canonical_id_changes_with_any_value(value: dict[str, int], draw: st.DataObject) -> None:
    key = draw.draw(st.sampled_from(sorted(value)))
    changed = {**value, key: value[key] + 1}
    assert canonical_json_id(changed) != canonical_json_id(value)


def test_canonical_bytes_are_compact_sorted_utf8() -> None:
    assert canonical_json_bytes({"b": 1, "a": ["ü", None]}) == '{"a":["ü",null],"b":1}'.encode()


def test_json_types_are_not_conflated() -> None:
    ids = {canonical_json_id(v) for v in (1, 1.0, True, "1", [1], {"1": 1})}
    assert len(ids) == 6


@pytest.mark.parametrize(
    "value",
    [
        {1: "int key would silently become '1'"},
        (1, 2),
        {1, 2},
        b"bytes",
        math.nan,
        math.inf,
        {"nested": [object()]},
    ],
)
def test_non_json_native_values_are_rejected(value: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_json_id(value)


# ---- typed domain IDs -------------------------------------------------------------------------

VALID = [
    (TaskId, "pktfr_0193"),
    (CandidateId, "c_pktfr_0193_e17_v3"),
    (ObservationId, "ob_88121"),
    (EpisodeId, "e17"),
    (RequirementId, "R17"),
    (PolicyId, "ep_fifo_004"),
    (FindingId, "F42"),
    (ContentId, "sha256:" + "0" * 64),
    (FamilyId, "stream-framing"),
    (LineageId, "pktfr"),
    (VariantId, "maxlen4-64_datasheet"),
    (ContractId, "ct_pktfr_0193_v3"),
    (ObligationId, "sim_stall_01"),
    (ObligationId, "sva_stall_stable"),
    (CheckId, "chk_formal_core"),
    (ConfigurationId, "cfg_w8_d8"),
    (ToolProfileId, "tp_sby_bmc_v0"),
    (ExceptionId, "ex_formal_w32"),
    (SimTestId, "stall_stability_004"),
    (PropertyId, "R03_sva"),
    (PropertyId, "sva_stall_stable"),
    (JobId, "job_771"),
]

INVALID = [
    (TaskId, "Pktfr_0193"),
    (TaskId, "pktfr__0193"),
    (TaskId, "0193"),
    (TaskId, ""),
    (CandidateId, "pktfr_0193_e17_v3"),
    (CandidateId, "c_"),
    (ObservationId, "88121"),
    (ObservationId, "ob_8812 1"),
    (EpisodeId, "17"),
    (EpisodeId, "e17a"),
    (RequirementId, "r17"),
    (RequirementId, "R"),
    (PolicyId, "fifo_004"),
    (FindingId, "F42x"),
    (ContentId, "sha256:" + "0" * 63),
    (ContentId, "sha256:" + "A" * 64),
    (ContentId, "md5:" + "0" * 64),
    (FamilyId, "Stream-Framing"),
    (FamilyId, "stream--framing"),
    (FamilyId, "-stream"),
    (LineageId, "pktfr_"),
    (VariantId, "maxlen 4"),
    (ContractId, "pktfr_0193_v3"),
    (ContractId, "ct_"),
    (ObligationId, "Sim_stall"),
    (ObligationId, "1sim"),
    (CheckId, "formal_core"),
    (ConfigurationId, "cfg-w8"),
    (ToolProfileId, "tp_"),
    (ExceptionId, "exc_formal"),
    (SimTestId, "Stall_test"),
    (SimTestId, "4_stall"),
    (PropertyId, "R03-sva"),
    (PropertyId, "_R03"),
    (JobId, "771"),
    (JobId, "job-771"),
]


@pytest.mark.parametrize(("cls", "value"), VALID)
def test_master_architecture_examples_are_valid(cls: type[str], value: str) -> None:
    built = cls(value)
    assert built == value
    assert isinstance(built, cls)
    assert cls(built) is built


@pytest.mark.parametrize(("cls", "value"), INVALID)
def test_malformed_ids_are_rejected(cls: type[str], value: str) -> None:
    with pytest.raises(ValueError):
        cls(value)


def test_ids_must_be_built_from_str() -> None:
    with pytest.raises(TypeError):
        TaskId(193)  # type: ignore[arg-type]


def test_pydantic_fields_validate_and_serialize_as_plain_strings() -> None:
    class Ref(BaseModel):
        task: TaskId
        artifact: ContentId

    ref = Ref.model_validate({"task": "pktfr_0193", "artifact": "sha256:" + "a" * 64})
    assert type(ref.task) is TaskId
    assert ref.model_dump() == {"task": "pktfr_0193", "artifact": "sha256:" + "a" * 64}
    with pytest.raises(ValidationError):
        Ref.model_validate({"task": "BAD ID", "artifact": "sha256:" + "a" * 64})
    with pytest.raises(ValidationError):
        Ref.model_validate({"task": 193, "artifact": "sha256:" + "a" * 64})


def test_id_types_are_not_interchangeable_for_the_type_checker(tmp_path: Path) -> None:
    """Passing one kind of ID, or a bare str, where another is expected is a mypy error."""
    code = """
from sindri.core.ids import CandidateId, TaskId

def load_task(task: TaskId) -> None: ...

load_task(CandidateId("c_x"))
load_task("pktfr_0193")
load_task(TaskId("pktfr_0193"))
"""
    config = tmp_path / "mypy.ini"  # isolate from the repo config, which pins `packages`
    config.write_text("[mypy]\n")
    stdout, stderr, exit_code = mypy_api.run(
        ["--config-file", str(config), "--strict", "--no-incremental", "-c", code]
    )
    assert not stderr, stderr
    errors = [line for line in stdout.splitlines() if ": error:" in line]
    assert exit_code == 1, stdout
    assert len(errors) == 2, stdout
    assert all('"load_task" has incompatible type' in e for e in errors), stdout
