"""Build opaque submission packages from machine-scoreable benchmark runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_workspace(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_dir():
        return candidate
    normalized = value.replace("\\", "/")
    marker = "/results/"
    if marker in normalized:
        return ROOT / "results" / normalized.split(marker, 1)[1]
    return candidate


def _workspace_from_gate(run: dict[str, Any]) -> Path:
    """Recover workspace root from the gate's normalized metrics path."""
    raw = str(run.get("workspace", ""))
    if raw:
        resolved = _resolve_workspace(raw)
        if resolved.is_dir() and resolved != Path.cwd():
            return resolved
    for raw_path in run.get("checks", {}).get("metrics_paths", []):
        path = _resolve_workspace(str(raw_path))
        if path.is_file():
            # metrics are conventionally <workspace>/<results-or-output>/metrics.json
            for parent in path.parents:
                if (parent / "results").is_dir() or (parent / "analysis_output").is_dir() or (parent / "run-output").is_dir():
                    return parent
    return Path()


def scoreable_runs(gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in gate.get("runs", []) if r.get("checks", {}).get("scoreable_machine_evidence")]


def build_blind_manifest(gate: dict[str, Any], output_root: Path) -> dict[str, Any]:
    """Copy passing workspaces and create a separate source map for the operator."""
    output_root.mkdir(parents=True, exist_ok=True)
    source_map: dict[str, Any] = {}
    packages: list[dict[str, Any]] = []
    for number, run in enumerate(sorted(scoreable_runs(gate), key=lambda x: str(x.get("run_id"))), 1):
        opaque = f"Submission-{number:03d}"
        package = output_root / opaque
        artifacts_dir = package / "artifacts"
        if package.exists():
            shutil.rmtree(package)
        artifacts_dir.mkdir(parents=True)
        workspace = _workspace_from_gate(run)
        copied: list[dict[str, str]] = []
        if workspace.is_dir():
            for src in sorted(p for p in workspace.rglob("*") if p.is_file() and ".pytest_cache" not in p.parts and "__pycache__" not in p.parts):
                rel = src.relative_to(workspace)
                dst = artifacts_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append({"path": rel.as_posix(), "sha256": _hash_file(dst)})
        package_manifest = {
            "submission_id": opaque,
            "protocol": "A/B v2 with recovery",
            "artifact_count": len(copied),
            "artifacts": copied,
            "review_status": "pending_blind_judges",
        }
        (package / "submission-manifest.json").write_text(json.dumps(package_manifest, indent=2), encoding="utf-8")
        source_map[opaque] = {
            "run_id": run.get("run_id"),
            "group": run.get("group"),
            "case_id": run.get("case_id"),
        }
        packages.append({"submission_id": opaque, "artifact_count": len(copied)})
    (output_root / "blind-source-map.json").write_text(json.dumps(source_map, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "protocol": "A/B v2 with recovery",
        "blind": True,
        "package_count": len(packages),
        "packages": packages,
        "source_map": "blind-source-map.json (operator-only)",
        "human_review": "pending blind Judges A-D",
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build_blind_manifest(_load(args.gate), args.output)
    print(json.dumps({"package_count": result["package_count"], "output": str(args.output)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
