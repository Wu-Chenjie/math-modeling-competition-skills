"""Prepare deterministic, binary-safe case summaries for controlled runs."""

from __future__ import annotations

import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from evaluate import sha256_tree


def _xlsx_audit(path: Path) -> dict[str, Any]:
    """Extract a compact, binary-safe workbook audit using only stdlib XML."""
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.findall("main:si", ns):
                shared.append("".join(node.text or "" for node in si.iter() if node.tag.endswith("}t")))
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = []
        rel_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root}
        for sheet in workbook.findall("main:sheets/main:sheet", ns):
            name = sheet.attrib.get("name", "")
            target = rels.get(sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"), "")
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            if target not in archive.namelist():
                continue
            ws = ET.fromstring(archive.read(target))
            rows = ws.findall("main:sheetData/main:row", ns)
            nonempty = 0
            max_col = 0
            headers: list[str] = []
            numeric_values: list[float] = []
            rows_data: list[list[str]] = []
            for row_index, row in enumerate(rows):
                values: list[str] = []
                for cell in row.findall("main:c", ns):
                    ref = cell.attrib.get("r", "")
                    letters = "".join(ch for ch in ref if ch.isalpha())
                    col = 0
                    for ch in letters:
                        col = col * 26 + ord(ch.upper()) - 64
                    max_col = max(max_col, col)
                    value = cell.find("main:v", ns)
                    raw = value.text if value is not None and value.text is not None else ""
                    if cell.attrib.get("t") == "inlineStr":
                        raw = "".join(node.text or "" for node in cell.iter() if node.tag.endswith("}t"))
                    if cell.attrib.get("t") == "s" and raw.isdigit() and int(raw) < len(shared):
                        raw = shared[int(raw)]
                    while len(values) < col:
                        values.append("")
                    values[col - 1] = raw
                    if raw != "":
                        nonempty += 1
                        try:
                            numeric_values.append(float(raw))
                        except ValueError:
                            pass
                if row_index == 0:
                    headers = values[:20]
                rows_data.append(values)
            entry: dict[str, Any] = {"sheet": name, "rows": len(rows), "columns": max_col, "nonempty_cells": nonempty, "headers": headers, "rows_data": rows_data}
            if numeric_values:
                entry["numeric_min"] = min(numeric_values)
                entry["numeric_max"] = max(numeric_values)
            sheets.append(entry)
    return {"file": path.name, "sheets": sheets}


def _data_audit(case_root: Path) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for path in sorted((case_root / "data").rglob("*.xlsx")):
        audits.append(_xlsx_audit(path))
    return audits


def build_summary(case_root: Path) -> dict[str, Any]:
    metadata = json.loads((case_root / "metadata.yaml").read_text(encoding="utf-8"))
    problem_files = sorted((case_root / "problem").glob("*.pdf"))
    if len(problem_files) != 1:
        raise ValueError(f"expected one problem PDF in {case_root}")
    pdf = problem_files[0]
    reader = PdfReader(str(pdf))
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    data_files = sorted(path.relative_to(case_root / "data").as_posix() for path in (case_root / "data").rglob("*") if path.is_file())
    zip_entries: dict[str, list[str]] = {}
    for path in (case_root / "data").glob("*.zip"):
        with zipfile.ZipFile(path) as archive:
            zip_entries[path.name] = sorted(archive.namelist())
    return {
        "case_id": metadata["id"],
        "competition": metadata["competition"],
        "year": metadata["year"],
        "title": metadata["title"],
        "problem_type": metadata["problem_type"],
        "source_status": metadata["source_status"],
        "problem_sha256": sha256_tree(case_root / "problem"),
        "data_sha256": sha256_tree(case_root / "data"),
        "pdf_pages": len(reader.pages),
        "pdf_extracted_chars": len(text),
        "problem_excerpt": " ".join(text.split())[:900],
        "problem_text": " ".join(text.split()),
        "data_files": data_files,
        "data_audit": _data_audit(case_root),
        "zip_entries": zip_entries,
        "metadata_expected_methods": metadata["expected_methods"],
        "metadata_common_failures": metadata["common_failures"],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("cases_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summaries = [build_summary(path.parent) for path in sorted(args.cases_root.glob("*/metadata.yaml")) if path.parent.joinpath("problem").is_dir() and path.parent.joinpath("data").is_dir()]
    if args.output.suffix.lower() == ".json":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        for summary in summaries:
            (args.output / f"{summary['case_id']}.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    print(json.dumps({"summaries": len(summaries), "output": str(args.output)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
