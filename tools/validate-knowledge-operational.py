#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "knowledge" / "concepts.yml"
VALIDATOR = (
    ROOT
    / ".agents/skills/kc-inventory/scripts/validate-corpus-layout.py"
)


def validate_concept_authorities() -> list[str]:
    text = CONCEPTS.read_text(encoding="utf-8")
    forbidden_patterns = {
        r"\bрешени(?:е|я|ю|ем|й)\s+владельца\b": (
            "owner decision used as concept authority"
        ),
        r"\bowner-": "owner pseudo-source used in concept reconciliation",
    }
    return [
        f"{CONCEPTS.relative_to(ROOT)}: {message}"
        for pattern, message in forbidden_patterns.items()
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]


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
    concept_errors = validate_concept_authorities()
    for error in concept_errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result.returncode == 0 and not concept_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
