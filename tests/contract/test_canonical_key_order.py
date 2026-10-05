"""SIN-P1.1-008 S10 on the canonical encoder itself: mapping-key order never reaches identity bytes.

Deliberately independent of the record catalog and of model validation: the catalog validates
pinned hashes at import, so a broken encoder would only surface there as collection errors. These
tests run on raw JSON-native data and fail on their own.
"""

import json
import random
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from sindri.core.ids import canonical_json_bytes, canonical_json_id

EXAMPLES = Path(__file__).parent / "examples"
example_names = sorted(p.stem for p in EXAMPLES.glob("*.json"))


def reverse_keys(value: Any) -> Any:
    """Deterministic: every mapping with more than one key is guaranteed to be reordered."""
    if isinstance(value, dict):
        return {k: reverse_keys(value[k]) for k in reversed(list(value))}
    if isinstance(value, list):
        return [reverse_keys(v) for v in value]
    return value


def permute_keys(value: Any, rng: random.Random) -> Any:
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {k: permute_keys(value[k], rng) for k in keys}
    if isinstance(value, list):
        return [permute_keys(v, rng) for v in value]  # array order preserved: it is identity
    return value


def key_orders(value: Any) -> list[list[str]]:
    """Key order of every mapping, depth-first, for asserting that a permutation took effect."""
    if isinstance(value, dict):
        return [list(value)] + [o for v in value.values() for o in key_orders(v)]
    if isinstance(value, list):
        return [o for v in value for o in key_orders(v)]
    return []


def assert_key_order_invariant(original: Any, seed: object) -> None:
    rng = random.Random(str(seed))
    permutations = [reverse_keys(original)] + [permute_keys(original, rng) for _ in range(5)]
    for before, after in zip(key_orders(original), key_orders(permutations[0]), strict=True):
        assert len(before) < 2 or before != after  # the reversal really reordered every mapping
    for permuted in permutations:
        assert permuted == original  # same mapping content, different insertion order
        assert canonical_json_bytes(permuted) == canonical_json_bytes(original)
        assert canonical_json_id(permuted) == canonical_json_id(original)


def test_examples_exist() -> None:
    assert len(example_names) >= 9


@pytest.mark.parametrize("name", example_names)
def test_canonical_encoding_of_raw_fixtures_ignores_mapping_key_order(name: str) -> None:
    assert_key_order_invariant(json.loads((EXAMPLES / f"{name}.json").read_text()), name)


def test_canonical_encoding_sorts_nested_mapping_keys() -> None:
    nested = {"b": {"z": 1, "a": [{"y": True, "x": None}]}, "a": "v"}
    assert canonical_json_bytes(nested) == b'{"a":"v","b":{"a":[{"x":null,"y":true}],"z":1}}'
    assert canonical_json_bytes(reverse_keys(nested)) == canonical_json_bytes(nested)


json_native = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=8),
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=6), inner,
                                                                 max_size=5),
    max_leaves=25,
)


@given(st.dictionaries(st.text(max_size=6), json_native, min_size=2, max_size=6),
       st.integers(0, 2**32))
def test_canonical_encoding_ignores_key_order_for_any_json_object(
        value: dict[str, Any], seed: int) -> None:
    assert_key_order_invariant(value, seed)
