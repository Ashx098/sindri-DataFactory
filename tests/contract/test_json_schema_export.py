"""P1.1-G A4/B4: checked-in JSON Schemas are deterministically generated from the current models.

The schemas are a structural projection; the Pydantic models remain the validation authority
(G-JS). This test proves only that the checked-in bytes are what the pinned exporter generates
from today's models, and that each file is self-contained. It deliberately does not pin today's
fidelity gaps, so later schema enrichment stays possible.
"""

import importlib.util
import json
from pathlib import Path
from typing import Any

import sindri.schemas as schemas
from sindri.schemas._base import Record

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "schemas" / "json" / "v1"


def _exporter() -> Any:
    spec = importlib.util.spec_from_file_location("export_json_schemas",
                                                  ROOT / "scripts" / "export_json_schemas.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _records() -> set[str]:
    return {n for n in schemas.__all__
            if isinstance(getattr(schemas, n), type) and issubclass(getattr(schemas, n), Record)}


def test_one_schema_per_top_level_record() -> None:
    assert len(_records()) == 9
    assert {p.name for p in OUT.glob("*.schema.json")} == {f"{n}.schema.json" for n in _records()}


def test_checked_in_bytes_equal_regeneration() -> None:
    generated = _exporter().generate()
    on_disk = {p.name: p.read_bytes() for p in OUT.glob("*.schema.json")}
    assert on_disk == generated


def test_generation_is_deterministic() -> None:
    exporter = _exporter()
    assert exporter.generate() == exporter.generate()


def _refs(node: Any) -> list[str]:
    if isinstance(node, dict):
        own = [node["$ref"]] if isinstance(node.get("$ref"), str) else []
        return own + [r for v in node.values() for r in _refs(v)]
    if isinstance(node, list):
        return [r for v in node for r in _refs(v)]
    return []


def test_each_schema_is_self_contained_with_nested_defs() -> None:
    for path in sorted(OUT.glob("*.schema.json")):
        schema = json.loads(path.read_text())
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object" and "schema_version" in schema["properties"]
        defs = schema.get("$defs", {})
        assert defs, f"{path.name}: nested models are expected under $defs"
        for ref in _refs(schema):
            assert ref.startswith("#/$defs/") and ref.removeprefix("#/$defs/") in defs, (
                path.name, ref)
