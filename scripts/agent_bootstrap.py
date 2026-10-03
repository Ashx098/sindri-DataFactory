#!/usr/bin/env python3
"""Print the canonical context a fresh coding-agent session must read (AGENT_KICKOFF.md).

Usage:
    python scripts/agent_bootstrap.py [TASK-ID] [--path src/sindri/judge] [--brief]

Prints, in order: governing documents, project state and repo map, the authoritative phase state
(implementation/current.yaml), the implementation plan, kickoff protocol and active phase file,
the task packet and its handoff, every AGENTS.md from the root down to --path, accepted ADRs and
git state. Stdlib only so it runs before `uv sync`.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOVERNING = ["PRINCIPLES.md", "AGENTS.md", "ARCHITECTURE_GUARDRAILS.md"]
STATE = [
    "docs/PROJECT_STATE.md",
    "docs/REPO_MAP.md",
    "implementation/current.yaml",
    "docs/implementation/CURRENT_PHASE.md",
    "docs/implementation/IMPLEMENTATION_PLAN.md",
    "docs/implementation/AGENT_KICKOFF.md",
]


def section(title: str, body: str) -> None:
    print(f"\n{'=' * 100}\n## {title}\n{'=' * 100}\n{body.rstrip()}")


def show(rel: str, brief: bool = False) -> None:
    path = ROOT / rel
    if not path.exists():
        section(rel, "(missing)")
    else:
        section(rel, "(exists; omitted by --brief)" if brief else path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return "(git not available)"
    return (out.stdout or out.stderr).strip() or "(empty)"


def active_phase() -> str | None:
    current = ROOT / "implementation/current.yaml"
    if not current.exists():
        return None
    m = re.search(r"(?m)^active_phase:\s*(\S+)", current.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def agents_chain(target: str) -> list[Path]:
    """Every nested AGENTS.md between the root (printed with GOVERNING) and the target path."""
    chain = []
    current = ROOT
    for part in Path(target).parts:
        current = current / part
        if (current / "AGENTS.md").exists():
            chain.append(current / "AGENTS.md")
    return chain


def accepted_adrs() -> str:
    lines = []
    for adr in sorted((ROOT / "docs/adr").glob("[0-9]*.md")):
        if adr.name.startswith("0000"):
            continue
        text = adr.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        status = next(
            (ln.split(":", 1)[1].strip() for ln in text.splitlines() if ln.startswith("- Status:")),
            "unknown",
        )
        lines.append(f"- [{status}] {title}  ({adr.relative_to(ROOT)})")
    return "\n".join(lines) or "(none)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task_id", nargs="?", help="e.g. SIN-P1.1-001")
    parser.add_argument("--path", default="", help="directory you will edit, e.g. src/sindri/judge")
    parser.add_argument(
        "--brief", action="store_true", help="list governing docs instead of printing them"
    )
    args = parser.parse_args()

    print("# Sindri Factory: session bootstrap")
    print("Repository state wins over remembered chat. Escalate conflicts; do not silently choose.")

    for rel in GOVERNING:
        show(rel, args.brief)
    for rel in STATE:
        show(rel)

    phase = active_phase()
    phases_dir = ROOT / "docs/implementation/phases"
    phase_files = sorted(phases_dir.glob(f"{phase}_*.md")) if phase else []
    if phase_files:
        show(str(phase_files[0].relative_to(ROOT)))
    else:
        section("Active phase file", f"(none found for active_phase={phase})")

    if args.task_id:
        packet = ROOT / "docs/tasks" / f"{args.task_id}.md"
        section("Task packet", packet.read_text(encoding="utf-8") if packet.exists()
                else f"(no packet docs/tasks/{args.task_id}.md: do not start without one)")
        handoff = ROOT / "docs/handoffs" / f"{args.task_id}.md"
        section("Handoff", handoff.read_text(encoding="utf-8") if handoff.exists() else "(none)")
    else:
        section("No TASK-ID given", "Sessions get a TASK-ID; see scripts/show_ready_tasks.py.")

    if args.path:
        chain = agents_chain(args.path)
        for path in chain:
            show(str(path.relative_to(ROOT)))
        if not chain:
            section(f"Local AGENTS.md for {args.path}", "(none beyond root)")

    section("Accepted ADRs", accepted_adrs())
    section("git", "\n".join([
        f"branch: {git('branch', '--show-current')}",
        "status:\n" + git("status", "--short"),
        "recent commits:\n" + git("log", "--oneline", "-10"),
    ]))
    section(
        "Before editing",
        "Restate outcome, non-goals, dependencies, allowed paths and verification commands.",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
