"""SIN-P1.1-008 S1, S2, S7, S12: every record and union variant survives serialization exactly."""

import json
from typing import Any

import pytest
from pydantic import BaseModel

from sindri.core.ids import canonical_json_bytes
from tests.contract._record_catalog import CATALOG, Entry


def transport_dump(record: BaseModel) -> str:
    """The transport serializer under test. Never exclude None: nullable keys are required."""
    return record.model_dump_json()


def json_dump(record: BaseModel) -> Any:
    return record.model_dump(mode="json")


def canonical(record: BaseModel) -> bytes:
    return canonical_json_bytes(json_dump(record))


def shape(value: Any) -> Any:
    """Recursive type fingerprint: classes of every model, typed ID, enum, scalar and container."""
    if isinstance(value, BaseModel):
        fields = type(value).model_fields
        return (type(value).__name__, {k: shape(getattr(value, k)) for k in fields})
    if isinstance(value, tuple):
        return ("tuple", [shape(v) for v in value])
    return (type(value).__name__, value)


ids = [e.name for e in CATALOG]


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_three_round_trip_paths_preserve_record_and_identity(entry: Entry) -> None:
    record = entry.build()
    paths = {
        "transport": entry.model.model_validate_json(transport_dump(record)),
        "json-native": entry.model.model_validate(json_dump(record)),
        "canonical-bytes": entry.model.model_validate_json(canonical(record)),
    }
    for path, again in paths.items():
        assert again == record, path
        assert again.content_id() == record.content_id(), path  # type: ignore[attr-defined]


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_same_serializer_re_emission_is_byte_stable(entry: Entry) -> None:
    record = entry.build()
    first = transport_dump(record)
    assert transport_dump(entry.model.model_validate_json(first)) == first
    first_canonical = canonical(record)
    assert canonical(entry.model.model_validate_json(first_canonical)) == first_canonical


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_types_ids_enums_nulls_empties_and_variants_survive(entry: Entry) -> None:
    record = entry.build()
    again = entry.model.model_validate_json(transport_dump(record))
    assert shape(again) == shape(record)


def _all_keys_present(model: BaseModel, dumped: Any) -> None:
    assert set(dumped) == set(type(model).model_fields), type(model).__name__
    for name in type(model).model_fields:
        value = getattr(model, name)
        if isinstance(value, BaseModel):
            _all_keys_present(value, dumped[name])
        elif isinstance(value, tuple):
            for item, item_dump in zip(value, dumped[name], strict=True):
                if isinstance(item, BaseModel):
                    _all_keys_present(item, item_dump)


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_every_dump_keeps_every_key_including_nulls(entry: Entry) -> None:
    record = entry.build()
    _all_keys_present(record, json_dump(record))
    _all_keys_present(record, json.loads(transport_dump(record)))


def test_catalog_contains_the_required_edge_shapes() -> None:
    names = {e.name for e in CATALOG}
    for required in (
        "EvaluationPolicy/zero-parameter-cfg_default",
        "EpisodeState/waiting-plan-candidate-less-job",
        "EpisodeState/aborted",
        "FindingTransition/existing-policy-check",
        "FindingTransition/formal-probe",
        "Observation/tool-error-no-report",
        "CandidateManifest/reconstructor",
    ):
        assert required in names


def test_zero_parameter_configuration_keeps_its_empty_assignments() -> None:
    entry = next(e for e in CATALOG if e.name == "EvaluationPolicy/zero-parameter-cfg_default")
    again = entry.model.model_validate_json(transport_dump(entry.build()))
    assert again.configurations[0].assignments == ()  # type: ignore[attr-defined]
