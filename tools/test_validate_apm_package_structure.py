#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


class ComplexityReferenceContractTests(unittest.TestCase):
    GUIDE = ".apm/skills/ait-routing/references/complexity-in-software-development.md"
    CONSUMERS = (
        ".apm/skills/ait-routing/SKILL.md",
        ".apm/agents/project-manager.agent.md",
        ".apm/skills/ait-architecture/references/system-complexity.md",
    )

    def setUp(self) -> None:
        self.validator = load_validator()
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        for relative_path in (self.GUIDE, *self.CONSUMERS):
            target = self.root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative_path).read_bytes())

    def check_contract(self) -> None:
        with patch.object(self.validator, "ROOT", self.root):
            self.validator.check_complexity_reference_contract()

    def test_existing_reference_and_consumers_pass(self) -> None:
        self.check_contract()

    def test_missing_reference_is_rejected(self) -> None:
        (self.root / self.GUIDE).unlink()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_missing_general_principle_owner_is_rejected(self) -> None:
        guide = self.root / self.GUIDE
        guide.write_text("# Справка без источника принципа", encoding="utf-8")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_broken_consumer_reference_is_rejected(self) -> None:
        for relative_path in self.CONSUMERS:
            with self.subTest(consumer=relative_path):
                consumer = self.root / relative_path
                original = consumer.read_text(encoding="utf-8")
                consumer.write_text(
                    original.replace("complexity-in-software-development.md", "missing.md"),
                    encoding="utf-8",
                )
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.check_contract()
                consumer.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
