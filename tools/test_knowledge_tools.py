"""Проверки средств корпуса знаний: указатели и адреса источников."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent


def load(script_name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, TOOLS / script_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


index_check = load("check-knowledge-index.py", "check_knowledge_index")
sources = load("check-knowledge-sources.py", "check_knowledge_sources")


def make_corpus(root: Path) -> Path:
    knowledge = root / "knowledge"
    unit = knowledge / "data" / "demo" / "items" / "intro"
    unit.mkdir(parents=True)
    (knowledge / "index").mkdir()
    (knowledge / "corpus.yml").write_text("contract_version: 2\n", encoding="utf-8")

    (knowledge / "data" / "demo" / "source.yml").write_text(
        yaml.safe_dump(
            {
                "id": "DEMO",
                "slug": "demo",
                "url": "https://example.test/page",
                "locator": "local:DEMO",
                "last_checked_at": "2026-01-01",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (knowledge / "index" / "items.yml").write_text("items: []\n", encoding="utf-8")
    (knowledge / "index" / "statements.yml").write_text(
        "statements: []\n", encoding="utf-8"
    )
    return knowledge


class IndexCheckTest(unittest.TestCase):
    """Обёртка над переносимой пересборкой указателей."""

    def setUp(self) -> None:
        self.original_rebuild = index_check.rebuild

    def tearDown(self) -> None:
        index_check.rebuild = self.original_rebuild

    def fake_rebuild(self, effect=None):
        def rebuild(corpus_root: Path):
            if effect is not None:
                effect(corpus_root)
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")

        return rebuild

    def test_no_drift_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            index_check.rebuild = self.fake_rebuild()

            self.assertEqual(index_check.main(["--corpus-root", str(knowledge)]), 0)

    def test_drift_is_reported_and_tree_is_left_intact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            target = knowledge / "index" / "statements.yml"

            def overwrite(corpus_root: Path) -> None:
                target.write_text("statements: [{id: DEMO-001}]\n", encoding="utf-8")

            index_check.rebuild = self.fake_rebuild(overwrite)

            self.assertEqual(index_check.main(["--corpus-root", str(knowledge)]), 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "statements: []\n")

    def test_write_keeps_rebuilt_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            target = knowledge / "index" / "statements.yml"

            def overwrite(corpus_root: Path) -> None:
                target.write_text("statements: [{id: DEMO-001}]\n", encoding="utf-8")

            index_check.rebuild = self.fake_rebuild(overwrite)

            argv = ["--corpus-root", str(knowledge), "--write"]
            self.assertEqual(index_check.main(argv), 0)
            self.assertIn("DEMO-001", target.read_text(encoding="utf-8"))

    def test_missing_index_file_counts_as_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            (knowledge / "index" / "items.yml").unlink()

            def create(corpus_root: Path) -> None:
                (knowledge / "index" / "items.yml").write_text(
                    "items: []\n", encoding="utf-8"
                )

            index_check.rebuild = self.fake_rebuild(create)

            self.assertEqual(index_check.main(["--corpus-root", str(knowledge)]), 1)
            self.assertFalse((knowledge / "index" / "items.yml").exists())

    def test_failed_rebuild_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))

            def failing(corpus_root: Path):
                return subprocess.CompletedProcess([], 1, stdout="", stderr="сбой")

            index_check.rebuild = failing

            self.assertEqual(index_check.main(["--corpus-root", str(knowledge)]), 2)

    def test_missing_corpus_contract_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(index_check.main(["--corpus-root", tmp]), 2)

    def test_rebuild_runs_from_corpus_root(self) -> None:
        """Пути в указателях зависят от рабочего каталога переносимого средства."""
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            seen: dict[str, object] = {}

            def capture(*args, **kwargs):
                seen.update(kwargs)
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            original_run = subprocess.run
            subprocess.run = capture
            try:
                self.original_rebuild(knowledge)
            finally:
                subprocess.run = original_run

            self.assertEqual(seen.get("cwd"), knowledge)


class SourceCheckTest(unittest.TestCase):
    def test_collects_only_network_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            targets, skipped = sources.collect_targets(knowledge / "data")

            self.assertEqual([t.url for t in targets], ["https://example.test/page"])
            self.assertEqual(skipped, [])

    def test_source_without_network_address_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            card = knowledge / "data" / "demo" / "source.yml"
            card.write_text(
                yaml.safe_dump(
                    {"id": "DEMO", "slug": "demo", "locator": "local:DEMO"},
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            targets, skipped = sources.collect_targets(knowledge / "data")

            self.assertEqual(targets, [])
            self.assertEqual(len(skipped), 1)
            self.assertIn("DEMO", skipped[0])

    def test_stale_source_is_detected(self) -> None:
        from datetime import date

        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))

            fresh = sources.stale_sources(knowledge / "data", date(2026, 1, 2))
            stale = sources.stale_sources(knowledge / "data", date(2027, 1, 1))

            self.assertEqual(fresh, [])
            self.assertEqual(len(stale), 1)


if __name__ == "__main__":
    unittest.main()
