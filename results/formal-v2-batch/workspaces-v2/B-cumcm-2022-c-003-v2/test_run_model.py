import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
metrics = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "results" / "复现清单.json").read_text(encoding="utf-8"))
assert metrics["audit"]["valid_composition_rows"] == 67
assert metrics["audit"]["invalid_composition_rows"] == 2
assert 0 <= metrics["q2"]["grouped_LOAO_accuracy"] <= 1
assert len(metrics["q3"]["unknown"]) == 8
assert len(metrics["q4"]["correlations"]) == 2
assert manifest["command"] == "python run_model.py"
assert len(list((ROOT / "figures").glob("*.svg"))) >= 12
print("PASS: metrics, manifest, unknown coverage, correlations, and figure count")
