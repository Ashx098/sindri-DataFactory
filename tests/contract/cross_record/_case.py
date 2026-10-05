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
    # Explicit raises, not `assert`: this support module is not rewritten by pytest, so a plain
    # assert would vanish under `python -O` (P1.1-G B2).
    if {v.code for v in found} != {case.code}:
        raise AssertionError(f"expected only {case.code.value}: {detail}")
    if len(found) != case.count:
        raise AssertionError(f"expected {case.count} x {case.code.value}: {detail}")


def ids(cases: list[Case]) -> list[str]:
    return [f"{c.code.value}:{c.name}" for c in cases]
