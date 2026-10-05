"""P1.1-G A3: the public schema API inventory matches the code.

Every public class or function defined in a `sindri.schemas.*` module is exported from
`sindri.schemas` (possibly under another name), or is on the explicit private allow-list.
`__all__` has no stale names, and its top-level Records are exactly the P1.1 record set.
"""

import importlib
import inspect
import pkgutil

import sindri.schemas as schemas
from sindri.schemas._base import Record

# G-R: harness-only implementation detail, deliberately not public API.
PRIVATE_ALLOWLIST = {"sindri.schemas.cross_record.run_rules"}
P1_1_RECORDS = {
    "TaskManifest", "Requirement", "EvaluationPolicy", "CandidateManifest", "Observation",
    "Finding", "FindingTransition", "EpisodeBudget", "EpisodeState",
}


def _modules() -> list[str]:
    return sorted(f"sindri.schemas.{m.name}" for m in pkgutil.iter_modules(schemas.__path__)
                  if not m.name.startswith("_"))


def test_all_has_no_stale_or_duplicate_names() -> None:
    assert len(schemas.__all__) == len(set(schemas.__all__))
    missing = [n for n in schemas.__all__ if not hasattr(schemas, n)]
    assert missing == []


def test_every_public_class_and_function_is_exported_or_allowlisted() -> None:
    exported = {id(getattr(schemas, n)) for n in schemas.__all__}
    unexported = []
    for name in _modules():
        module = importlib.import_module(name)
        for attr, obj in vars(module).items():
            if attr.startswith("_") or not (inspect.isclass(obj) or inspect.isfunction(obj)):
                continue
            if getattr(obj, "__module__", None) != name:
                continue  # imported from elsewhere
            if id(obj) not in exported and f"{name}.{attr}" not in PRIVATE_ALLOWLIST:
                unexported.append(f"{name}.{attr}")
    assert unexported == []


def test_allowlisted_names_exist_and_stay_private() -> None:
    for dotted in PRIVATE_ALLOWLIST:
        module, attr = dotted.rsplit(".", 1)
        assert hasattr(importlib.import_module(module), attr), dotted
        assert attr not in schemas.__all__, dotted


def test_top_level_records_are_exactly_the_p1_1_set() -> None:
    records = {n for n in schemas.__all__
               if isinstance(getattr(schemas, n), type) and issubclass(getattr(schemas, n), Record)}
    assert records == P1_1_RECORDS
