"""Create and execute the preregistered A/B benchmark run plan."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluate import build_run_id, eligible_cases, _load_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "benchmarks" / "benchmark-config.json"
MANIFEST_PATH = PROJECT_ROOT / "docs" / "baseline-run-manifest.json"
SUMMARY_DIR = PROJECT_ROOT / "benchmarks" / "case-summaries"
RUNTIME_ROOT = Path(os.environ.get("CODEX_PRIMARY_RUNTIME", "C:/Users/伍辰杰/.cache/codex-runtimes/codex-primary-runtime/dependencies"))
WALL_CLOCK_BUDGET_SECONDS = 120 * 60


def build_execution_env() -> dict[str, str]:
    """Pin the bundled Python package runtime for generated benchmark code."""
    env = os.environ.copy()
    python_root = RUNTIME_ROOT / "python"
    bin_root = RUNTIME_ROOT / "bin" / "override"
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(python_root), env.get("PYTHONPATH", ""))))
    env["PATH"] = os.pathsep.join(filter(None, (str(bin_root), str(python_root), env.get("PATH", ""))))
    return env


def decode_process_output(value: bytes | None) -> str:
    """Decode Codex output independently of the Windows console code page."""
    return (value or b"").decode("utf-8", errors="replace")


def validate_vendor_root(vendor_root: Path) -> list[str]:
    """Return missing files that would make a baseline preflight invalid."""
    required = [
        Path("xiao/SKILL.md"),
        Path("xiao/使用指南.md"),
        Path("xiao/references/roles/建模手/SKILL.md"),
        Path("xiao/references/roles/编程手/SKILL.md"),
        Path("matt/skills/engineering/research/SKILL.md"),
    ]
    return [path.as_posix() for path in required if not (vendor_root / path).is_file()]


def process_command_result(returncode: int | None, timed_out: bool) -> str:
    if timed_out:
        return "timeout"
    return "completed" if returncode == 0 else "failed"


def build_run_plan(cases_root: Path) -> list[dict[str, Any]]:
    """Expand verified cases into the fixed A/B x case x three-run plan."""
    config = _load_json(CONFIG_PATH)
    manifest = _load_json(MANIFEST_PATH)
    plan: list[dict[str, Any]] = []
    for metadata_path in eligible_cases(sorted(cases_root.glob("*/metadata.yaml"))):
        metadata = _load_json(metadata_path)
        case_root = metadata_path.parent
        for group in ("A", "B"):
            for index in range(1, int(config["controls"]["independent_runs_per_case"]) + 1):
                item: dict[str, Any] = {
                    "group": group,
                    "case_id": metadata["id"],
                    "index": index,
                    "run_id": f"{build_run_id(group, metadata['id'], index)}-v2",
                    "protocol_version": 2,
                    "case_root": case_root.as_posix(),
                    "summary_path": (SUMMARY_DIR / f"{metadata['id']}.json").as_posix(),
                    "statement_sha256": metadata["statement_sha256"],
                    "data_sha256": metadata["data_sha256"],
                    "model": config["model"]["id"],
                    "domain_skill_ref": manifest["skill_refs"]["domain"]["commit"],
                    "engineering_skill_ref": manifest["skill_refs"]["engineering"]["commit"] if group == "B" else None,
                    "status": "planned",
                }
                plan.append(item)
    return plan


def _prompt(item: dict[str, Any], vendor_root: Path) -> str:
    domain = vendor_root / "xiao" / "SKILL.md"
    text = [
        f"This is preregistered run {item['run_id']}. Do not modify repository files.",
        f"Read the pinned domain Skill at {domain}.",
        f"Also read exactly these domain stage files: {vendor_root / 'xiao' / '使用指南.md'}, {vendor_root / 'xiao' / 'references' / 'roles' / '建模手' / 'SKILL.md'}, and {vendor_root / 'xiao' / 'references' / 'roles' / '编程手' / 'SKILL.md'}.",
    ]
    if item["group"] == "B":
        text.append(
            "Read exactly these pinned Matt files: "
            + ", ".join(
                str(vendor_root / "matt" / "skills" / "engineering" / name / "SKILL.md")
                for name in ("grill-with-docs", "research", "prototype", "tdd", "code-review")
            )
            + ". Do not recursively enumerate other files."
        )
    text.extend(
        [
            f"Read the deterministic case summary JSON at {item['summary_path']} as the complete benchmark input. It includes the full official problem text and a binary-safe data audit with sample rows.",
            "Do not open or parse binary attachments (PDF, XLSX, ZIP). You may create text/code artifacts in the run workspace and use the supplied rows_data, but never invent omitted rows or values.",
            "create executable code in the run workspace, run the code, and save machine-readable metrics and figures. If a calculation cannot be completed, mark only that stage pending and explain why.",
            "Return a structured modeling report: problem framing, data audit, assumptions, candidate models, baseline, math specification, code/prototype, experiment, validation, sensitivity/robustness, falsification, reviewer risks, and reproducibility manifest.",
            "Never invent data, execution results, citations, or scores. Do not narrate tool use or internal reasoning. After the code run, stop immediately and return only a JSON receipt with keys status, code_path, metrics_path, figures_count, tests, and pending_stages; keep it under 300 words.",
        ]
    )
    return "\n".join(text)


def execute_one(item: dict[str, Any], vendor_root: Path, output_root: Path) -> dict[str, Any]:
    """Execute one run and retain a machine-readable process record."""
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = (output_root / f"{item['run_id']}.txt").resolve()
    workspace = (output_root.parent / "workspaces-v2" / item["run_id"]).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    missing_dependencies = validate_vendor_root(vendor_root)
    started = datetime.now(timezone.utc).isoformat()
    if missing_dependencies:
        record = dict(item)
        record.update(
            {
                "status": "invalid_preflight",
                "started_at": started,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": None,
                "output_file": None,
                "missing_dependencies": missing_dependencies,
            }
        )
        return record
    command = [
        "codex",
        "exec",
        "-m",
        item["model"],
        "-s",
        "workspace-write",
        "-C",
        str(workspace),
        "--add-dir",
        str(vendor_root),
        "--add-dir",
        str(Path(item["summary_path"]).parent),
        "-o",
        str(output_path),
        _prompt(item, vendor_root),
    ]
    stdout_log = output_root / f"{item['run_id']}.stdout.log"
    stderr_log = output_root / f"{item['run_id']}.stderr.log"
    timed_out = False
    try:
        with stdout_log.open("wb") as stdout_handle, stderr_log.open("wb") as stderr_handle:
            process = subprocess.Popen(command, cwd=workspace, stdout=stdout_handle, stderr=stderr_handle, env=build_execution_env())
            try:
                returncode = process.wait(timeout=WALL_CLOCK_BUDGET_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                returncode = None
    except OSError as error:
        returncode = None
        stderr_log.write_text(str(error), encoding="utf-8")
    record = dict(item)
    record["timeout_budget_seconds"] = WALL_CLOCK_BUDGET_SECONDS
    stderr_text = decode_process_output(stderr_log.read_bytes()) if stderr_log.exists() else ""
    token_matches = re.findall(r"tokens used\s*\n([\d,]+)", stderr_text)
    artifacts = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file())
    record.update(
        {
            "status": process_command_result(returncode, timed_out),
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": returncode,
            "output_file": output_path.as_posix(),
            "workspace": workspace.as_posix(),
            "artifacts": artifacts,
            "reported_tokens": int(token_matches[-1].replace(",", "")) if token_matches else None,
            "stdout_log": stdout_log.as_posix(),
            "stderr_log": stderr_log.as_posix(),
            "stdout_tail": decode_process_output(stdout_log.read_bytes())[-2000:] if stdout_log.exists() else "",
            "stderr_tail": stderr_text[-2000:],
        }
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("cases_root", type=Path)
    plan_parser.add_argument("output", type=Path)
    run_parser = sub.add_parser("run-one")
    run_parser.add_argument("plan", type=Path)
    run_parser.add_argument("run_id")
    run_parser.add_argument("vendor_root", type=Path)
    run_parser.add_argument("output_root", type=Path)
    run_parser.add_argument("record", type=Path)
    args = parser.parse_args()

    if args.command == "plan":
        plan = build_run_plan(args.cases_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"runs": len(plan), "output": str(args.output)}, ensure_ascii=True))
        return 0

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    item = next(item for item in plan if item["run_id"] == args.run_id)
    record = execute_one(item, args.vendor_root, args.output_root)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=True))
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
