"""F7 result-protocol verdict for the FIFO engineering seed (SIN-P1.6-001).

Test-support code only: it pins the protocol the seed testbench speaks, so the kill matrix can be
reproduced without trusting exit codes. The production normalizer is P1.4's job and must implement
at least these rules. It uses no `assert` (P1.1-G B2 guard).

Verdicts:
- PASS: every expected TEST exactly once and PASS; no unexpected or duplicate id; exactly one
  terminal RESULT; RESULT agrees.
- FAIL: a well-formed transcript reporting a failure (some TEST FAIL, RESULT FAIL, consistent).
- INVALID: anything else (missing, duplicate or unexpected test; no RESULT or several; RESULT not
  terminal; RESULT disagreeing with the tests). INVALID is never PASS: it fails closed.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

TEST_LINE = re.compile(r"^TEST (\S+) (PASS|FAIL)$")
RESULT_LINE = re.compile(r"^RESULT (PASS|FAIL)$")


@dataclass(frozen=True)
class Verdict:
    status: str  # "PASS" | "FAIL" | "INVALID"
    reasons: tuple[str, ...] = field(default=())


def verdict(transcript: str, expected: Iterable[str]) -> Verdict:
    expected_ids = list(expected)
    seen: dict[str, list[str]] = {}
    results: list[tuple[int, str]] = []
    last_test_line = -1
    for n, raw in enumerate(transcript.splitlines()):
        line = raw.strip()
        if m := TEST_LINE.match(line):
            seen.setdefault(m.group(1), []).append(m.group(2))
            last_test_line = n
        elif m := RESULT_LINE.match(line):
            results.append((n, m.group(1)))

    problems = []
    missing = [t for t in expected_ids if t not in seen]
    unexpected = sorted(t for t in seen if t not in expected_ids)
    duplicated = sorted(t for t, v in seen.items() if len(v) > 1)
    if missing:
        problems.append(f"missing tests {missing}")
    if unexpected:
        problems.append(f"unexpected tests {unexpected}")
    if duplicated:
        problems.append(f"duplicated tests {duplicated}")
    if len(results) != 1:
        problems.append(f"expected exactly one RESULT line, found {len(results)}")
    elif results[0][0] < last_test_line:
        problems.append("RESULT is not terminal (TEST lines follow it)")
    if problems:
        return Verdict("INVALID", tuple(problems))

    any_fail = any(v[0] == "FAIL" for v in seen.values())
    result = results[0][1]
    if (result == "PASS") == any_fail:
        return Verdict("INVALID", (f"RESULT {result} disagrees with per-test results",))
    return Verdict("PASS" if result == "PASS" else "FAIL")
