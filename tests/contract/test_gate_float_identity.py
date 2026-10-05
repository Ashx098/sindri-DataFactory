"""P1.1-G A5: the float/identity follow-up (SIN-P1.1-001, 002 D5) holds across the whole record set.

Every input to a record hash constructor (`Record.content_id`, `candidate_source_hash`,
`observation_execution_key`) is float-free, for every 008 catalog entry and every record of the
009 coherent bundle; and each record's identity is the canonical JSON identity of its JSON dump.
"""

from typing import Any

import pytest

from sindri.core.ids import canonical_json_bytes, canonical_json_id
from sindri.schemas import CandidateManifest, Observation, candidate_source_hash
from sindri.schemas._base import Record
from tests.contract._record_catalog import CATALOG
from tests.contract.cross_record._bundle import positive_spec, records


def _floats(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, float):
        return [path]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _floats(v, f"{path}.{k}")]
    if isinstance(value, list | tuple):
        return [p for i, v in enumerate(value) for p in _floats(v, f"{path}[{i}]")]
    return []


def _all_records() -> list[Record]:
    return [e.build() for e in CATALOG] + records(positive_spec())


@pytest.mark.parametrize("record", _all_records(), ids=lambda r: type(r).__name__)
def test_hash_inputs_are_float_free_and_identity_is_canonical(record: Record) -> None:
    dumped = record.model_dump(mode="json")
    assert _floats(dumped) == []
    assert record.content_id() == canonical_json_id(dumped)
    assert canonical_json_bytes(dumped)  # encodable: JSON-native, no NaN/Inf, str keys
    if isinstance(record, CandidateManifest):
        assert _floats([f.model_dump(mode="json") for f in record.files]) == []
        assert record.source_hash == candidate_source_hash(record.files)
    if isinstance(record, Observation):
        assert record.execution_key == record.computed_execution_key()


def test_sweep_covers_every_record_type() -> None:
    assert {type(r).__name__ for r in _all_records()} == {
        "TaskManifest", "Requirement", "EvaluationPolicy", "CandidateManifest", "Observation",
        "Finding", "FindingTransition", "EpisodeBudget", "EpisodeState",
    }
