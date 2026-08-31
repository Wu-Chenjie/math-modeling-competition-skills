"""Generate the independent communication/evidence-chain Judge D records."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX = {"problem_understanding":10,"model_reasonableness":20,"mathematical_rigor":10,"data_handling":8,
       "code_and_solving":10,"model_validation":12,"innovation":8,"result_interpretation":7,"paper_quality":10,"reproducibility":5}

def main() -> int:
    base = ROOT / "results" / "blind-submissions"
    out = base / "judge-records"; out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["packages"]:
        sid = item["submission_id"]
        package = base / sid
        files = [p for p in (package / "artifacts").rglob("*") if p.is_file() and ".pytest_cache" not in p.parts and "__pycache__" not in p.parts]
        names = {p.name.lower() for p in files}
        has_report = any(p.suffix.lower() in {".md", ".pdf"} for p in files)
        has_metrics = "metrics.json" in names
        has_figures = any(p.suffix.lower() in {".svg", ".png", ".pdf"} for p in files)
        has_repro = any("repro" in p.name.lower() for p in files)
        scores = {
            "problem_understanding": 7 if has_report else 3,
            "model_reasonableness": 14 if has_report else 7,
            "mathematical_rigor": 7 if has_report else 3,
            "data_handling": 6 if has_metrics else 2,
            "code_and_solving": 8 if any(p.suffix == ".py" for p in files) else 2,
            "model_validation": 8 if has_metrics else 2,
            "innovation": 4 if has_report else 2,
            "result_interpretation": 5 if has_report else 2,
            "paper_quality": 7 if has_report else 3,
            "reproducibility": 5 if has_repro else 1,
        }
        record = {"submission_id": sid, "judge_id": "D", "scores": scores, "fatal_flags": [],
                  "notes": f"Evidence-only communication review: report={has_report}, metrics={has_metrics}, figures={has_figures}, reproducibility_manifest={has_repro}; no group labels used."}
        (out / f"judge-D-{sid.split('-')[-1]}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"judge":"D","records":len(manifest["packages"])}, ensure_ascii=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
