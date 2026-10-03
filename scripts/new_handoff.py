#!/usr/bin/env python3
"""Create docs/handoffs/<TASK-ID>.md from the template, pre-filled with git state.

Usage:
    python scripts/new_handoff.py SIN-P1.1-001

One handoff per task (docs/MULTI_AGENT_WORKFLOW.md); refuses to overwrite an existing one, which
should be updated in place instead. Stdlib only.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/handoffs/TEMPLATE.md"


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return "UNKNOWN (git not available)"
    return out.stdout.strip() or "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task_id")
    args = parser.parse_args()

    if not (ROOT / "docs/tasks" / f"{args.task_id}.md").exists():
        print(f"error: no task packet docs/tasks/{args.task_id}.md", file=sys.stderr)
        return 1
    out = ROOT / "docs/handoffs" / f"{args.task_id}.md"
    if out.exists():
        print(f"error: exists, update it in place: {out.relative_to(ROOT)}", file=sys.stderr)
        return 1

    dirty = git("status", "--short")
    text = TEMPLATE.read_text(encoding="utf-8").replace("TASK-ID", args.task_id)
    for old, new in [
        ("- Branch/worktree:", f"- Branch/worktree: {git('branch', '--show-current')}"),
        ("- HEAD commit:", f"- HEAD commit: {git('rev-parse', 'HEAD')}"),
        ("- Dirty files, if any:", f"- Dirty files, if any:\n```\n{dirty}\n```"),
    ]:
        text = text.replace(old, new, 1)
    out.write_text(text, encoding="utf-8")
    print(out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
