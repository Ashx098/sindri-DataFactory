# Current Phase

> The active phase, phase states and gates live **only** in `implementation/current.yaml`; task
> status lives **only** in `implementation/task_board.yaml` (ADR-0003). This file carries the
> narrative that does not fit there. Do not copy state values into it.

Quick view:
```bash
cat implementation/current.yaml
python scripts/show_ready_tasks.py --all
```

## Notes for the active phase
- B0 work is complete and awaiting coordinator review in `docs/implementation/gates/B0.G.md`.
- After B0.G is COMPLETE, the first READY task is `SIN-P1.1-001` (core schemas). Per the P1
  dependency graph, P1.2, P1.3 and P1.6 can then be opened in parallel worktrees.

## Rule
Only tasks with status `ready` on the task board may be assigned to coding agents.
