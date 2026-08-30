"""Prepare evidence metadata for a locally ingested benchmark case."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate import sha256_tree


def prepare_case(case_root: Path, source_url: str, license_note: str) -> dict[str, str]:
    """Return metadata additions; caller decides when source verification is complete."""
    return {
        "source_url": source_url,
        "source_status": "unverified",
        "statement_sha256": sha256_tree(case_root / "problem"),
        "data_sha256": sha256_tree(case_root / "data"),
        "accessed_at": "RECORD_ACCESS_DATE",
        "license_note": license_note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_root", type=Path)
    parser.add_argument("source_url")
    parser.add_argument("license_note")
    args = parser.parse_args()
    print(json.dumps(prepare_case(args.case_root, args.source_url, args.license_note), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
