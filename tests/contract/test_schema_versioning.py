"""SIN-P1.1-008 S4, S5, S6, S13: schema_version strictness, domain revisions, schema generation.

`schema_version` is 1 for every P1.1 record and is never parsed leniently (S4, S5: a v1 reader
only; no dispatch registry, no migration framework). TaskManifest, Requirement and EvaluationPolicy
additionally carry a *domain revision* chain (`*_version` + `supersedes`), which is not a schema
version (S6).
"""

import copy
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from tests.contract._record_catalog import (
    CATALOG,
    DOMAIN_REVISION_FIELD,
    FIXTURES,
    TOP_LEVEL_RECORDS,
    H,
)

fixture_ids = [e.name for e in FIXTURES]


def _errors(model: type[BaseModel], data: dict[str, Any]) -> list[Any]:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(data)
    return caught.value.errors()


def _mentions_schema_version(errors: list[Any]) -> bool:
    return any("schema_version" in map(str, e["loc"]) or "schema_version" in e["msg"]
               for e in errors)


@pytest.mark.parametrize("entry", FIXTURES, ids=fixture_ids)
@pytest.mark.parametrize("version", [0, 2, 99, -1, True, 1.0, "1", None])
def test_unsupported_or_malformed_schema_version_is_rejected(entry: Any, version: Any) -> None:
    data = copy.deepcopy(entry.data)
    data["schema_version"] = version
    assert _mentions_schema_version(_errors(entry.model, data))


@pytest.mark.parametrize("entry", FIXTURES, ids=fixture_ids)
def test_missing_schema_version_is_rejected(entry: Any) -> None:
    data = copy.deepcopy(entry.data)
    del data["schema_version"]
    assert _mentions_schema_version(_errors(entry.model, data))


@pytest.mark.parametrize("entry", FIXTURES, ids=fixture_ids)
def test_v2_shaped_record_fails_loudly_including_the_version_error(entry: Any) -> None:
    """Several errors are fine (S4); the schema-version failure must be among them."""
    data = copy.deepcopy(entry.data)
    data.update(schema_version=2, field_added_in_v2="x")
    errors = _errors(entry.model, data)
    assert _mentions_schema_version(errors)


# ---- S6: schema_version vs domain revision ------------------------------------------------------


@pytest.mark.parametrize("model", TOP_LEVEL_RECORDS, ids=lambda m: m.__name__)
def test_revision_inventory_is_locked(model: type[BaseModel]) -> None:
    fields = set(model.model_fields)
    assert "schema_version" in fields
    if model in DOMAIN_REVISION_FIELD:
        assert {DOMAIN_REVISION_FIELD[model], "supersedes"} <= fields
    else:
        assert "supersedes" not in fields
        assert not {"manifest_version", "requirement_version", "policy_version"} & fields


def test_exactly_three_records_carry_domain_revisions() -> None:
    assert {m.__name__ for m in DOMAIN_REVISION_FIELD} == {
        "TaskManifest", "Requirement", "EvaluationPolicy",
    }


@pytest.mark.parametrize(
    "entry", [e for e in CATALOG if e.name.endswith("/revision-2")], ids=lambda e: e.name
)
def test_domain_revision_2_keeps_schema_version_1_and_round_trips(entry: Any) -> None:
    record = entry.build()
    assert record.schema_version == 1
    assert getattr(record, DOMAIN_REVISION_FIELD[entry.model]) == 2
    assert record.supersedes is not None
    again = entry.model.model_validate_json(record.model_dump_json())
    assert again == record and again.content_id() == record.content_id()


@pytest.mark.parametrize("model", list(DOMAIN_REVISION_FIELD), ids=lambda m: m.__name__)
@pytest.mark.parametrize(("revision", "supersedes"), [(1, H("aa")), (2, None)])
def test_domain_revision_chain_shape(model: type[BaseModel], revision: int,
                                     supersedes: str | None) -> None:
    entry = next(e for e in FIXTURES if e.model is model)
    data = copy.deepcopy(entry.data)
    data.update({DOMAIN_REVISION_FIELD[model]: revision, "supersedes": supersedes})
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_every_revision_record_has_a_revision_2_catalog_variant() -> None:
    covered = {e.model for e in CATALOG if e.name.endswith("/revision-2")}
    assert covered == set(DOMAIN_REVISION_FIELD)


# ---- S13: JSON Schema generation (export and consistency stay in P1.1-G) -----------------------


@pytest.mark.parametrize("model", TOP_LEVEL_RECORDS, ids=lambda m: m.__name__)
def test_json_schema_generates(model: type[BaseModel]) -> None:
    schema = model.model_json_schema()
    assert schema["type"] == "object"
    assert "schema_version" in schema["properties"]
