#!/usr/bin/env python3
"""List tasks on implementation/task_board.yaml, READY ones first.

Usage:
    python scripts/show_ready_tasks.py [--all]

Stdlib only, so it reads the board's restricted format (one `- id:` block per task with flat
`key: value` lines). tests/unit/test_governance.py validates the board with a real YAML parser.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "implementation/task_board.yaml"


def load_tasks(text: str) -> list[dict[str, str]]:
    tasks = []
    for block in re.split(r"(?m)^\s*-\s+(?=id:)", text)[1:]:
        task = {}
        for line in block.splitlines():
            m = re.match(r"\s*(\w+):\s*(.*?)\s*$", line)
            if m and not line.lstrip().startswith("#"):
                task[m.group(1)] = m.group(2).strip("\"'")
        tasks.append(task)
    return tasks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true", help="show every task, not only ready ones")
    args = ap.parse_args()

    if not BOARD.exists():
        print(f"error: {BOARD.relative_to(ROOT)} not found", file=sys.stderr)
        return 1
    tasks = load_tasks(BOARD.read_text(encoding="utf-8"))
    shown = tasks if args.all else [t for t in tasks if t.get("status") == "ready"]
    if not shown:
        print("No READY tasks." if not args.all else "Task board is empty.")
        return 0
    for t in sorted(shown, key=lambda t: (t.get("status") != "ready", t.get("id", ""))):
        print(f"{t.get('status', '?'):9} {t.get('id', '?'):15} {t.get('title', '')}")
        print(f"{'':9} depends_on={t.get('depends_on', '[]')}  packet={t.get('packet', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
