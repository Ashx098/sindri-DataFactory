"""P1.1-G B1/B2 guard: no `assert` statement where `python -O` would silently remove it.

`python -O` strips `assert`. Production code under `src/` must express every semantic check
explicitly, and so must test *support* modules (`tests/**/_*.py`): pytest rewrites asserts only in
test modules, so a helper's assert would vanish under `-O` and its callers would pass vacuously.
Ordinary assertions in `test_*.py` bodies are rewritten by pytest and may stay.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _asserts(path: Path, root: Path = ROOT) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [f"{path.relative_to(root)}:{n.lineno}" for n in ast.walk(tree)
            if isinstance(n, ast.Assert)]


def _support_modules() -> list[Path]:
    return sorted(p for p in (ROOT / "tests").rglob("_*.py") if p.name != "__init__.py")


def test_no_assert_in_production_code() -> None:
    found = [hit for p in sorted((ROOT / "src").rglob("*.py")) for hit in _asserts(p)]
    assert found == [], found


def test_no_assert_in_test_support_modules() -> None:
    modules = _support_modules()
    assert modules, "expected support modules such as tests/contract/_record_catalog.py"
    found = [hit for p in modules for hit in _asserts(p)]
    assert found == [], found


def test_the_guard_detects_an_assert(tmp_path: Path) -> None:
    sample = tmp_path / "_helper.py"
    sample.write_text("def f(x):\n    assert x\n")
    assert _asserts(sample, tmp_path) == ["_helper.py:2"]
