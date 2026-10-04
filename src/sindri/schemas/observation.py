"""Observation: the authenticated record of one attempted execution of one declared policy check.

Scope (ADR-0005): only executions of a declared EvaluationPolicy check are Observations. Waveform
and coverage queries, formal `cover` runs and ad-hoc queries are separately typed results defined by
their first consumer. `quality` is not an Observation kind in v1 (O11).

An Observation records an *attempted* execution (O15): PASS needs a complete typed execution report;
FAIL needs a report (possibly partial) carrying candidate-attributed failure evidence; INCONCLUSIVE
needs a report showing the unmet bound; TOOL_ERROR / TIMEOUT / UNSUPPORTED may carry no report or a
partial one, which never counts as PASS/FAIL evidence. The raw `ToolStatus` is never rewritten
(ADR-0002): TIMEOUT stays TIMEOUT.

Immutable and non-versioned (O12): a rerun is a new Observation. Authentication is the evidence
store's write authority (O13), not a field in this record. Hidden-check Observations are
judge-side protected (O14). Decisions O1–O15, R1–R5: docs/tasks/SIN-P1.1-005.md.
"""

import re
from datetime import datetime
from enum import StrEnum, unique
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictBool, StrictInt, model_validator

from sindri.core.ids import (
    CandidateId,
    CheckId,
    ConfigurationId,
    ContentId,
    ObservationId,
    PolicyId,
    PropertyId,
    TestId,
    ToolProfileId,
    canonical_json_id,
)
from sindri.core.status import ToolStatus
from sindri.schemas._base import NonEmptyText, Record, StrictModel
from sindri.schemas.policy import CheckKind, FormalMode, Visibility
from sindri.schemas.task import EditPath

EXECUTION_KEY_KIND = "observation_execution_key_v1"
MAX_DIAGNOSTICS = 200
MAX_SUMMARY_CHARS = 500

NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveInt = Annotated[StrictInt, Field(ge=1)]


@unique
class ObservationAction(StrEnum):
    """Check-execution tools of the Tool Gateway (master §8 F1). Query tools are not here."""

    INTEGRITY_SCAN = "integrity_scan"
    COMPILE = "compile"
    LINT = "lint"
    SYNTH = "synth"
    RUN_SIM = "run_sim"
    RUN_FORMAL = "run_formal"
    CHECK_EQUIV = "check_equiv"


# R2: closed one-to-one mapping. `quality` has no entry: it is not an Observation kind in v1.
ACTION_FOR_KIND: dict[CheckKind, ObservationAction] = {
    CheckKind.INTEGRITY_SCAN: ObservationAction.INTEGRITY_SCAN,
    CheckKind.PARSE_ELABORATE: ObservationAction.COMPILE,
    CheckKind.LINT: ObservationAction.LINT,
    CheckKind.SYNTHESIS: ObservationAction.SYNTH,
    CheckKind.DIRECTED_SIM: ObservationAction.RUN_SIM,
    CheckKind.RANDOM_SIM: ObservationAction.RUN_SIM,
    CheckKind.FORMAL: ObservationAction.RUN_FORMAL,
    CheckKind.EQUIVALENCE: ObservationAction.CHECK_EQUIV,
}
SIM_KINDS = frozenset({CheckKind.DIRECTED_SIM, CheckKind.RANDOM_SIM})
STRUCTURAL_KINDS = frozenset(
    {CheckKind.INTEGRITY_SCAN, CheckKind.PARSE_ELABORATE, CheckKind.LINT, CheckKind.SYNTHESIS}
)


@unique
class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@unique
class DiagnosticCategory(StrEnum):
    """Who a diagnostic is about. Only `candidate` diagnostics attribute a failure to the RTL."""

    CANDIDATE = "candidate"
    EVALUATOR = "evaluator"
    INFRASTRUCTURE = "infrastructure"


class Diagnostic(StrictModel):
    severity: Severity
    category: DiagnosticCategory
    code: NonEmptyText | None
    message: NonEmptyText
    path: EditPath | None
    line: PositiveInt | None


@unique
class EvidenceKind(StrEnum):
    COUNTEREXAMPLE_TRACE = "counterexample_trace"
    WAVEFORM = "waveform"
    TOOL_REPORT = "tool_report"


class EvidenceRef(StrictModel):
    kind: EvidenceKind
    hash: ContentId


# ---- execution reports (O7) ---------------------------------------------------------------------


class TestResult(StrictModel):
    test_id: TestId
    outcome: ToolStatus


class SimulationReport(StrictModel):
    """`expected_test_ids` is the declared inventory; `test_results` what the tool reported."""

    report_kind: Literal["simulation"]
    expected_test_ids: Annotated[tuple[TestId, ...], Field(min_length=1)]
    test_results: tuple[TestResult, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        _unique(self.expected_test_ids, "expected_test_ids")
        ran = [r.test_id for r in self.test_results]
        _unique(tuple(ran), "test_results")
        unexpected = set(ran) - set(self.expected_test_ids)
        if unexpected:
            raise ValueError(f"results for tests outside the expected inventory: {unexpected}")
        return self

    def complete(self) -> bool:
        return {r.test_id for r in self.test_results} == set(self.expected_test_ids)

    def failed(self) -> bool:
        return any(r.outcome is ToolStatus.FAIL for r in self.test_results)

    def all_pass(self) -> bool:
        return all(r.outcome is ToolStatus.PASS for r in self.test_results)


class PropertyResult(StrictModel):
    property_id: PropertyId
    outcome: ToolStatus


class FormalReport(StrictModel):
    """BMC carries requested/reached depth; prove carries `proof_closed` (exactly one applies)."""

    report_kind: Literal["formal"]
    mode: FormalMode
    requested_depth: PositiveInt | None
    reached_depth: NonNegativeInt | None
    proof_closed: StrictBool | None
    expected_property_ids: Annotated[tuple[PropertyId, ...], Field(min_length=1)]
    property_results: tuple[PropertyResult, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        bmc = self.mode is FormalMode.BMC
        if bmc and (self.requested_depth is None or self.reached_depth is None):
            raise ValueError("bmc reports need requested_depth and reached_depth")
        if bmc and self.proof_closed is not None:
            raise ValueError("bmc reports carry no proof_closed")
        if not bmc and (self.proof_closed is None):
            raise ValueError("prove reports need proof_closed")
        if not bmc and (self.requested_depth is not None or self.reached_depth is not None):
            raise ValueError("prove reports carry no depths")
        _unique(self.expected_property_ids, "expected_property_ids")
        checked = [r.property_id for r in self.property_results]
        _unique(tuple(checked), "property_results")
        unexpected = set(checked) - set(self.expected_property_ids)
        if unexpected:
            raise ValueError(f"results for properties outside the expected inventory: {unexpected}")
        return self

    def bound_met(self) -> bool:
        if self.mode is FormalMode.BMC:
            assert self.reached_depth is not None and self.requested_depth is not None
            return self.reached_depth >= self.requested_depth
        return self.proof_closed is True

    def complete(self) -> bool:
        checked = {r.property_id for r in self.property_results}
        return checked == set(self.expected_property_ids) and self.bound_met()

    def failed(self) -> bool:
        return any(r.outcome is ToolStatus.FAIL for r in self.property_results)

    def all_pass(self) -> bool:
        return all(r.outcome is ToolStatus.PASS for r in self.property_results)


class EquivalenceReport(StrictModel):
    """The relation is committed by policy, contract, evaluator bundle and golden (R4)."""

    report_kind: Literal["equivalence"]
    proved: StrictBool


class StructuralReport(StrictModel):
    """Lint/parse/synth/integrity counts. Latch/blackbox counts exist for synthesis only."""

    report_kind: Literal["structural"]
    error_count: NonNegativeInt
    warning_count: NonNegativeInt
    latch_count: NonNegativeInt | None
    blackbox_count: NonNegativeInt | None


ExecutionReport = Annotated[
    SimulationReport | FormalReport | EquivalenceReport | StructuralReport,
    Field(discriminator="report_kind"),
]


def _report_kind_for(kind: CheckKind) -> str:
    if kind in SIM_KINDS:
        return "simulation"
    if kind is CheckKind.FORMAL:
        return "formal"
    if kind is CheckKind.EQUIVALENCE:
        return "equivalence"
    return "structural"


# ---- execution key (O6) -------------------------------------------------------------------------


def observation_execution_key(
    *,
    candidate_manifest_hash: ContentId,
    source_hash: ContentId,
    dependency_hash: ContentId | None,
    policy_hash: ContentId,
    check_id: CheckId,
    configuration_id: ConfigurationId,
    action: ObservationAction,
    tool_profile_hash: ContentId,
    tool_image_digest: ContentId,
    adapter_hash: ContentId,
    evaluator_bundle_hash: ContentId,
    seed: int | None,
    formal_mode: FormalMode | None,
    formal_depth: int | None,
    wall_time_limit_ms: int,
) -> ContentId:
    """The execution *request* identity; the only implementation of the construction.

    Result fields (observation_id, started_at, duration_ms, status, summary, diagnostics, log and
    evidence refs, report) are never part of it.
    """
    return canonical_json_id(
        {
            "kind": EXECUTION_KEY_KIND,
            "candidate_manifest_hash": str(candidate_manifest_hash),
            "source_hash": str(source_hash),
            "dependency_hash": None if dependency_hash is None else str(dependency_hash),
            "policy_hash": str(policy_hash),
            "check_id": str(check_id),
            "configuration_id": str(configuration_id),
            "action": action.value,
            "tool_profile_hash": str(tool_profile_hash),
            "tool_image_digest": str(tool_image_digest),
            "adapter_hash": str(adapter_hash),
            "evaluator_bundle_hash": str(evaluator_bundle_hash),
            "seed": seed,
            "formal_mode": None if formal_mode is None else formal_mode.value,
            "formal_depth": formal_depth,
            "wall_time_limit_ms": wall_time_limit_ms,
        }
    )


_UTC_SECOND = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def _utc_second(value: str) -> str:
    """Exactly `YYYY-MM-DDTHH:MM:SSZ`; strptime alone would also accept unpadded forms."""
    message = f"started_at must look like 2026-10-04T12:00:00Z: {value!r}"
    if not _UTC_SECOND.fullmatch(value):
        raise ValueError(message)
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(message) from exc
    return value


def _summary(value: str) -> str:
    if len(value) > MAX_SUMMARY_CHARS:
        raise ValueError(f"summary exceeds {MAX_SUMMARY_CHARS} characters")
    return value


def _unique(values: tuple[object, ...], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} contains duplicates")


class Observation(Record):
    # binding: exact candidate (O2) and exact policy check/configuration (O3, O4)
    observation_id: ObservationId
    candidate_id: CandidateId
    candidate_manifest_hash: ContentId
    source_hash: ContentId
    dependency_hash: ContentId | None
    policy_id: PolicyId
    policy_hash: ContentId
    check_id: CheckId
    configuration_id: ConfigurationId
    check_kind: CheckKind
    visibility: Visibility

    # executor (O5)
    action: ObservationAction
    tool_profile_id: ToolProfileId
    tool_profile_hash: ContentId
    tool_image_digest: ContentId
    adapter_version: NonEmptyText
    adapter_hash: ContentId

    # execution inputs (O6, O9, R1)
    evaluator_bundle_hash: ContentId
    seed: StrictInt | None
    formal_mode: FormalMode | None
    formal_depth: PositiveInt | None
    wall_time_limit_ms: PositiveInt
    execution_key: ContentId

    # result
    started_at: Annotated[NonEmptyText, AfterValidator(_utc_second)]
    duration_ms: NonNegativeInt
    status: ToolStatus
    summary: Annotated[NonEmptyText, AfterValidator(_summary)]
    diagnostics: Annotated[tuple[Diagnostic, ...], Field(max_length=MAX_DIAGNOSTICS)]
    diagnostics_truncated: StrictBool
    log_ref: ContentId
    evidence_refs: tuple[EvidenceRef, ...]
    execution_report: ExecutionReport | None

    def computed_execution_key(self) -> ContentId:
        return observation_execution_key(
            candidate_manifest_hash=self.candidate_manifest_hash,
            source_hash=self.source_hash,
            dependency_hash=self.dependency_hash,
            policy_hash=self.policy_hash,
            check_id=self.check_id,
            configuration_id=self.configuration_id,
            action=self.action,
            tool_profile_hash=self.tool_profile_hash,
            tool_image_digest=self.tool_image_digest,
            adapter_hash=self.adapter_hash,
            evaluator_bundle_hash=self.evaluator_bundle_hash,
            seed=self.seed,
            formal_mode=self.formal_mode,
            formal_depth=self.formal_depth,
            wall_time_limit_ms=self.wall_time_limit_ms,
        )

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        self._check_request_shape()
        if self.execution_key != self.computed_execution_key():
            raise ValueError(f"execution_key does not match the {EXECUTION_KEY_KIND} construction")
        if self.diagnostics_truncated and len(self.diagnostics) != MAX_DIAGNOSTICS:
            raise ValueError(f"diagnostics_truncated requires exactly {MAX_DIAGNOSTICS} entries")
        self._check_status()
        return self

    # -- request shape: kind, action, report variant, seed, formal fields ---------------------

    def _check_request_shape(self) -> None:
        kind = self.check_kind
        if kind is CheckKind.QUALITY:
            raise ValueError("quality is not an Observation check kind in v1 (O11)")
        if self.action is not ACTION_FOR_KIND[kind]:
            raise ValueError(f"{kind} is executed by {ACTION_FOR_KIND[kind]}, not {self.action}")
        if self.execution_report is not None:
            if self.execution_report.report_kind != _report_kind_for(kind):
                raise ValueError(f"{kind} needs a {_report_kind_for(kind)} report")
        if (kind in SIM_KINDS) != (self.seed is not None):
            raise ValueError("simulation observations need exactly one seed; others have none (R1)")
        if kind is CheckKind.FORMAL:
            if self.formal_mode is None:
                raise ValueError("formal observations need formal_mode")
            if (self.formal_mode is FormalMode.BMC) != (self.formal_depth is not None):
                raise ValueError("bmc needs formal_depth; prove takes none")
            report = self.execution_report
            if isinstance(report, FormalReport) and (
                report.mode is not self.formal_mode or report.requested_depth != self.formal_depth
            ):
                raise ValueError("formal report mode/requested depth differ from the request")
        elif self.formal_mode is not None or self.formal_depth is not None:
            raise ValueError("only formal observations carry formal_mode/formal_depth")
        report = self.execution_report
        if isinstance(report, StructuralReport):
            synth = kind is CheckKind.SYNTHESIS
            if synth != (report.latch_count is not None and report.blackbox_count is not None):
                raise ValueError("latch/blackbox counts belong to synthesis reports only")
            if not synth and (report.latch_count is not None or report.blackbox_count is not None):
                raise ValueError("latch/blackbox counts belong to synthesis reports only")

    # -- status matrix (O11, R3) ---------------------------------------------------------------

    def _has_counterexample(self) -> bool:
        return any(e.kind is EvidenceKind.COUNTEREXAMPLE_TRACE for e in self.evidence_refs)

    def _has_candidate_error(self) -> bool:
        return any(
            d.severity is Severity.ERROR and d.category is DiagnosticCategory.CANDIDATE
            for d in self.diagnostics
        )

    def _failure_locus(self) -> bool:
        """Candidate-attributed failure evidence, in any form."""
        report = self.execution_report
        report_failed = isinstance(report, SimulationReport | FormalReport) and report.failed()
        return report_failed or self._has_counterexample() or self._has_candidate_error()

    def _check_status(self) -> None:
        status, kind, report = self.status, self.check_kind, self.execution_report

        if status is ToolStatus.PASS:
            if report is None:
                raise ValueError("PASS needs a complete execution report")
            if isinstance(report, SimulationReport | FormalReport):
                if not report.complete():
                    raise ValueError("PASS needs a complete report (all expected, bound met)")
                if not report.all_pass():
                    raise ValueError("PASS needs every test/property to pass")
            if isinstance(report, EquivalenceReport) and not report.proved:
                raise ValueError("equivalence PASS needs proved=true")
            if isinstance(report, StructuralReport):
                if report.error_count != 0:
                    raise ValueError("structural PASS needs zero errors")
                # Master §14 J1: synthesis with no black boxes. Latches are not judged here: only
                # *unexpected* latches fail, and "expected" needs evaluator/profile semantics
                # (P1.4/P1.6 follow-up); the adapter will then emit a candidate error.
                if kind is CheckKind.SYNTHESIS and report.blackbox_count != 0:
                    raise ValueError("synthesis PASS needs zero black boxes")
            if any(d.severity is Severity.ERROR for d in self.diagnostics):
                raise ValueError("PASS cannot carry error diagnostics")
            if self._has_counterexample():
                raise ValueError("PASS cannot carry a counterexample")
            return

        if status is ToolStatus.FAIL:
            if report is None:
                raise ValueError("FAIL needs an execution report (it may be partial)")
            if isinstance(report, SimulationReport) and not report.failed():
                raise ValueError("simulation FAIL needs at least one failing test")
            if isinstance(report, FormalReport) and not (
                report.failed() and self._has_counterexample()
            ):
                raise ValueError("formal FAIL needs a failing property and a counterexample")
            if isinstance(report, EquivalenceReport) and (
                report.proved or not self._has_counterexample()
            ):
                raise ValueError("equivalence FAIL needs proved=false and a counterexample")
            if isinstance(report, StructuralReport):
                violations = report.error_count > 0
                if kind is CheckKind.SYNTHESIS:
                    violations = violations or bool(report.blackbox_count) or bool(
                        report.latch_count
                    )
                if not (violations and self._has_candidate_error()):
                    raise ValueError(
                        "structural FAIL needs a candidate error and a structural violation"
                    )
            return

        # Every remaining status is a non-verdict: it must not carry candidate failure evidence.
        if self._failure_locus():
            raise ValueError(f"{status} cannot carry candidate failure evidence")

        if status is ToolStatus.INCONCLUSIVE:
            if kind not in (CheckKind.FORMAL, CheckKind.EQUIVALENCE):
                raise ValueError("INCONCLUSIVE is only for formal and equivalence checks")
            if report is None:
                raise ValueError("INCONCLUSIVE needs a report showing the unmet bound")
            if isinstance(report, FormalReport) and report.bound_met():
                raise ValueError("INCONCLUSIVE formal report must show the unmet bound")
            if isinstance(report, EquivalenceReport) and report.proved:
                raise ValueError("INCONCLUSIVE equivalence cannot be proved")
        elif status is ToolStatus.TOOL_ERROR:
            if not any(d.category is DiagnosticCategory.INFRASTRUCTURE for d in self.diagnostics):
                raise ValueError("TOOL_ERROR needs an infrastructure diagnostic")
        elif status is ToolStatus.TIMEOUT:
            if self.duration_ms < self.wall_time_limit_ms:
                raise ValueError("TIMEOUT needs duration_ms >= wall_time_limit_ms")
        elif status is ToolStatus.UNSUPPORTED:
            if not any(d.code is not None for d in self.diagnostics):
                raise ValueError("UNSUPPORTED needs a diagnostic code naming the capability")
