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


class PortableCoreBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.skill = self.root / ".apm/skills/example/SKILL.md"
        self.skill.parent.mkdir(parents=True)

    def check_text(self, text: str) -> None:
        self.skill.write_text(text, encoding="utf-8")
        with patch.object(self.validator, "ROOT", self.root):
            self.validator.check_portable_core_boundary()

    def test_repository_identifiers_without_paths_are_rejected(self) -> None:
        for identifier in (
            "ФТ-6", "ФТ-7", "ФТ-8", "ФТ-9", "КАЧ-6",
            "ADR-0002", "ADR-0003",
        ):
            with self.subTest(identifier=identifier):
                with redirect_stderr(io.StringIO()) as errors:
                    with self.assertRaises(SystemExit) as raised:
                        self.check_text(f"Основание: `{identifier}`.")
                self.assertNotEqual(raised.exception.code, 0)
                self.assertIn(".apm/skills/example/SKILL.md", errors.getvalue())

    def test_fixed_repository_paths_are_rejected(self) -> None:
        for path in (
            "docs/06-architecture/adr/0002-cross-cutting-decision-records.md",
            "docs/05-requirements/functional/ft-7.md",
            "knowledge/index/source-impact/2026-06-29-adrg-adr-github-io.md",
        ):
            with self.subTest(path=path):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.check_text(path)

    def test_portable_rules_sources_and_examples_pass(self) -> None:
        self.check_text(
            "Профильный навык задаёт значимость решения.\n"
            "Статусы основаны на ADRG-011. Принципы — на CLAR-050.\n"
            "Путь журнала: docs/06-architecture/adr/.\n"
            "Пример имени: docs/ADR/ADR-0001.md. Формат: ADR-NNNN.md.\n"
            "Пример: ADR-0007 о миграции хранилища заказов.\n"
            "Пример требования: ФТ-1. Идентификаторы ФТ-60 и КАЧ-60."
        )

    def test_local_documentation_is_outside_portable_core(self) -> None:
        document = self.root / "docs/06-architecture/README.md"
        document.parent.mkdir(parents=True)
        document.write_text(
            "ФТ-6, ФТ-7–ФТ-9, КАЧ-6, ADR-0002, ADR-0003.",
            encoding="utf-8",
        )
        self.check_text("Переносимые правила без локальной трассировки.")


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


class CommunicationLoadingContractTests(unittest.TestCase):
    PATHS = (
        ".apm/skills/ait-routing/SKILL.md",
        ".agents/skills/ai-human-communication/SKILL.md",
        ".apm/instructions/ai-dev-team-connection.instructions.md",
        ".apm/skills/ait-setup/SKILL.md",
        ".apm/skills/ait-setup/assets/project-AGENTS.md",
        ".apm/skills/ait-routing/references/skill-index.md",
    )

    def setUp(self) -> None:
        self.validator = load_validator()
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        for relative in self.PATHS:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())

    def check_contract(self) -> None:
        with patch.object(self.validator, "ROOT", self.root):
            self.validator.check_human_communication_loading_contract()

    def test_complete_loading_chain_passes(self) -> None:
        self.check_contract()

    def test_mention_without_required_open_is_rejected(self) -> None:
        routing = self.root / self.PATHS[0]
        text = routing.read_text(encoding="utf-8")
        routing.write_text(text.replace(
            "До первого сообщения открой `ai-human-communication/SKILL.md`",
            "После ответа упомяни `ai-human-communication/SKILL.md`",
        ), encoding="utf-8")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_duplicate_product_text_rules_are_rejected(self) -> None:
        duplicate = self.root / (
            ".apm/skills/ait-routing/references/human-texts.md"
        )
        duplicate.parent.mkdir(parents=True, exist_ok=True)
        duplicate.write_text("# Тексты для человека\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_stale_product_rules_link_is_rejected(self) -> None:
        routing = self.root / self.PATHS[0]
        with routing.open("a", encoding="utf-8") as stream:
            stream.write("\n[human-texts]: references/human-texts.md\n")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_missing_shared_communication_skill_is_rejected(self) -> None:
        (self.root / self.PATHS[1]).unlink()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_lazy_connection_loader_is_rejected(self) -> None:
        connection = self.root / self.PATHS[2]
        text = connection.read_text(encoding="utf-8")
        connection.write_text(text.replace(
            "---\n", '---\napplyTo: "**/*"\n', 1,
        ), encoding="utf-8")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()

    def test_stale_immediate_reply_order_is_rejected(self) -> None:
        routing = self.root / self.PATHS[0]
        with routing.open("a", encoding="utf-8") as stream:
            stream.write("\nДо чтения других навыков покажи маршрут.\n")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.check_contract()


if __name__ == "__main__":
    unittest.main()
