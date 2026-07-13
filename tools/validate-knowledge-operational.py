#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / ".agents/skills/kc-inventory/scripts/validate-corpus-layout.py"
)


def main() -> int:
    result = subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "knowledge",
            "--strict-statements",
            "--operational",
            "--operational-policy",
            "operational-check.yml",
            "--output",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            "ERROR: corpus operational validator returned invalid JSON",
            file=sys.stderr,
        )
        return 1

    counts = report.get("counts", {})
    print(
        "Corpus operational validation: "
        f"{counts.get('contract_errors', 0)} contract error(s), "
        f"{counts.get('blockers', 0)} blocker(s), "
        f"{counts.get('quality_warnings', 0)} quality warning(s), "
        f"{counts.get('suppressed', 0)} documented suppression(s)."
    )
    for finding in report.get("contract_errors", []):
        print(f"ERROR: {finding}", file=sys.stderr)
    for finding in report.get("blockers", []):
        print(
            "ERROR: "
            f"{finding.get('kind')} at {finding.get('path')}:"
            f"{finding.get('line')}",
            file=sys.stderr,
        )
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
