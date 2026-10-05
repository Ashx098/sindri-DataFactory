"""SIN-P1.6-001: reproduce the FIFO seed's five-configuration Icarus kill matrix.

Marked `eda`; skipped when Icarus Verilog (`iverilog`, `vvp`) is not installed (CI today). The
verdict comes only from the F7 protocol (`_protocol.py`) checked against the configuration-scoped
inventory, never from the process exit code.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.eda._protocol import verdict

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "evals" / "fixtures" / "fifo"
INVENTORY = json.loads((SEED / "tb" / "tests.json").read_text())
MUTANTS = json.loads((SEED / "mutants" / "manifest.json").read_text())
KNOWN_BAD = json.loads((SEED / "known_bad" / "manifest.json").read_text())
CONFIGS = list(INVENTORY["configurations"])

pytestmark = [
    pytest.mark.eda,
    pytest.mark.skipif(not (shutil.which("iverilog") and shutil.which("vvp")),
                       reason="Icarus Verilog (iverilog/vvp) not installed"),
]


def _simulate(tmp_path: Path, testbench: str, design: str, cfg: str) -> tuple[str, str]:
    a = INVENTORY["configurations"][cfg]["assignments"]
    out = tmp_path / f"{Path(design).stem}_{cfg}.vvp"
    compiled = subprocess.run(
        ["iverilog", "-g2005", "-Wall", f"-Ptb.WIDTH={a['WIDTH']}", f"-Ptb.DEPTH={a['DEPTH']}",
         "-o", str(out), testbench, design],
        cwd=SEED, capture_output=True, text=True, timeout=60, check=False)
    assert compiled.returncode == 0 and "error" not in compiled.stderr, compiled.stderr
    run = subprocess.run(["vvp", "-n", str(out)], cwd=SEED, capture_output=True, text=True,
                         timeout=60, check=False)
    expected = INVENTORY["configurations"][cfg]["expected_tests"]
    return verdict(run.stdout, expected).status, run.stdout


CORRECT = [(d, c) for d in ("rtl/fifo_ref.v", "rtl/fifo_alt.v") for c in CONFIGS]
KILLS = [(m["file"], c, m["kill_matrix"][c]) for m in MUTANTS["mutants"] for c in CONFIGS]
BAD = [(d, c, v) for d, row in KNOWN_BAD["expected_verdicts"].items() for c, v in row.items()]


@pytest.mark.parametrize(("design", "cfg"), CORRECT, ids=[f"{d}-{c}" for d, c in CORRECT])
def test_correct_controls_pass(tmp_path: Path, design: str, cfg: str) -> None:
    status, out = _simulate(tmp_path, "tb/tb_fifo.v", design, cfg)
    assert status == "PASS", out[-600:]


@pytest.mark.parametrize(("design", "cfg", "expected"), KILLS,
                         ids=[f"{Path(d).stem}-{c}" for d, c, _ in KILLS])
def test_mutant_kill_matrix_reproduces(tmp_path: Path, design: str, cfg: str,
                                       expected: str) -> None:
    status, out = _simulate(tmp_path, "tb/tb_fifo.v", design, cfg)
    assert status == {"killed": "FAIL", "survived": "PASS"}[expected], out[-600:]


@pytest.mark.parametrize(("design", "cfg", "expected"), BAD,
                         ids=[f"xblind-{Path(d).stem}-{c}" for d, c, _ in BAD])
def test_quarantined_xblind_testbench_verdicts(tmp_path: Path, design: str, cfg: str,
                                               expected: str) -> None:
    status, out = _simulate(tmp_path, "known_bad/tb_fifo_xblind.v", design, cfg)
    assert status == expected, out[-600:]


def test_xblind_fake_passes_m4_where_strict_kills_it(tmp_path: Path) -> None:
    m4 = "mutants/m4_rdptr_not_reset.v"
    for cfg in CONFIGS:
        bad, _ = _simulate(tmp_path, "known_bad/tb_fifo_xblind.v", m4, cfg)
        good, _ = _simulate(tmp_path, "tb/tb_fifo.v", m4, cfg)
        assert (bad, good) == ("PASS", "FAIL"), cfg
