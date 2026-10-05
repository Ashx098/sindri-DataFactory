"""SIN-P1.1-008 S8, S9: after JSON parsing, no float and no coerced scalar becomes record state.

Driven by a walker over every leaf of every catalog entry rather than hand-picked samples.
`ExactScalar` positions (requirement parameter values, policy configuration assignment values)
are the one intentional exception to S9: there, JSON true, 1 and "1" are three distinct valid
values (and they must stay distinct after the round trip).

S9 requires a strict-scalar error *at the mutated field*: a record-level invariant (e.g. the
Observation execution-key check) rejecting the record is a second line of defence, not evidence
that the field itself stayed strict. JSON floats are covered by S8's exact-path assertion.
"""

import copy
import inspect
import json
import math
import re
from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import ValidationError

import sindri.schemas as schemas_pkg
from sindri.schemas import Requirement
from tests.contract._record_catalog import CATALOG, Entry

ids = [e.name for e in CATALOG]
EXACT_SCALAR_PATH = re.compile(r"(\.parameters\[\d+\]\.values\[\d+\]|\.assignments\[\d+\]\.value)$")
Path = tuple[str | int, ...]
DISCRIMINATORS = ("kind", "report_kind", "proposal_kind")  # every Field(discriminator=...) in P1.1


def leaves(value: Any, path: Path = ()) -> Iterator[tuple[Path, Any]]:
    if isinstance(value, dict):
        for k, v in value.items():
            yield from leaves(v, (*path, k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from leaves(v, (*path, i))
    else:
        yield path, value


def json_path(path: Path) -> str:
    """The path syntax the records' float walker reports: $.key[index]."""
    return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in path)


def replaced(data: Any, path: Path, value: Any) -> Any:
    out = copy.deepcopy(data)
    target = out
    for p in path[:-1]:
        target = target[p]
    target[path[-1]] = value
    return out


def rejected(entry: Entry, data: Any) -> ValidationError | None:
    try:
        entry.model.model_validate_json(json.dumps(data))
    except ValidationError as exc:
        return exc
    return None


def at_field(loc: tuple[str | int, ...], path: Path, data: Any) -> bool:
    """True if a Pydantic error location names exactly the mutated JSON field.

    Discriminated unions insert the selected tag into `loc` (e.g. `execution_report.formal.
    requested_depth`); such an element is skipped only when it equals the discriminator value
    carried by the mapping at that point (it may also be a field name, e.g. ModelProducer.model).
    """
    i = 0
    node = data
    for step in loc:
        if i < len(path) and step == path[i]:
            node = node[step]
            i += 1
        elif isinstance(node, dict) and any(node.get(d) == step for d in DISCRIMINATORS):
            continue
        else:
            return False
    return i == len(path)


def field_errors(exc: ValidationError, path: Path, data: Any) -> list[str]:
    return [e["type"] for e in exc.errors() if at_field(tuple(e["loc"]), path, data)]


# ---- S8: floats, NaN and Infinity at every depth -----------------------------------------------


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_a_float_at_any_leaf_is_rejected_with_its_exact_path(entry: Entry) -> None:
    dumped = entry.build().model_dump(mode="json")
    checked = 0
    for path, _ in leaves(dumped):
        exc = rejected(entry, replaced(dumped, path, 1.5))
        assert exc is not None, json_path(path)
        assert any(f"{json_path(path)}: binary floats" in e["msg"] for e in exc.errors()), (
            json_path(path), exc.errors()[:2])
        checked += 1
    assert checked > 5


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
@pytest.mark.parametrize("token", [math.nan, math.inf, -math.inf])
def test_nan_and_infinity_tokens_are_rejected(entry: Entry, token: float) -> None:
    """Pydantic's JSON parser admits these tokens; the records must still reject them."""
    dumped = entry.build().model_dump(mode="json")
    ints = [(p, v) for p, v in leaves(dumped) if type(v) is int]
    for path, _ in ints:
        exc = rejected(entry, replaced(dumped, path, token))  # json.dumps emits NaN/Infinity
        assert exc is not None, json_path(path)
        assert any("binary floats" in e["msg"] for e in exc.errors())


# ---- S9: strict scalars after JSON ---------------------------------------------------------------


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_authoritative_ints_reject_bool_float_and_numeric_strings(entry: Entry) -> None:
    dumped = entry.build().model_dump(mode="json")
    for path, value in leaves(dumped):
        if type(value) is not int or EXACT_SCALAR_PATH.search(json_path(path)):
            continue
        for wrong in (True, str(value)):
            mutated = replaced(dumped, path, wrong)
            exc = rejected(entry, mutated)
            assert exc is not None, (json_path(path), wrong)
            assert "int_type" in field_errors(exc, path, mutated), (
                json_path(path), wrong, exc.errors()[:2])


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_authoritative_bools_reject_ints_and_strings(entry: Entry) -> None:
    dumped = entry.build().model_dump(mode="json")
    for path, value in leaves(dumped):
        if type(value) is not bool or EXACT_SCALAR_PATH.search(json_path(path)):
            continue
        for wrong in (1, 0, "true"):
            mutated = replaced(dumped, path, wrong)
            exc = rejected(entry, mutated)
            assert exc is not None, (json_path(path), wrong)
            assert "bool_type" in field_errors(exc, path, mutated), (
                json_path(path), wrong, exc.errors()[:2])


def test_field_location_matching_is_exact() -> None:
    data = {"report": {"kind": "formal", "depth": 3, "kinds": ["formal"]}, "depth": 1}
    path: Path = ("report", "depth")
    assert at_field(("report", "formal", "depth"), path, data)  # union tag skipped
    assert at_field(("report", "depth"), path, data)
    assert not at_field(("depth",), path, data)  # a different field
    assert not at_field(("report",), path, data)  # record/parent-level error
    assert not at_field(("report", "sim", "depth"), path, data)  # not this mapping's tag
    assert not at_field(("report", "depth", "x"), path, data)
    producer = {"producer": {"kind": "model", "model": "m", "training_allowed": 1}}
    assert at_field(("producer", "model", "training_allowed"), ("producer", "training_allowed"),
                    producer)  # tag value that is also a field name


def test_discriminator_inventory_is_complete() -> None:
    src = "".join(inspect.getsource(m) for m in vars(schemas_pkg).values()
                  if inspect.ismodule(m) and m.__name__.startswith("sindri.schemas."))
    assert set(re.findall(r'discriminator="(\w+)"', src)) == set(DISCRIMINATORS)


def test_the_walkers_see_ints_and_bools() -> None:
    kinds = {type(v) for e in CATALOG for _, v in leaves(e.build().model_dump(mode="json"))}
    assert {int, bool, str, type(None)} <= kinds


def test_exact_scalar_positions_keep_bool_int_and_string_distinct() -> None:
    entry = next(e for e in CATALOG if e.name == "Requirement/exact-scalars")
    again = Requirement.model_validate_json(entry.build().model_dump_json())
    assert again.applicability.kind == "parameter_scope"
    values = again.applicability.parameters[0].values
    assert values == (True, 1, "1") and [type(v) for v in values] == [bool, int, str]
