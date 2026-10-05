"""SIN-P1.1-008 S3, S10, S11, S17 and hash re-checks: what content identity is, and is not.

- S3: `content_id()` is `canonical_json_id(model_dump(mode="json"))`. Transport JSON is not the
  identity contract (it may differ today or coincide later; neither is asserted as an invariant).
- S10: JSON object key order never affects identity, both in the canonical encoder itself and
  after Pydantic parses transport JSON.
- S11: array/tuple order DOES affect exact record identity; specialized semantic hashes
  (`source_hash`, `assignment_key`) may intentionally ignore order.
- S17: no Unicode normalization; text is identity-bearing byte for byte.
"""

import copy
import hashlib
import json
import random
import unicodedata
from typing import Any

import pytest

from sindri.core.ids import canonical_json_id
from sindri.schemas import (
    CandidateFile,
    CandidateManifest,
    EpisodeBudget,
    EvaluationPolicy,
    Observation,
    Requirement,
    TaskManifest,
    candidate_source_hash,
)
from tests.contract._record_catalog import CATALOG, Entry, load, source_hash_of
from tests.contract.test_canonical_key_order import assert_key_order_invariant

ids = [e.name for e in CATALOG]


# ---- S3: the canonical identity contract -------------------------------------------------------


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_content_id_is_canonical_json_id_of_the_json_dump(entry: Entry) -> None:
    record = entry.build()
    assert record.content_id() == canonical_json_id(record.model_dump(mode="json"))  # type: ignore[attr-defined]


def test_content_id_independent_byte_level_vector() -> None:
    """Pins the identity encoding without going through canonical_json_id: sorted keys, compact
    separators, UTF-8. Catches any change of the encoding behind Record.content_id()."""
    raw = (
        b'{"limits":{"candidate_versions":12,"formal_ms":1800000,"repair_attempts":6,'
        b'"sim_jobs":40,"tokens":200000,"tool_calls":60},'
        b'"schema_version":1,"wall_clock_limit_ms":3600000}'
    )
    budget = EpisodeBudget.model_validate(load("episode_budget"))
    assert budget.content_id() == "sha256:" + hashlib.sha256(raw).hexdigest()


# ---- S10: mapping-key order and formatting never affect identity --------------------------------


def _permute_keys(value: Any, rng: random.Random) -> Any:
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {k: _permute_keys(value[k], rng) for k in keys}
    if isinstance(value, list):
        return [_permute_keys(v, rng) for v in value]  # array order preserved: it is identity
    return value


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
def test_canonical_encoding_ignores_mapping_key_order(entry: Entry) -> None:
    """S10 on the encoder itself over the whole catalog, before any model normalization
    (catalog-independent coverage: test_canonical_key_order.py)."""
    assert_key_order_invariant(entry.build().model_dump(mode="json"), entry.name)


@pytest.mark.parametrize("entry", CATALOG, ids=ids)
@pytest.mark.parametrize("seed", range(5))
def test_object_key_order_and_formatting_do_not_change_identity(entry: Entry, seed: int) -> None:
    record = entry.build()
    """Transport-JSON key order does not alter record meaning after Pydantic parsing."""
    rng = random.Random(seed)
    permuted = _permute_keys(record.model_dump(mode="json"), rng)
    text = json.dumps(permuted, indent=rng.choice([None, 1, 4]),
                      separators=rng.choice([(",", ":"), (", ", ": ")]))
    again = entry.model.model_validate_json(text)
    assert again.content_id() == record.content_id()  # type: ignore[attr-defined]
    assert again == record


# ---- S11: exact-record sequence order -----------------------------------------------------------


def test_candidate_files_order_changes_record_identity_not_source_identity() -> None:
    base = load("candidate_manifest")
    reordered = copy.deepcopy(base)
    reordered["files"] = list(reversed(base["files"]))
    a, b = CandidateManifest.model_validate(base), CandidateManifest.model_validate(reordered)
    assert a.source_hash == b.source_hash  # semantic file-set identity ignores order
    assert a.content_id() != b.content_id()  # exact manifest record identity does not


def test_requirement_ids_order_changes_record_identity() -> None:
    base = load("task_manifest")
    reordered = copy.deepcopy(base)
    reordered["requirement_ids"] = list(reversed(base["requirement_ids"]))
    assert (TaskManifest.model_validate(base).content_id()
            != TaskManifest.model_validate(reordered).content_id())


def test_assignment_key_is_order_independent_while_policy_identity_is_not() -> None:
    base = load("evaluation_policy")
    reordered = copy.deepcopy(base)
    for cfg in reordered["configurations"]:
        cfg["assignments"] = list(reversed(cfg["assignments"]))
    a, b = EvaluationPolicy.model_validate(base), EvaluationPolicy.model_validate(reordered)
    assert [c.assignment_key() for c in a.configurations] == [
        c.assignment_key() for c in b.configurations
    ]
    assert a.content_id() != b.content_id()


# ---- hash constructions re-checked after a round trip -------------------------------------------


@pytest.mark.parametrize("entry", [e for e in CATALOG if e.model is CandidateManifest],
                         ids=lambda e: e.name)
def test_candidate_source_hash_still_recomputes_after_round_trip(entry: Entry) -> None:
    again = CandidateManifest.model_validate_json(entry.build().model_dump_json())
    assert again.source_hash == candidate_source_hash(again.files)
    assert again.source_hash == source_hash_of(entry.data["files"])


@pytest.mark.parametrize("entry", [e for e in CATALOG if e.model is Observation],
                         ids=lambda e: e.name)
def test_observation_execution_key_still_recomputes_after_round_trip(entry: Entry) -> None:
    again = Observation.model_validate_json(entry.build().model_dump_json())
    assert again.execution_key == again.computed_execution_key()


def test_candidate_file_set_construction_is_unchanged() -> None:
    files = [CandidateFile.model_validate({"path": "rtl/a.sv", "hash": "sha256:" + "4f" * 32})]
    raw = (
        b'{"files":[{"hash":"sha256:' + b"4f" * 32
        + b'","path":"rtl/a.sv"}],"kind":"candidate_file_set_v1"}'
    )
    assert candidate_source_hash(files) == "sha256:" + hashlib.sha256(raw).hexdigest()


# ---- S17: no Unicode normalization ---------------------------------------------------------------


def test_unicode_is_preserved_verbatim_and_identity_bearing() -> None:
    nfc = unicodedata.normalize("NFC", "data must stay stable — café")
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd
    base = load("requirement")
    a = Requirement.model_validate({**base, "original_text": nfc})
    b = Requirement.model_validate({**base, "original_text": nfd})
    assert Requirement.model_validate_json(a.model_dump_json()).original_text == nfc
    assert Requirement.model_validate_json(b.model_dump_json()).original_text == nfd
    assert a.content_id() != b.content_id()
