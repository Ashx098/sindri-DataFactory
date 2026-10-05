"""Export the JSON Schemas of the P1.1 top-level records (P1.1-G B4, G-JS).

The schemas are a deterministic *structural projection* generated from the Pydantic models, which
remain the only validation authority. Cross-field and model-level validators, typed-ID patterns and
other semantics are not representable or not projected (see components/schemas.yaml). One file per
top-level record; nested models live under `$defs` in the same file.

    uv run python scripts/export_json_schemas.py          # (re)write schemas/json/v1/
    uv run python scripts/export_json_schemas.py --check  # exit 1 if checked-in output drifted
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schemas" / "json" / "v1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"


def generate() -> dict[str, bytes]:
    """File name -> exact bytes, for every top-level P1.1 record."""
    import sindri.schemas as schemas
    from sindri.schemas._base import Record

    records = sorted(
        (getattr(schemas, n) for n in schemas.__all__),
        key=lambda o: getattr(o, "__name__", ""),
    )
    out: dict[str, bytes] = {}
    for model in records:
        if not (isinstance(model, type) and issubclass(model, Record)):
            continue
        schema = {"$schema": DIALECT, **model.model_json_schema(mode="validation")}
        text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        out[f"{model.__name__}.schema.json"] = text.encode("utf-8")
    return out


def main(argv: list[str]) -> int:
    generated = generate()
    if "--check" in argv:
        on_disk = {p.name: p.read_bytes() for p in OUT.glob("*.schema.json")}
        if on_disk != generated:
            drift = sorted(set(on_disk) ^ set(generated)) + sorted(
                n for n in set(on_disk) & set(generated) if on_disk[n] != generated[n]
            )
            print(f"JSON Schema drift in {OUT.relative_to(ROOT)}: {drift}", file=sys.stderr)
            return 1
        print(f"{len(generated)} schemas match {OUT.relative_to(ROOT)}")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.schema.json"):
        if stale.name not in generated:
            stale.unlink()
    for name, data in generated.items():
        (OUT / name).write_bytes(data)
    print(f"wrote {len(generated)} schemas to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
