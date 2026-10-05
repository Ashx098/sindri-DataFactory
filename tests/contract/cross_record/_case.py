"""Negative-case plumbing shared by the cross-record test modules and the rule-removal harness."""

from collections.abc import Callable
from dataclasses import dataclass

from sindri.schemas import InvariantCode, Violation, check_records
from tests.contract.cross_record._bundle import Spec, positive_spec, records


@dataclass(frozen=True)
class Case:
    """One isolated negative mutation: exactly `count` violations, all of `code`."""

    name: str
    code: InvariantCode
    count: int
    mutate: Callable[[Spec], None]

    def spec(self) -> Spec:
        spec = positive_spec()
        self.mutate(spec)
        return spec


def violations(case: Case) -> tuple[Violation, ...]:
    return check_records(records(case.spec()))


def assert_isolated(case: Case) -> None:
    found = violations(case)
    detail = [f"{v.code.value} {v.subject}: {v.detail}" for v in found]
    assert {v.code for v in found} == {case.code}, detail
    assert len(found) == case.count, detail


def ids(cases: list[Case]) -> list[str]:
    return [f"{c.code.value}:{c.name}" for c in cases]
