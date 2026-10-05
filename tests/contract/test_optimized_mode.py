"""P1.1-G B1/B2/G-O: targeted proof that fail-closed behaviour survives `python -O`.

Each check runs in a `python -O` subprocess, which also confirms that optimization is really on,
so the evidence is not vacuous. The full suite under `-O` is gate evidence only (run once in
P1.1-G), not a permanent CI pass.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_optimized(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-O", "-c", textwrap.dedent(code)],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )


def test_bypassed_bmc_report_fails_closed_under_optimization() -> None:
    result = _run_optimized("""
        import sys
        from sindri.schemas import FormalMode, FormalReport
        assert_off = sys.flags.optimize >= 1
        report = FormalReport.model_construct(
            report_kind="formal", mode=FormalMode.BMC, requested_depth=None, reached_depth=None,
            proof_closed=None, expected_property_ids=("p_a",), property_results=(),
        )
        try:
            report.bound_met()
        except RuntimeError as exc:
            print(f"optimize={assert_off} RuntimeError: {exc}")
        else:
            print(f"optimize={assert_off} NO ERROR")
    """)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "optimize=True RuntimeError: invalid FormalReport: BMC report missing depths"
    )


def test_support_helper_assertions_still_fire_under_optimization() -> None:
    result = _run_optimized("""
        import sys
        from sindri.schemas import InvariantCode
        from tests.contract.cross_record._case import Case, assert_isolated
        wrong = Case("expects a violation the positive bundle does not have",
                     InvariantCode.B1, 1, lambda spec: None)
        try:
            assert_isolated(wrong)
        except AssertionError:
            print(f"optimize={sys.flags.optimize >= 1} AssertionError")
        else:
            print(f"optimize={sys.flags.optimize >= 1} NO ERROR")
    """)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "optimize=True AssertionError"


def test_validated_reports_keep_their_bound_semantics() -> None:
    from sindri.schemas import FormalReport

    def bmc(requested: int, reached: int) -> FormalReport:
        return FormalReport.model_validate({
            "report_kind": "formal", "mode": "bmc", "requested_depth": requested,
            "reached_depth": reached, "proof_closed": None, "expected_property_ids": ["p_a"],
            "property_results": [],
        })

    assert bmc(24, 24).bound_met() is True
    assert bmc(24, 7).bound_met() is False
