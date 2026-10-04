"""Typed identifiers and canonical content hashing.

Every result binds to the exact artifact it was produced from (master architecture §4 principle 9),
so identity is either a content hash (`ContentId`) or a typed domain ID. Domain ID formats follow
the master architecture §20 examples:

    TaskId         pktfr_0193           CandidateId    c_pktfr_0193_e17_v3
    ObservationId  ob_88121             EpisodeId      e17
    RequirementId  R17                  PolicyId       ep_fifo_004
    FindingId      F42                  ContentId      sha256:<64 hex>
    FamilyId       stream-framing       LineageId      pktfr
    VariantId      maxlen4-64_datasheet ContractId     ct_pktfr_0193_v3

    ObligationId   sim_stall_01         CheckId        chk_formal_core
    ConfigurationId cfg_w8_d8           ToolProfileId  tp_sby_bmc_v0
    ExceptionId    ex_formal_w32        TestId         stall_stability_004
    PropertyId     R03_sva              JobId          job_771

(Family, lineage, variant and contract IDs were added by SIN-P1.1-002, decision D2; obligation,
check, configuration, tool-profile and exception IDs by SIN-P1.1-003 for EvaluationPolicy; test and
property IDs by SIN-P1.1-005 for Observation execution reports; job IDs by SIN-P1.1-007 for
EpisodeState pending jobs. Earlier
types and patterns are frozen.)

Each ID type is a distinct `str` subclass that validates on construction, so a malformed value
cannot exist and mypy rejects passing one kind of ID where another is expected.
"""

import hashlib
import json
import re
from typing import Any, ClassVar, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class _TypedId(str):
    """Base for validated identifier strings. Subclasses set PATTERN."""

    __slots__ = ()
    PATTERN: ClassVar[re.Pattern[str]]

    def __new__(cls, value: str) -> Self:
        if type(value) is cls:
            return value
        if not isinstance(value, str):
            raise TypeError(f"{cls.__name__} must be built from str, got {type(value).__name__}")
        if not cls.PATTERN.fullmatch(value):
            raise ValueError(f"invalid {cls.__name__}: {value!r} (expected {cls.PATTERN.pattern})")
        return super().__new__(cls, value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str.__repr__(self)})"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Let Pydantic records use these types directly: validate, then serialize as plain str."""
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(strict=True),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )


_SLUG = r"[a-z0-9]+(?:_[a-z0-9]+)*"


class TaskId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


class CandidateId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"c_{_SLUG}")


class ObservationId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(r"ob_[0-9a-z]+")


class EpisodeId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(r"e[0-9]+")


class RequirementId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(r"R[0-9]+")


class PolicyId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"ep_{_SLUG}")


class FindingId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(r"F[0-9]+")


_HYPHEN_SLUG = r"[a-z0-9]+(?:[-_][a-z0-9]+)*"


class FamilyId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(_HYPHEN_SLUG)


class LineageId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(_HYPHEN_SLUG)


class VariantId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(_HYPHEN_SLUG)


class ContractId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"ct_{_SLUG}")


class ObligationId(_TypedId):
    """Master §20.9 examples: `sim_stall_01`, `sva_stall_stable` (ADR-0004)."""

    __slots__ = ()
    PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


class CheckId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"chk_{_SLUG}")


class ConfigurationId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"cfg_{_SLUG}")


class ToolProfileId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"tp_{_SLUG}")


class ExceptionId(_TypedId):
    __slots__ = ()
    PATTERN = re.compile(rf"ex_{_SLUG}")


class TestId(_TypedId):
    """Master §20.6 example: `stall_stability_004`."""

    __slots__ = ()
    PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


class PropertyId(_TypedId):
    """Master §20.4 example: `R03_sva` (property names may carry requirement-style capitals)."""

    __slots__ = ()
    PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*")


class JobId(_TypedId):
    """Master §20.11 example: `job_771` (an asynchronous controller job)."""

    __slots__ = ()
    PATTERN = re.compile(rf"job_{_SLUG}")


class ContentId(_TypedId):
    """SHA-256 content identity: ``sha256:`` followed by 64 lowercase hex digits."""

    __slots__ = ()
    PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def content_id(data: bytes) -> ContentId:
    """Identity of exact bytes. Any changed byte yields a different ID."""
    if not isinstance(data, bytes | bytearray | memoryview):
        raise TypeError(f"content_id needs bytes, got {type(data).__name__}")
    return ContentId("sha256:" + hashlib.sha256(data).hexdigest())


def canonical_json_bytes(obj: Any) -> bytes:
    """Canonical JSON encoding: sorted keys, no insignificant whitespace, UTF-8.

    Only JSON-native values are accepted (dict with str keys, list, str, int, float, bool, None).
    Anything the json module would silently convert is rejected instead, because silent conversion
    makes different values share an ID: non-str dict keys (``{1: x}`` would equal ``{"1": x}``),
    tuples, sets, NaN and infinities. Values keep their JSON type: ``1``, ``1.0`` and ``True``
    encode differently and therefore have different IDs.
    """
    _require_json_native(obj, "$")
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_id(obj: Any) -> ContentId:
    """Identity of a JSON value, independent of key order and formatting."""
    return content_id(canonical_json_bytes(obj))


def _require_json_native(obj: Any, path: str) -> None:
    if obj is None or isinstance(obj, str | bool | int | float):
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _require_json_native(item, f"{path}[{i}]")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(f"{path}: JSON object keys must be str, got {type(key).__name__}")
            _require_json_native(value, f"{path}.{key}")
        return
    raise TypeError(f"{path}: {type(obj).__name__} is not a JSON-native value")
