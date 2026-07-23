#!/usr/bin/env python3
"""Regression checks for generated artifacts in APM lockfiles."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate-apm-lock-artifacts.py")
SPEC = importlib.util.spec_from_file_location("validate_apm_lock_artifacts", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_lock(directory: Path, content: str) -> Path:
    path = directory / "apm.lock.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory() as raw_directory:
        directory = Path(raw_directory)
        clean = write_lock(
            directory,
            """
packages:
  - deployed_files:
      - .agents/skills/example/scripts/check.py
    deployed_file_hashes:
      .agents/skills/example/scripts/check.py: sha256:abc
""",
        )
        assert MODULE.scan_lockfile(clean) == []

        polluted = write_lock(
            directory,
            """
packages:
  - deployed_files:
      - .agents/skills/example/scripts/__pycache__/check.cpython-313.pyc
    deployed_file_hashes:
      .claude/skills/example/scripts/check.pyc: sha256:def
""",
        )
        assert MODULE.scan_lockfile(polluted) == [
            ".agents/skills/example/scripts/__pycache__/check.cpython-313.pyc",
            ".claude/skills/example/scripts/check.pyc",
        ]

    assert MODULE.is_generated_python_artifact(r"scripts\\__pycache__\\check.py")
    assert MODULE.is_generated_python_artifact("scripts/check.pyc")
    assert not MODULE.is_generated_python_artifact("scripts/check.py")

    print("Проверки артефактов Python в файлах блокировки пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
