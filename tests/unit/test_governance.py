"""Governance consistency (ADR-0003).

implementation/current.yaml is the only phase-state authority and implementation/task_board.yaml the
only task-status list. These tests keep the board, the task packets and the phase state consistent
so a fresh agent cannot be handed a task whose phase or dependencies are not open.
"""

import re
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TASK_ID = re.compile(r"SIN-((?:P[1-6]|B0)\.[0-9]+)-[0-9]{3}")
TASK_STATUSES = {"planned", "ready", "active", "blocked", "review", "merged", "verified", "closed"}
DONE = {"merged", "verified", "closed"}
PHASE_STATES = {"NOT_STARTED", "ACTIVE", "GATE_REVIEW", "COMPLETE", "BLOCKED"}


def _load(rel: str) -> Any:
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def current() -> dict[str, Any]:
    data: dict[str, Any] = _load("implementation/current.yaml")
    return data


@pytest.fixture(scope="module")
def tasks() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = _load("implementation/task_board.yaml")["tasks"] or []
    return data


def test_phase_state_is_well_formed(current: dict[str, Any]) -> None:
    phases = current["phases"]
    assert current["active_phase"] in phases
    assert {p["state"] for p in phases.values()} <= PHASE_STATES
    assert set(phases) == set(_load("implementation/phase_graph.yaml")["phases"])


def test_phase_graph_order_is_respected(current: dict[str, Any]) -> None:
    """A phase may start only when every phase gate it depends on is COMPLETE."""
    graph = _load("implementation/phase_graph.yaml")["phases"]
    states = {pid: p["state"] for pid, p in current["phases"].items()}
    for pid, spec in graph.items():
        if states[pid] == "NOT_STARTED":
            continue
        for dep in spec["depends_on"]:
            if dep.endswith(".G"):
                assert states[dep[:-2]] == "COMPLETE", f"{pid} is {states[pid]} before {dep}"


def test_every_task_is_well_formed(tasks: list[dict[str, Any]]) -> None:
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    for t in tasks:
        m = TASK_ID.fullmatch(t["id"])
        assert m, f"bad id {t['id']}"
        assert t["subphase"] == m.group(1) and t["phase"] == m.group(1).split(".")[0], t["id"]
        assert t["status"] in TASK_STATUSES, t["id"]
        assert t["packet"] == f"docs/tasks/{t['id']}.md", t["id"]
        assert (ROOT / t["packet"]).exists(), f"missing packet for {t['id']}"


def test_every_packet_is_on_the_board(tasks: list[dict[str, Any]]) -> None:
    on_board = {t["id"] for t in tasks}
    packets = {p.stem for p in (ROOT / "docs/tasks").glob("SIN-*.md")}
    assert packets <= on_board, f"packets missing from task board: {sorted(packets - on_board)}"


def test_ready_tasks_are_actually_ready(
    current: dict[str, Any], tasks: list[dict[str, Any]]
) -> None:
    """READY requires an ACTIVE phase and every dependency done (task) or COMPLETE (gate)."""
    by_id = {t["id"]: t for t in tasks}
    phases = current["phases"]
    for t in (t for t in tasks if t["status"] in {"ready", "active"}):
        assert phases[t["phase"]]["state"] == "ACTIVE", f"{t['id']} open in non-active phase"
        for dep in t["depends_on"]:
            if dep.endswith(".G"):
                assert phases[dep[:-2]]["state"] == "COMPLETE", f"{t['id']} waits on {dep}"
            else:
                assert by_id[dep]["status"] in DONE, f"{t['id']} waits on {dep}"


def test_markdown_does_not_restate_phase_state() -> None:
    """Only current.yaml may carry phase-state values (no duplicate source of truth)."""
    pattern = re.compile(r"Phase state:|Bootstrap gate:|Canonical phase:")
    for rel in ["docs/implementation/CURRENT_PHASE.md", "docs/PROJECT_STATE.md"]:
        assert not pattern.search((ROOT / rel).read_text(encoding="utf-8")), rel


def test_show_ready_tasks_parser_agrees_with_yaml(tasks: list[dict[str, Any]]) -> None:
    """The stdlib parser in scripts/ must read the board the same way as a real YAML parser."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from show_ready_tasks import load_tasks
    finally:
        sys.path.pop(0)
    parsed = load_tasks((ROOT / "implementation/task_board.yaml").read_text(encoding="utf-8"))
    assert [(t["id"], t["status"]) for t in parsed] == [(t["id"], t["status"]) for t in tasks]


ADR_STATUSES = {"proposed", "reviewed", "accepted", "rejected", "superseded"}


def test_adr_statuses_are_valid() -> None:
    for adr in sorted((ROOT / "docs/adr").glob("[0-9]*.md")):
        if adr.name.startswith("0000"):
            continue
        lines = adr.read_text(encoding="utf-8").splitlines()
        line = next((ln for ln in lines if ln.startswith("- Status:")), None)
        assert line, f"{adr.name} has no status line"
        status = line.split(":", 1)[1].split()[0]
        assert status in ADR_STATUSES, f"{adr.name}: {status}"
        if status in {"accepted", "rejected"}:
            assert "- Accepted by:" in adr.read_text(encoding="utf-8"), (
                f"{adr.name} is {status} without an 'Accepted by:' line naming the owner"
            )
