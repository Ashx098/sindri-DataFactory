"""SIN-P1.1-009 rule-removal harness: the exhaustive load-bearing proof for every runtime code.

For each `InvariantCode`, running with exactly that rule removed must make at least one of its
isolated negative fixtures clean, and must leave the positive bundle clean. Contract tests (CT-*)
are not runtime codes and are not in the registry.
"""

import pytest

from sindri.schemas import InvariantCode
from sindri.schemas.cross_record import RULES, run_rules
from tests.contract.cross_record import (
    test_bundle_integrity,
    test_candidate_bindings,
    test_episode_chains,
    test_finding_bindings,
    test_observation_bindings,
    test_policy_coverage,
    test_revision_chains,
)
from tests.contract.cross_record._bundle import positive_spec, records
from tests.contract.cross_record._case import Case

ALL_CASES: list[Case] = [
    *test_bundle_integrity.CASES,
    *test_revision_chains.CASES,
    *test_policy_coverage.CASES,
    *test_candidate_bindings.CASES,
    *test_observation_bindings.CASES,
    *test_finding_bindings.CASES,
    *test_episode_chains.CASES,
]


def test_registry_covers_exactly_the_runtime_codes() -> None:
    assert set(RULES) == set(InvariantCode)
    assert not {"XR-B3", "XR-C2", "XR-T1"} & {c.value for c in InvariantCode}


def test_every_runtime_code_has_an_isolated_negative_case() -> None:
    assert {c.code for c in ALL_CASES} == set(InvariantCode)


@pytest.mark.parametrize("code", list(InvariantCode), ids=lambda c: c.value)
def test_removing_a_rule_silences_its_negative_case(code: InvariantCode) -> None:
    without = {k: rule for k, rule in RULES.items() if k is not code}
    cases = [c for c in ALL_CASES if c.code is code]
    silenced = [c.name for c in cases if run_rules(records(c.spec()), without) == ()]
    assert silenced, f"no {code.value} negative case becomes clean without its rule"
    assert run_rules(records(positive_spec()), without) == ()
