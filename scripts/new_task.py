#!/usr/bin/env python3
"""Create a bounded Sindri task packet from the repository template.

Usage:
    python scripts/new_task.py SIN-P1.4-003 "Verilator lint adapter"

Phase and subphase are derived from the ID. The packet is created with status `planned`; the
coordinator adds it to implementation/task_board.yaml and marks it ready. Stdlib only.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/tasks/TASK_TEMPLATE.md"
TASK_ID = re.compile(r"SIN-((?:P[1-6]|B0)\.[0-9]+)-[0-9]{3}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("task_id", help="SIN-P<phase>.<subphase>-<nnn> or SIN-B0.<n>-<nnn>")
    ap.add_argument("title")
    args = ap.parse_args()

    match = TASK_ID.fullmatch(args.task_id)
    if not match:
        print("error: task_id must look like SIN-P1.4-003 or SIN-B0.1-001", file=sys.stderr)
        return 1
    subphase = match.group(1)
    phase = subphase.split(".")[0]

    out = ROOT / "docs/tasks" / f"{args.task_id}.md"
    if out.exists():
        print(f"error: exists: {out.relative_to(ROOT)}", file=sys.stderr)
        return 1

    text = TEMPLATE.read_text(encoding="utf-8")
    for old, new in [
        ("TASK-ID — Short title", f"{args.task_id} — {args.title}"),
        ("- Phase: `P?`", f"- Phase: `{phase}`"),
        ("- Subphase: `P?.?`", f"- Subphase: `{subphase}`"),
    ]:
        if old not in text:
            print(f"error: template no longer contains {old!r}", file=sys.stderr)
            return 1
        text = text.replace(old, new, 1)
    out.write_text(text, encoding="utf-8")
    print(out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
