"""Recover missing standalone manifests only from valid embedded run evidence."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_artifacts import resolve_record_path

def repair(gate: dict, output: Path) -> dict:
    repaired, blocked = [], []
    for run in gate.get("runs", []):
        checks = run.get("checks", {})
        if not checks.get("has_metrics") or checks.get("has_reproducibility_manifest"):
            continue
        paths = [resolve_record_path(str(p)) for p in checks.get("metrics_paths", [])]
        metrics = next((p for p in paths if p.is_file()), None)
        if metrics is None:
            blocked.append({"run_id": run.get("run_id"), "reason": "metrics_missing"}); continue
        try:
            payload = json.loads(metrics.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            blocked.append({"run_id": run.get("run_id"), "reason": "metrics_invalid_json", "detail": str(exc)}); continue
        manifest = payload.get("reproducibility_manifest") if isinstance(payload, dict) else None
        if not isinstance(manifest, dict) or not manifest:
            blocked.append({"run_id": run.get("run_id"), "reason": "embedded_manifest_absent"}); continue
        workspace = metrics.parent.parent
        target = workspace / "reproducibility_manifest.json"
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        repaired.append({"run_id": run.get("run_id"), "path": target.as_posix(), "source": metrics.as_posix()})
    result = {"repaired": repaired, "blocked": blocked, "status": "completed"}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("gate", type=Path); p.add_argument("output", type=Path); a=p.parse_args()
    r=repair(json.loads(a.gate.read_text(encoding="utf-8")), a.output)
    print(json.dumps({"repaired":len(r["repaired"]),"blocked":len(r["blocked"])}, ensure_ascii=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
