#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-apm-package-structure.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_apm_package_structure",
        VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the APM package structure validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageTargetContractTests(unittest.TestCase):
    def test_manifest_declares_all_required_package_targets(self) -> None:
        validator = load_validator()
        manifest = yaml.safe_load((ROOT / "apm.yml").read_text(encoding="utf-8"))

        self.assertEqual(
            set(manifest["targets"]),
            validator.REQUIRED_PACKAGE_TARGETS,
        )


if __name__ == "__main__":
    unittest.main()
