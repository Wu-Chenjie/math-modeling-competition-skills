import json
import subprocess
import sys
from pathlib import Path


def test_simulation_contract_and_determinism():
    out1 = subprocess.check_output([sys.executable, "model_simulation.py"], text=True)
    out2 = subprocess.check_output([sys.executable, "model_simulation.py"], text=True)
    assert out1 == out2
    metrics = json.loads(Path("results/metrics.json").read_text(encoding="utf-8"))
    assert metrics["input_audit"]["data_files"] == 0
    assert metrics["reproducibility"]["seed"] == 2023
    assert metrics["scenarios"]
    assert metrics["falsification"]["no_drought_total_biomass"] >= 0


def test_generated_figures_are_nonempty_svg():
    figures = sorted(Path("figures").glob("*.svg"))
    assert len(figures) >= 9
    assert all(f.stat().st_size > 500 for f in figures)
