"""Cross-record invariants over a closed validation bundle (SIN-P1.1-009).

`check_records` takes a deliberately assembled, **closed** set of already-valid P1.1 records and
returns every violation of the cross-record rules deferred by SIN-P1.1-002…008, sorted
deterministically. It is pure: no I/O, store, clock or mutation of its inputs. It is not a query
over a partial store. Every reference to a P1.1 record type must resolve inside the bundle, and
store-global questions (completeness, global uniqueness, the global current head) belong to P1.2.

Reporting is aggregate with explicit owners (X3): an ambiguous logical key (XR-B1) or a broken
hash reference (XR-B2) is reported once, and every rule that would have to read through it skips
it. The dependency ordering is documented per rule and in the task packet. A *set head* is a
revision that no same-chain revision in the bundle supersedes.

This module imports the concrete schema modules directly (never `sindri.schemas`) so the package
can re-export the public API without an import cycle.
"""

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping
from enum import StrEnum, unique
from typing import Any, TypeVar, cast

from pydantic import StrictStr

from sindri.core.status import ToolStatus
from sindri.schemas._base import ExactScalar, Record, StrictModel
from sindri.schemas.candidate import CandidateManifest
from sindri.schemas.episode import (
    ALLOWED_EPISODE_TRANSITIONS,
    TERMINAL_EPISODE_STATES,
    AbortReason,
    BudgetVector,
    CandidateBinding,
    EpisodeBudget,
    EpisodeState,
    EpisodeStatus,
)
from sindri.schemas.finding import (
    DECIDED_FINDING_STATUSES,
    TERMINAL_FINDING_STATUSES,
    DevelopmentProbeRequest,
    ExistingPolicyCheck,
    Finding,
    FindingStatus,
    FindingTransition,
)
from sindri.schemas.finding import ProducerRole as FindingRole
from sindri.schemas.observation import Observation
from sindri.schemas.policy import CheckKind, Configuration, EvaluationPolicy, Visibility
from sindri.schemas.requirement import (
    AllSupportedConfigs,
    Requirement,
    RequirementDisposition,
)
from sindri.schemas.task import READ_ONLY_TASK_TYPES, MutationSource, TaskManifest


@unique
class InvariantCode(StrEnum):
    """Runtime cross-record invariants. Contract tests (CT-*) are deliberately not codes."""

    B1 = "XR-B1"
    B2 = "XR-B2"
    C1 = "XR-C1"
    C3 = "XR-C3"
    C4 = "XR-C4"
    C5 = "XR-C5"
    C6 = "XR-C6"
    C7 = "XR-C7"
    C8 = "XR-C8"
    P1 = "XR-P1"
    P2A = "XR-P2A"
    P2B = "XR-P2B"
    P3 = "XR-P3"
    P4 = "XR-P4"
    P5 = "XR-P5"
    P6 = "XR-P6"
    P7 = "XR-P7"
    P8 = "XR-P8"
    K1 = "XR-K1"
    K2 = "XR-K2"
    K3 = "XR-K3"
    K4 = "XR-K4"
    K5 = "XR-K5"
    K6 = "XR-K6"
    O1 = "XR-O1"
    O2 = "XR-O2"
    O3 = "XR-O3"
    O4 = "XR-O4"
    F1 = "XR-F1"
    F2 = "XR-F2"
    F3 = "XR-F3"
    F4 = "XR-F4"
    F5 = "XR-F5"
    F6 = "XR-F6"
    F7 = "XR-F7"
    F8 = "XR-F8"
    F9 = "XR-F9"
    F10 = "XR-F10"
    F11 = "XR-F11"
    T2 = "XR-T2"
    T3 = "XR-T3"
    T4 = "XR-T4"
    T5 = "XR-T5"
    E1 = "XR-E1"
    E2 = "XR-E2"
    E3 = "XR-E3"
    E4 = "XR-E4"
    E5 = "XR-E5"
    E6 = "XR-E6"
    E7 = "XR-E7"
    E8 = "XR-E8"
    E9 = "XR-E9"
    E10 = "XR-E10"
    E11 = "XR-E11"


class Violation(StrictModel):
    """One violated cross-record invariant. A result value, not a Record: never persisted here."""

    code: InvariantCode
    subject: StrictStr
    detail: StrictStr


SUPPORTED_RECORD_TYPES: tuple[type[Record], ...] = (
    TaskManifest,
    Requirement,
    EvaluationPolicy,
    CandidateManifest,
    Observation,
    Finding,
    FindingTransition,
    EpisodeBudget,
    EpisodeState,
)

# X5: identity that a TaskManifest revision may never change (task_id is the chain key itself).
TASK_STABLE_FIELDS = (
    "task_id",
    "family_id",
    "lineage_id",
    "variant_id",
    "split",
    "contract_id",
    "task_type",
    "authority_mode",
    "source",
)
_ADDITIVE = tuple(BudgetVector.model_fields)
_CHAIN_TYPES = (TaskManifest, Requirement, EvaluationPolicy)

R = TypeVar("R", bound=Record)


# ---- indexing ----------------------------------------------------------------------------------


def _subject(record: Record) -> str:
    match record:
        case TaskManifest():
            return f"TaskManifest:{record.task_id}@v{record.manifest_version}"
        case Requirement():
            return (
                f"Requirement:{record.task_id}/{record.requirement_id}"
                f"@v{record.requirement_version}"
            )
        case EvaluationPolicy():
            return f"EvaluationPolicy:{record.policy_id}@v{record.policy_version}"
        case CandidateManifest():
            return f"CandidateManifest:{record.candidate_id}"
        case Observation():
            return f"Observation:{record.observation_id}"
        case Finding():
            return f"Finding:{record.finding_id}"
        case FindingTransition():
            return f"FindingTransition:{record.finding_id}#{record.sequence}"
        case EpisodeState():
            return f"EpisodeState:{record.task_id}/{record.episode_id}#{record.sequence}"
        case _:
            return f"{type(record).__name__}:{record.content_id()}"


def _logical_key(record: Record) -> Hashable | None:
    match record:
        case TaskManifest():
            return (record.task_id, record.manifest_version)
        case Requirement():
            return (record.task_id, record.requirement_id, record.requirement_version)
        case EvaluationPolicy():
            return (record.policy_id, record.policy_version)
        case CandidateManifest():
            return record.candidate_id
        case Observation():
            return record.observation_id
        case Finding():
            return record.finding_id
        case FindingTransition():
            return (record.finding_id, record.sequence)
        case EpisodeState():
            return (record.task_id, record.episode_id, record.sequence)
        case _:
            return None  # EpisodeBudget: identity is its content_id


def _chain_key(record: Record) -> Hashable:
    match record:
        case TaskManifest():
            return record.task_id
        case Requirement():
            return (record.task_id, record.requirement_id)
        case EvaluationPolicy():
            return record.policy_id
    raise TypeError(type(record).__name__)


def _references(record: Record) -> Iterator[tuple[str, type[Record], str, str | None, str | None]]:
    """H1 references: (path, target type, hash, id attribute, expected id)."""
    match record:
        case TaskManifest() | Requirement() | EvaluationPolicy():
            if record.supersedes is not None:
                yield "supersedes", type(record), record.supersedes, None, None
        case Observation():
            yield ("candidate_manifest_hash", CandidateManifest, record.candidate_manifest_hash,
                   "candidate_id", record.candidate_id)
            yield "policy_hash", EvaluationPolicy, record.policy_hash, "policy_id", record.policy_id
        case Finding():
            yield ("candidate_manifest_hash", CandidateManifest, record.candidate_manifest_hash,
                   "candidate_id", record.candidate_id)
            for i, c in enumerate(record.correctness_citations):
                yield (f"correctness_citations[{i}]", Observation, c.observation_hash,
                       "observation_id", c.observation_id)
        case FindingTransition():
            yield "finding_hash", Finding, record.finding_hash, "finding_id", record.finding_id
            if record.previous_transition_hash is not None:
                yield ("previous_transition_hash", FindingTransition,
                       record.previous_transition_hash, None, None)
            for i, c in enumerate(record.deciding_citations):
                yield (f"deciding_citations[{i}]", Observation, c.observation_hash,
                       "observation_id", c.observation_id)
            if record.proposed_check is not None:
                yield ("proposed_check.policy_hash", EvaluationPolicy,
                       record.proposed_check.policy_hash, None, None)
        case EpisodeState():
            if record.previous_state_hash is not None:
                yield "previous_state_hash", EpisodeState, record.previous_state_hash, None, None
            yield "policy_hash", EvaluationPolicy, record.policy_hash, "policy_id", record.policy_id
            yield "budget_hash", EpisodeBudget, record.budget_hash, None, None
            for path, binding in _bindings(record):
                yield (path, CandidateManifest, binding.candidate_manifest_hash,
                       "candidate_id", binding.candidate_id)


def _bindings(state: EpisodeState) -> Iterator[tuple[str, CandidateBinding]]:
    if state.active_candidate is not None:
        yield "active_candidate", state.active_candidate
    if state.best_candidate is not None:
        yield "best_candidate", state.best_candidate
    for job in state.pending_jobs:
        if job.candidate is not None:
            yield f"pending_jobs[{job.job_id}].candidate", job.candidate


class _Bundle:
    """Read-only index over the deduplicated input. Rules read it; they never emit from here."""

    def __init__(self, records: Iterable[Record]) -> None:
        self.cid: dict[int, str] = {}
        by_hash: dict[type[Record], dict[str, Record]] = defaultdict(dict)
        for record in records:
            kind = type(record)
            if not isinstance(record, Record):
                raise TypeError(f"check_records accepts Records only, not {kind.__name__}")
            if kind not in SUPPORTED_RECORD_TYPES:
                raise TypeError(f"unsupported Record type for cross-record checks: {kind.__name__}")
            by_hash[kind].setdefault(record.content_id(), record)  # exact duplicates collapse
        self.by_hash = by_hash
        for table in by_hash.values():
            for cid, record in table.items():
                self.cid[id(record)] = cid
        self.of: dict[type[Record], list[Record]] = {
            kind: [by_hash[kind][c] for c in sorted(by_hash[kind])]
            for kind in SUPPORTED_RECORD_TYPES
        }

        # XR-B1: logical keys; an ambiguous key is ambiguous authority for every dependant.
        self.by_key: dict[type[Record], dict[Hashable, list[Record]]] = defaultdict(dict)
        for kind, items in self.of.items():
            for record in items:
                key = _logical_key(record)
                if key is not None:
                    self.by_key[kind].setdefault(key, []).append(record)
        self.ambiguous: dict[type[Record], set[Hashable]] = {
            kind: {k for k, v in keys.items() if len(v) > 1} for kind, keys in self.by_key.items()
        }

        # XR-B2: resolve every H1 reference occurrence once.
        self.resolved: dict[tuple[int, str], Record | None] = {}
        self.broken: list[tuple[Record, str, str]] = []
        for kind in SUPPORTED_RECORD_TYPES:
            for record in self.of[kind]:
                for path, target_kind, ref_hash, id_attr, expected in _references(record):
                    target = by_hash[target_kind].get(ref_hash)
                    if target is None:
                        reason = f"{ref_hash} names no {target_kind.__name__} in the bundle"
                        self.broken.append((record, path, reason))
                    elif id_attr is not None and str(getattr(target, id_attr)) != expected:
                        reason = (f"{ref_hash} is {id_attr}={getattr(target, id_attr)}, "
                                  f"not {expected}")
                        self.broken.append((record, path, reason))
                        target = None
                    self.resolved[(id(record), path)] = target

        # Domain revision chains: set heads per chain key, with ownership-aware tainting.
        self.superseded: set[str] = set()
        self.tainted: set[tuple[type[Record], Hashable]] = set()
        for kind in _CHAIN_TYPES:
            for key in self.ambiguous.get(kind, ()):
                sample = self.by_key[kind][key][0]
                self.tainted.add((kind, _chain_key(sample)))
            for record in self.of[kind]:
                prev = self.ref(record, "supersedes")
                if prev is None:
                    continue
                if _chain_key(prev) == _chain_key(record):
                    self.superseded.add(self.cid[id(prev)])
                else:  # identity broken across the link (C3/C4/C5 own it): both chains unusable
                    self.tainted.add((kind, _chain_key(record)))
                    self.tainted.add((kind, _chain_key(prev)))
        self.chains: dict[type[Record], dict[Hashable, list[Record]]] = defaultdict(dict)
        for kind in _CHAIN_TYPES:
            for record in self.of[kind]:
                self.chains[kind].setdefault(_chain_key(record), []).append(record)

    def ref(self, record: Record, path: str) -> Any:
        return self.resolved.get((id(record), path))

    def unique(self, kind: type[R], key: Hashable) -> R | None:
        found = self.by_key[kind].get(key, [])
        return found[0] if len(found) == 1 else None  # type: ignore[return-value]

    def is_ambiguous(self, kind: type[Record], key: Hashable) -> bool:
        return key in self.ambiguous.get(kind, ())

    def records(self, kind: type[R]) -> list[R]:
        return self.of[kind]  # type: ignore[return-value]

    def head(self, kind: type[R], chain_key: Hashable) -> R | None:
        if (kind, chain_key) in self.tainted:
            return None
        live = [r for r in self.chains[kind].get(chain_key, [])
                if self.cid[id(r)] not in self.superseded]
        return live[0] if len(live) == 1 else None  # type: ignore[return-value]

    def is_superseded(self, record: Record) -> bool:
        return self.cid[id(record)] in self.superseded

    def task_revisions(self, task_id: str) -> list[TaskManifest]:
        return self.chains[TaskManifest].get(task_id, [])  # type: ignore[return-value]


def _v(code: InvariantCode, subject: str, detail: str) -> Violation:
    return Violation(code=code, subject=subject, detail=detail)


def _cycles(edges: Mapping[str, Iterable[str]]) -> list[list[str]]:
    """Cyclic strongly connected components (incl. self-loops), each sorted, deterministic."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    found: list[list[str]] = []
    counter = 0
    graph = {node: sorted(set(nxt)) for node, nxt in edges.items()}
    for root in sorted(graph):
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, i = work.pop()
            if i == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            successors = graph.get(node, [])
            if i < len(successors):
                work.append((node, i + 1))
                nxt = successors[i]
                if nxt not in index:
                    work.append((nxt, 0))
                elif nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
                continue
            if low[node] == index[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                if len(component) > 1 or node in graph.get(node, []):
                    found.append(sorted(component))
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
    return sorted(found)


def _cycle_text(members: list[str]) -> str:
    return "cycle among " + ", ".join(members)


# ---- B: bundle structure and hash resolution ---------------------------------------------------


def _b1(b: _Bundle) -> Iterator[Violation]:
    for kind, keys in b.ambiguous.items():
        for key in keys:
            group = b.by_key[kind][key]
            ids = ", ".join(sorted(b.cid[id(r)] for r in group))
            yield _v(InvariantCode.B1, _subject(group[0]),
                     f"{len(group)} distinct records share this logical key: {ids}")


def _b2(b: _Bundle) -> Iterator[Violation]:
    for record, path, reason in b.broken:
        yield _v(InvariantCode.B2, _subject(record), f"{path}: {reason}")


# ---- C: domain revision chains and task lineage ------------------------------------------------


def _version(record: Record) -> int:
    match record:
        case TaskManifest():
            return record.manifest_version
        case Requirement():
            return record.requirement_version
        case EvaluationPolicy():
            return record.policy_version
    raise TypeError(type(record).__name__)


def _c1(b: _Bundle) -> Iterator[Violation]:
    for kind in _CHAIN_TYPES:
        for record in b.records(kind):
            prev = b.ref(record, "supersedes")
            if prev is not None and _version(prev) != _version(record) - 1:
                yield _v(InvariantCode.C1, _subject(record),
                         f"supersedes version {_version(prev)}, expected {_version(record) - 1}")


def _link_fields(
    b: _Bundle, kind: type[Record], fields: tuple[str, ...], code: InvariantCode
) -> Iterator[Violation]:
    for record in b.records(kind):
        prev = b.ref(record, "supersedes")
        if prev is None:
            continue
        for field in fields:
            if getattr(record, field) != getattr(prev, field):
                yield _v(code, _subject(record),
                         f"{field} differs from the superseded revision {_subject(prev)}")


def _c3(b: _Bundle) -> Iterator[Violation]:
    yield from _link_fields(b, TaskManifest, TASK_STABLE_FIELDS, InvariantCode.C3)


def _c4(b: _Bundle) -> Iterator[Violation]:
    yield from _link_fields(b, Requirement, ("task_id", "requirement_id"), InvariantCode.C4)


def _c5(b: _Bundle) -> Iterator[Violation]:
    yield from _link_fields(b, EvaluationPolicy, ("policy_id", "task_id"), InvariantCode.C5)


def _task_heads(b: _Bundle) -> list[TaskManifest]:
    heads = (b.head(TaskManifest, k) for k in sorted(b.chains[TaskManifest], key=str))
    return [h for h in heads if h is not None]


def _c6(b: _Bundle) -> Iterator[Violation]:
    families: dict[str, list[TaskManifest]] = defaultdict(list)
    for head in _task_heads(b):
        families[head.family_id].append(head)
    for family in sorted(families):
        splits = sorted({h.split.value for h in families[family]})
        if len(splits) > 1:
            tasks = ", ".join(sorted(h.task_id for h in families[family]))
            yield _v(InvariantCode.C6, f"TaskFamily:{family}",
                     f"set heads carry splits {splits} ({tasks})")


def _c7(b: _Bundle) -> Iterator[Violation]:
    for task in b.records(TaskManifest):
        if not isinstance(task.source, MutationSource):
            continue
        parent_id = task.source.parent_task_id
        if not b.task_revisions(parent_id):
            yield _v(InvariantCode.C7, _subject(task),
                     f"mutation parent_task_id {parent_id} names no TaskManifest")
            continue
        parent = b.head(TaskManifest, parent_id)
        if parent is None:
            continue
        for field in ("family_id", "lineage_id"):
            if getattr(task, field) != getattr(parent, field):
                yield _v(InvariantCode.C7, _subject(task),
                         f"{field} differs from mutation parent {_subject(parent)}")


def _c8(b: _Bundle) -> Iterator[Violation]:
    edges: dict[str, list[str]] = {}
    for head in _task_heads(b):
        source = head.source
        if isinstance(source, MutationSource) and b.task_revisions(source.parent_task_id):
            edges[head.task_id] = [source.parent_task_id]
    for members in _cycles(edges):
        yield _v(InvariantCode.C8, f"Task:{members[0]}",
                 f"mutation ancestry {_cycle_text(members)}")


# ---- P: task <-> requirement <-> policy --------------------------------------------------------


def _policy_heads(b: _Bundle) -> list[EvaluationPolicy]:
    heads = (b.head(EvaluationPolicy, k) for k in sorted(b.chains[EvaluationPolicy], key=str))
    return [h for h in heads if h is not None]


def _p1(b: _Bundle) -> Iterator[Violation]:
    for policy in b.records(EvaluationPolicy):
        if not b.task_revisions(policy.task_id):
            yield _v(InvariantCode.P1, _subject(policy),
                     f"task_id {policy.task_id} names no TaskManifest")


def _p2a_ok(b: _Bundle, policy: EvaluationPolicy) -> bool:
    revisions = b.task_revisions(policy.task_id)
    return any(t.approved_contract_hash == policy.contract_hash for t in revisions)


def _current(b: _Bundle, policy: EvaluationPolicy) -> TaskManifest | None:
    """The head task of a head policy whose contract matches it (XR-P2B satisfied), else None."""
    task = b.head(TaskManifest, policy.task_id)
    if task is None or task.approved_contract_hash != policy.contract_hash:
        return None
    return task


def _p2a(b: _Bundle) -> Iterator[Violation]:
    for policy in b.records(EvaluationPolicy):
        if b.task_revisions(policy.task_id) and not _p2a_ok(b, policy):
            yield _v(InvariantCode.P2A, _subject(policy),
                     "contract_hash is not the approved_contract_hash of any revision of "
                     f"{policy.task_id}")


def _p2b(b: _Bundle) -> Iterator[Violation]:
    for policy in _policy_heads(b):
        task = b.head(TaskManifest, policy.task_id)
        if task is not None and task.approved_contract_hash != policy.contract_hash:
            yield _v(InvariantCode.P2B, _subject(policy),
                     f"head policy contract_hash differs from head task {_subject(task)}")


def _p3(b: _Bundle) -> Iterator[Violation]:
    for policy in b.records(EvaluationPolicy):
        if not b.task_revisions(policy.task_id):
            continue
        wanted = sorted({ob.requirement_id for ob in policy.obligations})
        if b.head(EvaluationPolicy, policy.policy_id) is policy:
            task = _current(b, policy)
            if task is None:
                continue
            listed = set(task.requirement_ids)
            where = f"head task {_subject(task)}"
        elif b.is_superseded(policy):
            if not _p2a_ok(b, policy):
                continue
            matching = [t for t in b.task_revisions(policy.task_id)
                        if t.approved_contract_hash == policy.contract_hash]
            listed = {rid for t in matching for rid in t.requirement_ids}
            where = "any task revision carrying this contract_hash"
        else:
            continue
        for rid in wanted:
            if rid not in listed:
                yield _v(InvariantCode.P3, _subject(policy),
                         f"obligation requirement {rid} is not listed by {where}")


def _p4(b: _Bundle) -> Iterator[Violation]:
    requirement_chains = b.chains[Requirement]
    for task in _task_heads(b):
        for rid in task.requirement_ids:
            if (task.task_id, rid) not in requirement_chains:
                yield _v(InvariantCode.P4, _subject(task),
                         f"requirement {rid} has no Requirement record")
    for key in sorted(requirement_chains, key=str):
        owner, requirement_id = cast(tuple[str, str], key)
        listed = {r for t in b.task_revisions(owner) for r in t.requirement_ids}
        if requirement_id not in listed:
            yield _v(InvariantCode.P4, f"Requirement:{owner}/{requirement_id}",
                     "not listed by any TaskManifest revision of its task")


def _vocabulary(policy: EvaluationPolicy) -> set[str] | None:
    names = {frozenset(a.name for a in c.assignments) for c in policy.configurations}
    return set(next(iter(names))) if len(names) == 1 else None


def _p8(b: _Bundle) -> Iterator[Violation]:
    for policy in b.records(EvaluationPolicy):
        if b.task_revisions(policy.task_id) and _vocabulary(policy) is None:  # P1 owns no-task
            sets = sorted(
                "{" + ",".join(sorted(a.name for a in c.assignments)) + "}"
                for c in policy.configurations
            )
            yield _v(InvariantCode.P8, _subject(policy),
                     f"configurations assign different parameter-name sets: {sorted(set(sets))}")


def _scoped_names(requirement: Requirement) -> list[str]:
    if isinstance(requirement.applicability, AllSupportedConfigs):
        return []
    return [p.name for p in requirement.applicability.parameters]


def _coverage_units(
    b: _Bundle,
) -> Iterator[tuple[TaskManifest, EvaluationPolicy, Requirement, set[str]]]:
    """(head task, head policy, head requirement, vocabulary) where P1/P8/P4 authority holds."""
    for policy in _policy_heads(b):
        task = b.head(TaskManifest, policy.task_id)
        vocabulary = _vocabulary(policy)
        if task is None or vocabulary is None:
            continue
        for rid in task.requirement_ids:
            requirement = b.head(Requirement, (task.task_id, rid))
            if requirement is not None:
                yield task, policy, requirement, vocabulary


def _p5(b: _Bundle) -> Iterator[Violation]:
    for _task, policy, requirement, vocabulary in _coverage_units(b):
        for name in _scoped_names(requirement):
            if name not in vocabulary:
                yield _v(InvariantCode.P5, _subject(requirement),
                         f"scoped parameter {name} is not in the vocabulary of {_subject(policy)}")


def _same_scalar(a: ExactScalar, b: ExactScalar) -> bool:
    return type(a) is type(b) and a == b


def _applies(requirement: Requirement, cfg: Configuration) -> bool:
    applicability = requirement.applicability
    if isinstance(applicability, AllSupportedConfigs):
        return True
    assigned = {a.name: a.value for a in cfg.assignments}
    return all(
        any(_same_scalar(assigned[p.name], value) for value in p.values)
        for p in applicability.parameters
    )


def _excluded(policy: EvaluationPolicy) -> set[tuple[str, str]]:
    return {(p.check_id, p.configuration_id) for e in policy.exceptions for p in e.excludes}


def _enforced(policy: EvaluationPolicy, rid: str, cfg: str) -> bool:
    checks = {c.check_id: c for c in policy.checks}
    excluded = _excluded(policy)
    return any(
        check.mandatory
        and check.kind is not CheckKind.QUALITY
        and cfg in check.configuration_ids
        and (check.check_id, cfg) not in excluded
        for ob in policy.obligations
        if ob.requirement_id == rid
        for check in (checks[c] for c in ob.check_ids)
    )


def _enforceable(
    b: _Bundle,
) -> Iterator[tuple[EvaluationPolicy, Requirement]]:
    for task, policy, requirement, vocabulary in _coverage_units(b):
        if task.approved_contract_hash != policy.contract_hash:
            continue  # XR-P2B owns currency
        if any(name not in vocabulary for name in _scoped_names(requirement)):
            continue  # XR-P5 owns resolvability
        if requirement.disposition is RequirementDisposition.APPROVED and requirement.mandatory:
            yield policy, requirement


def _p6(b: _Bundle) -> Iterator[Violation]:
    for policy, requirement in _enforceable(b):
        for cfg in policy.configurations:
            rid, cid = requirement.requirement_id, cfg.configuration_id
            if _applies(requirement, cfg) and not _enforced(policy, rid, cid):
                yield _v(InvariantCode.P6, _subject(policy),
                         f"approved mandatory {rid} is not enforced in {cid}: no mandatory, "
                         "non-quality, applicable, non-excluded obligation check")


def _p7(b: _Bundle) -> Iterator[Violation]:
    for policy, requirement in _enforceable(b):
        if not any(_applies(requirement, cfg) for cfg in policy.configurations):
            yield _v(InvariantCode.P7, _subject(policy),
                     f"approved mandatory {requirement.requirement_id} applies to no configuration")


# ---- K: candidate <-> task / parent ------------------------------------------------------------


def _inside(path: str, entries: Iterable[str]) -> bool:
    return any(path == e or path.startswith(e + "/") for e in entries)


def _k1(b: _Bundle) -> Iterator[Violation]:
    for cand in b.records(CandidateManifest):
        if not b.task_revisions(cand.task_id):
            yield _v(InvariantCode.K1, _subject(cand),
                     f"task_id {cand.task_id} names no TaskManifest")


def _k2(b: _Bundle) -> Iterator[Violation]:
    for cand in b.records(CandidateManifest):
        task = b.head(TaskManifest, cand.task_id)
        if task is not None and task.task_type in READ_ONLY_TASK_TYPES:
            yield _v(InvariantCode.K2, _subject(cand),
                     f"head task {_subject(task)} is read-only ({task.task_type})")


def _k3(b: _Bundle) -> Iterator[Violation]:
    for cand in b.records(CandidateManifest):
        task = b.head(TaskManifest, cand.task_id)
        if task is None or task.task_type in READ_ONLY_TASK_TYPES:
            continue  # XR-K1 / XR-K2 own these
        for f in cand.files:
            if not _inside(str(f.path), task.allowed_edit_paths):
                yield _v(InvariantCode.K3, _subject(cand),
                         f"{f.path} is outside allowed_edit_paths of {_subject(task)}")


def _parent(b: _Bundle, cand: CandidateManifest) -> CandidateManifest | None:
    pid = cand.parent_candidate_id
    if pid is None or b.is_ambiguous(CandidateManifest, pid):
        return None
    return b.unique(CandidateManifest, pid)


def _k4(b: _Bundle) -> Iterator[Violation]:
    for cand in b.records(CandidateManifest):
        pid = cand.parent_candidate_id
        if pid is None or b.is_ambiguous(CandidateManifest, pid):
            continue
        parent = b.unique(CandidateManifest, pid)
        if parent is None:
            yield _v(InvariantCode.K4, _subject(cand), f"parent {pid} is not in the bundle")
        elif parent.task_id != cand.task_id:
            yield _v(InvariantCode.K4, _subject(cand),
                     f"parent {pid} belongs to task {parent.task_id}, not {cand.task_id}")


def _k5(b: _Bundle) -> Iterator[Violation]:
    edges: dict[str, list[str]] = {}
    for cand in b.records(CandidateManifest):
        if b.is_ambiguous(CandidateManifest, cand.candidate_id):
            continue  # ambiguous source authority: XR-B1 owns it
        parent = _parent(b, cand)
        if parent is not None:
            edges[str(cand.candidate_id)] = [str(parent.candidate_id)]
    for members in _cycles(edges):
        yield _v(InvariantCode.K5, f"CandidateManifest:{members[0]}",
                 f"parent ancestry {_cycle_text(members)}")


def _k6(b: _Bundle) -> Iterator[Violation]:
    by_task: dict[str, set[str]] = defaultdict(set)
    for cand in b.records(CandidateManifest):
        if b.task_revisions(cand.task_id):
            by_task[cand.task_id].add(str(cand.dependency_hash))
    for task_id in sorted(by_task):
        if len(by_task[task_id]) > 1:
            yield _v(InvariantCode.K6, f"Task:{task_id}",
                     "candidates carry different dependency_hash values "
                     f"{sorted(by_task[task_id])}")


# ---- O: observation <-> exact candidate, policy, check, configuration -------------------------


def _o3_problem(obs: Observation, policy: EvaluationPolicy) -> str | None:
    check = next((c for c in policy.checks if c.check_id == obs.check_id), None)
    if check is None:
        return f"check {obs.check_id} is not in {_subject(policy)}"
    if obs.configuration_id not in check.configuration_ids:
        return f"{obs.check_id} does not target {obs.configuration_id}"
    if (obs.check_id, obs.configuration_id) in _excluded(policy):
        return f"({obs.check_id}, {obs.configuration_id}) is excluded by a policy exception"
    return None


def _o1(b: _Bundle) -> Iterator[Violation]:
    for obs in b.records(Observation):
        cand = b.ref(obs, "candidate_manifest_hash")
        if cand is None:
            continue
        for field in ("source_hash", "dependency_hash"):
            if getattr(obs, field) != getattr(cand, field):
                yield _v(InvariantCode.O1, _subject(obs),
                         f"{field} differs from {_subject(cand)}")


def _o2(b: _Bundle) -> Iterator[Violation]:
    for obs in b.records(Observation):
        cand, policy = b.ref(obs, "candidate_manifest_hash"), b.ref(obs, "policy_hash")
        if cand is not None and policy is not None and policy.task_id != cand.task_id:
            yield _v(InvariantCode.O2, _subject(obs),
                     f"policy task {policy.task_id} differs from candidate task {cand.task_id}")


def _o3(b: _Bundle) -> Iterator[Violation]:
    for obs in b.records(Observation):
        policy = b.ref(obs, "policy_hash")
        problem = None if policy is None else _o3_problem(obs, policy)
        if problem is not None:
            yield _v(InvariantCode.O3, _subject(obs), problem)


_O4_FIELDS = (
    ("check_kind", "kind"),
    ("visibility", "visibility"),
    ("tool_profile_id", "tool_profile_id"),
    ("formal_mode", "formal_mode"),
    ("formal_depth", "depth"),
)


def _o4(b: _Bundle) -> Iterator[Violation]:
    for obs in b.records(Observation):
        policy = b.ref(obs, "policy_hash")
        if policy is None or _o3_problem(obs, policy) is not None:
            continue
        check = next(c for c in policy.checks if c.check_id == obs.check_id)
        for mine, theirs in _O4_FIELDS:
            if getattr(obs, mine) != getattr(check, theirs):
                yield _v(InvariantCode.O4, _subject(obs),
                         f"{mine} differs from policy check {check.check_id}.{theirs}")


# ---- F: finding <-> candidate, requirement, policy, observations -------------------------------


def _chains(b: _Bundle) -> dict[str, list[FindingTransition]]:
    out: dict[str, list[FindingTransition]] = defaultdict(list)
    for t in b.records(FindingTransition):
        out[t.finding_id].append(t)
    return {fid: sorted(ts, key=lambda t: (t.sequence, b.cid[id(t)])) for fid, ts in out.items()}


def _proposal(chain: list[FindingTransition]) -> FindingTransition | None:
    proposing = [t for t in chain if t.proposed_check is not None]
    return proposing[0] if len(proposing) == 1 else None


def _f6_problem(b: _Bundle, t: FindingTransition) -> str | None:
    """None when the proposal resolves cleanly (or cannot be judged: B2 owns that)."""
    proposal, policy = t.proposed_check, b.ref(t, "proposed_check.policy_hash")
    if proposal is None or policy is None:
        return None
    if isinstance(proposal, ExistingPolicyCheck):
        check = next((c for c in policy.checks if c.check_id == proposal.check_id), None)
        if check is None:
            return f"proposed check {proposal.check_id} is not in {_subject(policy)}"
        if proposal.configuration_id not in check.configuration_ids:
            return f"{proposal.check_id} does not target {proposal.configuration_id}"
        if (proposal.check_id, proposal.configuration_id) in _excluded(policy):
            return f"({proposal.check_id}, {proposal.configuration_id}) is excluded"
    elif proposal.configuration_id not in {c.configuration_id for c in policy.configurations}:
        return f"probe configuration {proposal.configuration_id} is not in {_subject(policy)}"
    finding = b.ref(t, "finding_hash")
    if finding is not None and policy.task_id != finding.task_id:
        return f"proposal policy task {policy.task_id} differs from finding task {finding.task_id}"
    return None


def _f1(b: _Bundle) -> Iterator[Violation]:
    for f in b.records(Finding):
        cand = b.ref(f, "candidate_manifest_hash")
        if cand is not None and cand.task_id != f.task_id:
            yield _v(InvariantCode.F1, _subject(f),
                     f"candidate {cand.candidate_id} belongs to task {cand.task_id}")


def _f2(b: _Bundle) -> Iterator[Violation]:
    for f in b.records(Finding):
        task = b.head(TaskManifest, f.task_id)
        if task is not None and f.requirement_id not in task.requirement_ids:
            yield _v(InvariantCode.F2, _subject(f),
                     f"requirement {f.requirement_id} is not listed by {_subject(task)}")


def _cited(
    b: _Bundle,
) -> Iterator[tuple[Record, str, Finding, Observation]]:
    """Every resolved citation with the Finding it speaks for: (subject record, path, F, obs)."""
    for f in b.records(Finding):
        for i in range(len(f.correctness_citations)):
            path = f"correctness_citations[{i}]"
            obs = b.ref(f, path)
            if obs is not None:
                yield f, path, f, obs
    for t in b.records(FindingTransition):
        finding = b.ref(t, "finding_hash")
        if finding is None:
            continue
        for i in range(len(t.deciding_citations)):
            path = f"deciding_citations[{i}]"
            obs = b.ref(t, path)
            if obs is not None:
                yield t, path, finding, obs


def _f3(b: _Bundle) -> Iterator[Violation]:
    for subject, path, finding, obs in _cited(b):
        if b.ref(obs, "candidate_manifest_hash") is None:
            continue  # the Observation's own binding is broken: XR-B2 owns it
        if obs.candidate_manifest_hash != finding.candidate_manifest_hash:
            yield _v(InvariantCode.F3, _subject(subject),
                     f"{path}: {_subject(obs)} is bound to another candidate manifest")


def _f4(b: _Bundle) -> Iterator[Violation]:
    for t in b.records(FindingTransition):
        for i in range(len(t.deciding_citations)):
            path = f"deciding_citations[{i}]"
            obs = b.ref(t, path)
            if obs is not None and not obs.status.is_label:
                yield _v(InvariantCode.F4, _subject(t),
                         f"{path}: {_subject(obs)} has non-verdict status {obs.status}")


def _f5(b: _Bundle) -> Iterator[Violation]:
    for _fid, chain in _clean_chains(b):
        proposer = _proposal(chain)
        if proposer is None or _f6_problem(b, proposer) is not None:
            continue
        proposal = proposer.proposed_check
        if not isinstance(proposal, ExistingPolicyCheck):
            continue
        if b.ref(proposer, "proposed_check.policy_hash") is None:
            continue
        for t in chain:
            if t.to_status not in DECIDED_FINDING_STATUSES:
                continue
            expected: ToolStatus = (
                proposal.confirming_status
                if t.to_status is FindingStatus.CONFIRMED
                else proposal.refuting_status
            )
            for i in range(len(t.deciding_citations)):
                path = f"deciding_citations[{i}]"
                obs = b.ref(t, path)
                if obs is None or not obs.status.is_label:
                    continue  # B2 / F4 own these
                if b.ref(obs, "policy_hash") is None:
                    continue  # the Observation's own policy binding is broken: XR-B2
                same_check = (
                    obs.policy_hash == proposal.policy_hash
                    and obs.check_id == proposal.check_id
                    and obs.configuration_id == proposal.configuration_id
                )
                if not same_check:
                    yield _v(InvariantCode.F5, _subject(t),
                             f"{path}: {_subject(obs)} is not the proposed check "
                             f"({proposal.check_id}, {proposal.configuration_id})")
                elif obs.status is not expected:
                    yield _v(InvariantCode.F5, _subject(t),
                             f"{path}: {t.to_status} needs {expected}, cited {obs.status}")


def _f6(b: _Bundle) -> Iterator[Violation]:
    for t in b.records(FindingTransition):
        problem = _f6_problem(b, t)
        if problem is not None:
            yield _v(InvariantCode.F6, _subject(t), problem)


def _f10(b: _Bundle) -> Iterator[Violation]:
    for t in b.records(FindingTransition):
        proposal = t.proposed_check
        if not isinstance(proposal, ExistingPolicyCheck) or _f6_problem(b, t) is not None:
            continue
        policy, finding = b.ref(t, "proposed_check.policy_hash"), b.ref(t, "finding_hash")
        if policy is None or finding is None:
            continue
        if not any(ob.requirement_id == finding.requirement_id and proposal.check_id in ob.check_ids
                   for ob in policy.obligations):
            yield _v(InvariantCode.F10, _subject(t),
                     f"{proposal.check_id} is in no obligation for {finding.requirement_id} "
                     f"in {_subject(policy)}")


def _f7(b: _Bundle) -> Iterator[Violation]:
    for fid, chain in _clean_chains(b):
        probed = any(isinstance(t.proposed_check, DevelopmentProbeRequest) for t in chain)
        decided = [t for t in chain if t.to_status in DECIDED_FINDING_STATUSES]
        if probed and decided:
            yield _v(InvariantCode.F7, f"Finding:{fid}",
                     f"a probe-proposed finding reached {decided[0].to_status}")


def _finding_by_id(b: _Bundle, fid: str) -> tuple[bool, Finding | None]:
    """(judgeable, finding): ambiguous ids are not judgeable (B1 owns them)."""
    if b.is_ambiguous(Finding, fid):
        return False, None
    return True, b.unique(Finding, fid)


def _f8(b: _Bundle) -> Iterator[Violation]:
    links: list[tuple[Record, str, str, str | None]] = []
    for f in b.records(Finding):
        if f.derived_from is not None:
            links.append((f, "derived_from", f.derived_from, f.task_id))
    for t in b.records(FindingTransition):
        if t.superseded_by is not None:
            owner = b.ref(t, "finding_hash")
            links.append((t, "superseded_by", t.superseded_by,
                          None if owner is None else owner.task_id))
    for subject, field, target_id, task_id in links:
        judgeable, target = _finding_by_id(b, target_id)
        if not judgeable:
            continue
        if target is None:
            yield _v(InvariantCode.F8, _subject(subject),
                     f"{field} {target_id} is not in the bundle")
        elif task_id is not None and target.task_id != task_id:
            yield _v(InvariantCode.F8, _subject(subject),
                     f"{field} {target_id} belongs to task {target.task_id}, not {task_id}")


def _f11(b: _Bundle) -> Iterator[Violation]:
    derived: dict[str, list[str]] = defaultdict(list)
    for f in b.records(Finding):
        if b.is_ambiguous(Finding, f.finding_id):
            continue  # ambiguous source authority: XR-B1 owns it
        if f.derived_from is not None and _finding_by_id(b, f.derived_from)[1] is not None:
            derived[str(f.finding_id)].append(str(f.derived_from))
    superseded: dict[str, list[str]] = defaultdict(list)
    for t in b.records(FindingTransition):
        if t.superseded_by is None or b.is_ambiguous(FindingTransition, (t.finding_id, t.sequence)):
            continue
        owner = b.ref(t, "finding_hash")
        if owner is None or b.is_ambiguous(Finding, owner.finding_id):
            continue  # broken (XR-B2) or ambiguous (XR-B1) owner
        if _finding_by_id(b, t.superseded_by)[1] is not None:
            superseded[str(owner.finding_id)].append(str(t.superseded_by))
    for graph, edges in (("derived_from", derived), ("superseded_by", superseded)):
        for members in _cycles(edges):
            yield _v(InvariantCode.F11, f"Finding:{members[0]}", f"{graph} {_cycle_text(members)}")


def _f9(b: _Bundle) -> Iterator[Violation]:
    for subject, path, finding, obs in _cited(b):
        if finding.producer.role is FindingRole.SOLVER and obs.visibility is Visibility.HIDDEN:
            yield _v(InvariantCode.F9, _subject(subject),
                     f"{path}: solver finding cites hidden-check {_subject(obs)}")


# ---- T: finding transition chains --------------------------------------------------------------


def _clean_chains(b: _Bundle) -> Iterator[tuple[str, list[FindingTransition]]]:
    for fid, chain in sorted(_chains(b).items()):
        if not any(b.is_ambiguous(FindingTransition, (fid, t.sequence)) for t in chain):
            yield fid, chain


def _pairs(chain: list[Any]) -> Iterator[tuple[Any, Any]]:
    """Consecutive pairs whose sequences are contiguous (gaps are owned by T2/E1)."""
    for prev, cur in zip(chain, chain[1:], strict=False):
        if cur.sequence == prev.sequence + 1:
            yield prev, cur


def _t2(b: _Bundle) -> Iterator[Violation]:
    for fid, chain in _clean_chains(b):
        seqs = [t.sequence for t in chain]
        if seqs != list(range(1, len(chain) + 1)):
            yield _v(InvariantCode.T2, f"Finding:{fid}",
                     f"transition sequences {seqs} are not 1..n")


def _t3(b: _Bundle) -> Iterator[Violation]:
    for _fid, chain in _clean_chains(b):
        for prev, cur in _pairs(chain):
            if b.ref(cur, "previous_transition_hash") is None:
                continue  # unresolved predecessor hash: XR-B2 owns it
            if cur.previous_transition_hash != b.cid[id(prev)]:
                yield _v(InvariantCode.T3, _subject(cur),
                         f"previous_transition_hash is not {_subject(prev)}")


def _t4(b: _Bundle) -> Iterator[Violation]:
    for _fid, chain in _clean_chains(b):
        for prev, cur in _pairs(chain):
            if prev.to_status in TERMINAL_FINDING_STATUSES:
                continue  # XR-T5 owns this
            if cur.from_status != prev.to_status:
                yield _v(InvariantCode.T4, _subject(cur),
                         f"from_status {cur.from_status} != previous to_status {prev.to_status}")


def _t5(b: _Bundle) -> Iterator[Violation]:
    for fid, chain in _clean_chains(b):
        for t in chain[:-1]:
            if t.to_status in TERMINAL_FINDING_STATUSES:
                yield _v(InvariantCode.T5, f"Finding:{fid}",
                         f"transitions follow terminal {t.to_status} at sequence {t.sequence}")
                break


# ---- E: episode state chains -------------------------------------------------------------------


def _episodes(b: _Bundle) -> Iterator[tuple[str, list[EpisodeState]]]:
    groups: dict[tuple[str, str], list[EpisodeState]] = defaultdict(list)
    for s in b.records(EpisodeState):
        groups[(s.task_id, s.episode_id)].append(s)
    for (task_id, episode_id), states in sorted(groups.items()):
        if any(b.is_ambiguous(EpisodeState, (task_id, episode_id, s.sequence)) for s in states):
            continue
        yield f"Episode:{task_id}/{episode_id}", sorted(states, key=lambda s: s.sequence)


def _e1(b: _Bundle) -> Iterator[Violation]:
    for name, chain in _episodes(b):
        problems = []
        seqs = [s.sequence for s in chain]
        if seqs != list(range(len(chain))):
            problems.append(f"sequences {seqs} are not 0..n")
        for prev, cur in _pairs(chain):
            if b.ref(cur, "previous_state_hash") is None:
                continue  # unresolved predecessor hash: XR-B2 owns it (E1 still owns gaps)
            if cur.previous_state_hash != b.cid[id(prev)]:
                problems.append(f"#{cur.sequence} does not name #{prev.sequence} as predecessor")
        if problems:
            yield _v(InvariantCode.E1, name, "; ".join(problems))


def _live_pairs(chain: list[EpisodeState]) -> Iterator[tuple[EpisodeState, EpisodeState]]:
    for prev, cur in _pairs(chain):
        if prev.state not in TERMINAL_EPISODE_STATES:  # XR-E4 owns post-terminal snapshots
            yield prev, cur


def _e2(b: _Bundle) -> Iterator[Violation]:
    for _name, chain in _episodes(b):
        for prev, cur in _live_pairs(chain):
            if (prev.state, cur.state) not in ALLOWED_EPISODE_TRANSITIONS:
                yield _v(InvariantCode.E2, _subject(cur),
                         f"{prev.state} -> {cur.state} is not an ADR-0006 transition")


def _e3(b: _Bundle) -> Iterator[Violation]:
    for _name, chain in _episodes(b):
        for prev, cur in _live_pairs(chain):
            if (prev.state, cur.state) not in ALLOWED_EPISODE_TRANSITIONS:
                continue  # XR-E2 owns illegal edges
            if prev.state is EpisodeStatus.WAITING and cur.state not in (
                prev.resume_state,
                EpisodeStatus.ABORTED,
            ):
                yield _v(InvariantCode.E3, _subject(cur),
                         f"WAITING resumed to {cur.state}, "
                         f"not its resume_state {prev.resume_state}")
            if cur.state is EpisodeStatus.WAITING and cur.resume_state != prev.state:
                yield _v(InvariantCode.E3, _subject(cur),
                         f"WAITING records resume_state {cur.resume_state}, "
                         f"but paused {prev.state}")


def _e4(b: _Bundle) -> Iterator[Violation]:
    for name, chain in _episodes(b):
        for s in chain[:-1]:
            if s.state in TERMINAL_EPISODE_STATES:
                yield _v(InvariantCode.E4, name,
                         f"snapshots follow terminal {s.state} #{s.sequence}")
                break


def _e5(b: _Bundle) -> Iterator[Violation]:
    for name, chain in _episodes(b):
        for field in ("policy_id", "policy_hash", "budget_hash", "solver_config_hash"):
            values = {getattr(s, field) for s in chain}
            if len(values) > 1:
                yield _v(InvariantCode.E5, name, f"{field} changes within the episode")


def _e6(b: _Bundle) -> Iterator[Violation]:
    for s in b.records(EpisodeState):
        policy = b.ref(s, "policy_hash")
        if policy is not None and policy.task_id != s.task_id:
            yield _v(InvariantCode.E6, _subject(s),
                     f"policy {_subject(policy)} belongs to task {policy.task_id}")


def _e7(b: _Bundle) -> Iterator[Violation]:
    for _name, chain in _episodes(b):
        for prev, cur in _pairs(chain):
            for dim in _ADDITIVE:
                if getattr(cur.spent, dim) < getattr(prev.spent, dim):
                    yield _v(InvariantCode.E7, _subject(cur), f"spent.{dim} decreased")
            if cur.wall_clock_elapsed_ms < prev.wall_clock_elapsed_ms:
                yield _v(InvariantCode.E7, _subject(cur), "wall_clock_elapsed_ms decreased")


def _aborted_for(s: EpisodeState, reason: AbortReason) -> bool:
    return s.state is EpisodeStatus.ABORTED and s.abort_reason is reason


def _e8(b: _Bundle) -> Iterator[Violation]:
    for s in b.records(EpisodeState):
        budget = b.ref(s, "budget_hash")
        if budget is None:
            continue
        if not _aborted_for(s, AbortReason.BUDGET_EXHAUSTED):
            for dim in _ADDITIVE:
                used = getattr(s.spent, dim) + getattr(s.reserved, dim)
                if used > getattr(budget.limits, dim):
                    yield _v(InvariantCode.E8, _subject(s),
                             f"{dim}: spent + reserved {used} exceeds limit "
                             f"{getattr(budget.limits, dim)}")
        if not _aborted_for(s, AbortReason.WALL_CLOCK_EXHAUSTED):
            if s.wall_clock_elapsed_ms > budget.wall_clock_limit_ms:
                yield _v(InvariantCode.E8, _subject(s),
                         f"wall_clock_elapsed_ms {s.wall_clock_elapsed_ms} exceeds limit "
                         f"{budget.wall_clock_limit_ms}")


def _e11(b: _Bundle) -> Iterator[Violation]:
    for s in b.records(EpisodeState):
        budget = b.ref(s, "budget_hash")
        if budget is None or s.state is not EpisodeStatus.ABORTED:
            continue
        if s.abort_reason is AbortReason.BUDGET_EXHAUSTED:
            positive = [d for d in _ADDITIVE if getattr(budget.limits, d) > 0]
            exhausted = not positive or any(
                getattr(s.spent, d) + getattr(s.reserved, d) >= getattr(budget.limits, d)
                for d in positive
            )
            if not exhausted:
                yield _v(InvariantCode.E11, _subject(s),
                         "budget_exhausted, but no positive-limit dimension reached its limit")
        elif s.abort_reason is AbortReason.WALL_CLOCK_EXHAUSTED:
            if s.wall_clock_elapsed_ms < budget.wall_clock_limit_ms:
                yield _v(InvariantCode.E11, _subject(s),
                         "wall_clock_exhausted, but elapsed wall clock is below its limit")


def _e9(b: _Bundle) -> Iterator[Violation]:
    for s in b.records(EpisodeState):
        for path, _binding in _bindings(s):
            cand = b.ref(s, path)
            if cand is None:
                continue
            if cand.task_id != s.task_id:
                yield _v(InvariantCode.E9, _subject(s),
                         f"{path}: {_subject(cand)} belongs to task {cand.task_id}")
            elif cand.episode_id is not None and cand.episode_id != s.episode_id:
                yield _v(InvariantCode.E9, _subject(s),
                         f"{path}: {_subject(cand)} was produced in episode {cand.episode_id}")


def _e10(b: _Bundle) -> Iterator[Violation]:
    for name, chain in _episodes(b):
        seen: dict[str, list[tuple[int, Any]]] = defaultdict(list)
        for position, s in enumerate(chain):
            for job in s.pending_jobs:
                seen[str(job.job_id)].append(
                    (position, (job.request_hash, job.candidate, job.reserved))
                )
        for job_id in sorted(seen):
            entries = seen[job_id]
            problems = []
            if len({identity for _, identity in entries}) > 1:
                problems.append("request_hash/candidate/reserved change")
            positions = [p for p, _ in entries]
            if positions != list(range(positions[0], positions[0] + len(positions))):
                problems.append("reappears after leaving the pending set")
            if problems:
                yield _v(InvariantCode.E10, name, f"{job_id}: " + "; ".join(problems))


# ---- registry and entry point ------------------------------------------------------------------

Rule = Callable[[_Bundle], Iterable[Violation]]

RULES: Mapping[InvariantCode, Rule] = {
    InvariantCode.B1: _b1,
    InvariantCode.B2: _b2,
    InvariantCode.C1: _c1,
    InvariantCode.C3: _c3,
    InvariantCode.C4: _c4,
    InvariantCode.C5: _c5,
    InvariantCode.C6: _c6,
    InvariantCode.C7: _c7,
    InvariantCode.C8: _c8,
    InvariantCode.P1: _p1,
    InvariantCode.P2A: _p2a,
    InvariantCode.P2B: _p2b,
    InvariantCode.P3: _p3,
    InvariantCode.P4: _p4,
    InvariantCode.P5: _p5,
    InvariantCode.P6: _p6,
    InvariantCode.P7: _p7,
    InvariantCode.P8: _p8,
    InvariantCode.K1: _k1,
    InvariantCode.K2: _k2,
    InvariantCode.K3: _k3,
    InvariantCode.K4: _k4,
    InvariantCode.K5: _k5,
    InvariantCode.K6: _k6,
    InvariantCode.O1: _o1,
    InvariantCode.O2: _o2,
    InvariantCode.O3: _o3,
    InvariantCode.O4: _o4,
    InvariantCode.F1: _f1,
    InvariantCode.F2: _f2,
    InvariantCode.F3: _f3,
    InvariantCode.F4: _f4,
    InvariantCode.F5: _f5,
    InvariantCode.F6: _f6,
    InvariantCode.F7: _f7,
    InvariantCode.F8: _f8,
    InvariantCode.F9: _f9,
    InvariantCode.F10: _f10,
    InvariantCode.F11: _f11,
    InvariantCode.T2: _t2,
    InvariantCode.T3: _t3,
    InvariantCode.T4: _t4,
    InvariantCode.T5: _t5,
    InvariantCode.E1: _e1,
    InvariantCode.E2: _e2,
    InvariantCode.E3: _e3,
    InvariantCode.E4: _e4,
    InvariantCode.E5: _e5,
    InvariantCode.E6: _e6,
    InvariantCode.E7: _e7,
    InvariantCode.E8: _e8,
    InvariantCode.E9: _e9,
    InvariantCode.E10: _e10,
    InvariantCode.E11: _e11,
}


def run_rules(
    records: Iterable[Record], rules: Mapping[InvariantCode, Rule]
) -> tuple[Violation, ...]:
    """Run a chosen rule subset (the rule-removal harness uses this); `check_records` runs all."""
    bundle = _Bundle(records)
    found = {v for rule in rules.values() for v in rule(bundle)}
    return tuple(sorted(found, key=lambda v: (v.code.value, v.subject, v.detail)))


def check_records(records: Iterable[Record]) -> tuple[Violation, ...]:
    """Every cross-record violation in a closed validation bundle, deterministically sorted.

    Raises TypeError for a non-Record value or an unsupported Record type; never raises for an
    inconsistent bundle.
    """
    return run_rules(records, RULES)
