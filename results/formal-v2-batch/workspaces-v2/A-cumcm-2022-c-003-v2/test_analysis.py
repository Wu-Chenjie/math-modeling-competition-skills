import json
from pathlib import Path

import analyze_case


def test_loader_uses_case_summary_rows_data_only():
    source = Path(__file__).with_name("analyze_case.py").read_text(encoding="utf-8")
    assert "rows_data" in source
    assert ".xlsx" not in source
    case = json.loads(Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/cumcm-2022-c.json").read_text(encoding="utf-8"))
    sheets = {s["sheet"]: s for f in case["data_audit"] for s in f["sheets"]}
    assert len(sheets["表单1"]["rows_data"]) == 59
    assert len(sheets["表单2"]["rows_data"]) == 70
    assert len(sheets["表单3"]["rows_data"]) == 9


def test_artifact_level_weathering_and_reconstruction_outputs():
    case, sheets, _ = analyze_case.load_case()
    meta, rows, unknown = analyze_case.parse_rows(sheets)
    assert case["case_id"] == "cumcm-2022-c"
    assert len(meta) == 58
    assert len(rows) == 69
    assert len(unknown) == 8
    metrics = json.loads(Path("results/metrics.json").read_text(encoding="utf-8"))
    assert sum(g["n"] for g in metrics["q1"]["weathering_rates"]["type"].values()) == 58
    assert metrics["q1"]["preweathered_predictions"]
    assert Path("results/preweathered_predictions.csv").is_file()
