"""Shared base for boundary records (master architecture ch. 20; SIN-P1.1-002 decisions).

Every record and every nested model is:
- closed: unknown fields are rejected at any depth;
- immutable: attribute assignment raises, and collections are tuples, never lists or dicts;
- float-free: a binary float anywhere in the input is rejected (decision D5), because floats have
  no exact canonical form and these records carry identity. Exact fractions, when a later record
  needs them, use an exact representation (decimal string, scaled integer or rational schema);
- coercion-free for scalars: identity-bearing scalars use Pydantic strict types, so `True`, `1`,
  `"1"` and `1.0` never turn into one another (decision C6).
"""

from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

from sindri.core.ids import ContentId, canonical_json_id

# Exact JSON scalars for authoritative values (C4/C6): no float, no Any, no cross-type coercion.
ExactScalar = StrictInt | StrictStr | StrictBool


def _require_text(value: str) -> str:
    """Non-empty and not whitespace-only. The value is kept verbatim (never stripped)."""
    if not value.strip():
        raise ValueError("must contain non-whitespace text")
    return value


NonEmptyText = Annotated[StrictStr, AfterValidator(_require_text)]
PositiveVersion = Annotated[StrictInt, Field(ge=1)]


def _reject_floats(value: Any, path: str) -> None:
    if isinstance(value, float):
        raise ValueError(f"{path}: binary floats are not allowed in records (decision D5)")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for i, item in enumerate(value):
            _reject_floats(item, f"{path}[{i}]")


class StrictModel(BaseModel):
    """Closed, immutable, float-free model. Base for records and their nested parts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _no_binary_floats(cls, data: Any) -> Any:
        _reject_floats(data, "$")
        return data


def _schema_version_1(value: int) -> int:
    if value != 1:
        raise ValueError("unsupported schema_version; this code reads version 1 only")
    return value


class Record(StrictModel):
    """A top-level, versioned boundary record.

    `schema_version` is a StrictInt pinned to 1 rather than `Literal[1]`: Pydantic's Literal
    accepts `True` and `1.0` as `1`, which would let a malformed record through.
    """

    schema_version: Annotated[StrictInt, AfterValidator(_schema_version_1)]

    def content_id(self) -> ContentId:
        """Canonical identity of this exact record (key order and formatting independent)."""
        return canonical_json_id(self.model_dump(mode="json"))


def check_version_chain(version: int, supersedes: ContentId | None, what: str) -> None:
    """First version has no predecessor; every later version names exactly one."""
    if version == 1 and supersedes is not None:
        raise ValueError(f"{what} version 1 must not supersede anything")
    if version > 1 and supersedes is None:
        raise ValueError(f"{what} version {version} must name the version it supersedes")
