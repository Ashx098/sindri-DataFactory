"""Enforce the dependency direction in ARCHITECTURE_GUARDRAILS.md.

Statically parses every module under src/sindri and fails if a package imports a sindri package it
is forbidden to depend on. Changing FORBIDDEN requires an ADR and a matching guardrails update.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "sindri"

FORGES = {"task_forge", "spec_forge", "verification_forge"}
# Fixed from ARCHITECTURE_GUARDRAILS.md, not discovered from disk: packages are created only when a
# task needs them (anti-skeleton rule), and the rules must already bind when they appear.
ALL = {
    "core", "schemas", "evidence", "controller", "models", "context", "agents", "tools",
    *FORGES, "qualification", "solver", "triage", "judge", "release", "data", "training",
}

FORBIDDEN: dict[str, set[str]] = {
    "core": ALL - {"core"},
    "schemas": {"judge", "solver", "triage"} | FORGES,
    "evidence": {"agents", "models", "solver"},
    "controller": {"models", "agents"},
    "models": {"judge"},
    "tools": {"solver"},
    "context": {"judge"},
    "agents": {"judge"},
    **{forge: {"solver"} for forge in FORGES},
    "solver": {"judge"},
    "judge": {"solver", "triage"},
    "data": {"judge", "solver"},
    "training": {"judge"},
}


def _sindri_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            parts = name.split(".")
            if parts[0] == "sindri" and len(parts) > 1:
                found.add(parts[1])
    return found


@pytest.mark.parametrize("package", sorted(FORBIDDEN))
def test_package_respects_forbidden_dependencies(package: str) -> None:
    violations = []
    if not (SRC / package).is_dir():
        pytest.skip(f"sindri.{package} does not exist yet")
    for path in sorted((SRC / package).rglob("*.py")):
        bad = _sindri_imports(path) & FORBIDDEN[package]
        if bad:
            violations.append(f"{path.relative_to(SRC)} imports {sorted(bad)}")
    assert not violations, "\n".join(violations)


def test_every_package_is_governed() -> None:
    """A new package must be added to ALL (and the guardrails) before it can exist."""
    present = {p.name for p in SRC.iterdir() if (p / "__init__.py").exists()}
    assert present <= ALL, f"ungoverned packages: {sorted(present - ALL)}"


def test_relative_imports_do_not_escape_package() -> None:
    """Relative imports above the package root would bypass the check above."""
    offenders = []
    for path in SRC.rglob("*/*.py"):
        depth = len(path.relative_to(SRC).parts) - 1  # 1 for src/sindri/<pkg>/x.py
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level > depth:
                offenders.append(str(path.relative_to(SRC)))
    assert not offenders, offenders
