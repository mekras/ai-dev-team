"""Проверки средств корпуса знаний: указатели и адреса источников."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

TOOLS = Path(__file__).resolve().parent


def load(script_name: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, TOOLS / script_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


index_check = load("check-knowledge-index.py", "check_knowledge_index")
sources = load("check-knowledge-sources.py", "check_knowledge_sources")
fetch_queue = load("fetch-knowledge-queue.py", "fetch_knowledge_queue")
transcribe_queue = load("transcribe-knowledge-queue.py", "transcribe_knowledge_queue")


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

    def test_rebuild_runs_from_project_root(self) -> None:
        """Контроллеру нужен доступ к решениям за пределами корпуса."""
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            seen: dict[str, object] = {}

            def capture(command, **kwargs):
                seen["command"] = command
                seen.update(kwargs)
                return subprocess.CompletedProcess([], 0, stdout="", stderr="")

            original_run = subprocess.run
            subprocess.run = capture
            try:
                self.original_rebuild(knowledge)
            finally:
                subprocess.run = original_run

            self.assertEqual(seen.get("cwd"), knowledge.parent)
            self.assertEqual(seen["command"][2:4], ["knowledge", "--rebuild-indexes"])

    def test_generated_statement_paths_remain_corpus_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            knowledge = make_corpus(Path(tmp))
            index = knowledge / "index" / "statements.yml"
            index.write_text(
                "statements:\n- id: DEMO-001\n"
                "  path: knowledge/data/demo/items/intro/statements.yml\n",
                encoding="utf-8",
            )

            index_check.normalize_statement_paths(index, "knowledge")

            self.assertIn(
                "  path: data/demo/items/intro/statements.yml\n",
                index.read_text(encoding="utf-8"),
            )


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


def make_queue_source(root: Path, stage: str) -> tuple[Path, Path]:
    source = root / "source.yml"
    unit = root / "items" / "unit"
    unit.mkdir(parents=True)
    source.write_text(yaml.safe_dump({"id": "DEMO", "copy_policy": "fragments_only"}))
    (root / "items.yml").write_text(yaml.safe_dump({"items": [
        {"id": "DEMO-unit", "path": "items/unit", "workflow_stage": stage}
    ]}))
    (unit / "item.yml").write_text(yaml.safe_dump({
        "id": "DEMO-unit", "workflow_stage": stage,
        "fetch_url": "https://example.test/fragment"
    }))
    return source, unit


class FetchQueueTest(unittest.TestCase):
    def test_fetches_indexed_unit_and_repeat_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, unit = make_queue_source(Path(tmp), "needs_fetch")
            original_source = source.read_bytes()

            def download(url, destination):
                self.assertEqual(url, "https://example.test/fragment")
                destination.write_text("selected fragment", encoding="utf-8")
            with patch.object(fetch_queue, "download_fragment", side_effect=download) as call:
                self.assertEqual(fetch_queue.fetch_source(source), 1)
                self.assertEqual(fetch_queue.fetch_source(source), 0)
                self.assertEqual(call.call_count, 1)
            self.assertEqual((unit / "fragment.html").read_text(), "selected fragment")
            unit_card = yaml.safe_load((unit / "item.yml").read_text())
            self.assertEqual(unit_card["workflow_stage"], "fetched")
            item_index = yaml.safe_load((source.parent / "items.yml").read_text())
            self.assertEqual(item_index["items"][0]["workflow_stage"], "fetched")
            self.assertEqual(source.read_bytes(), original_source)

    def test_accepts_only_selected_items(self) -> None:
        self.assertTrue(fetch_queue.eligible({"workflow_stage": "needs_fetch"}))
        self.assertTrue(
            fetch_queue.eligible(
                {
                    "workflow_stage": "indexed",
                    "processing_scope": "selected_fragments",
                }
            )
        )
        self.assertFalse(fetch_queue.eligible({"workflow_stage": "indexed"}))

    def test_rejects_path_outside_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            source_dir.mkdir()
            with self.assertRaises(ValueError):
                fetch_queue.item_directory(source_dir, {"path": "../../outside"})


class TranscribeQueueTest(unittest.TestCase):
    def test_transcribes_indexed_unit_and_repeat_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, unit = make_queue_source(Path(tmp), "needs_transcript")
            original_source = source.read_bytes()
            (unit / "audio.tmp.wav").write_bytes(b"audio fixture")
            def run(argv, **kwargs):
                if argv[0] == "fixture-whisper":
                    (unit / "audio.tmp.txt").write_text("raw transcript", encoding="utf-8")
                else:
                    self.assertEqual((unit / "transcript.txt").read_text(), "raw transcript")
                return subprocess.CompletedProcess(argv, 0)
            with patch.object(transcribe_queue.subprocess, "run", side_effect=run) as call:
                self.assertEqual(
                    transcribe_queue.transcribe(source, "fixture-whisper", Path("validator.py")), 1
                )
                self.assertEqual(
                    transcribe_queue.transcribe(source, "fixture-whisper", Path("validator.py")), 0
                )
                self.assertEqual(call.call_count, 2)
            self.assertEqual((unit / "transcript.txt").read_text(), "raw transcript")
            unit_card = yaml.safe_load((unit / "item.yml").read_text())
            self.assertEqual(unit_card["workflow_stage"], "raw_transcribed")
            item_index = yaml.safe_load((source.parent / "items.yml").read_text())
            self.assertEqual(item_index["items"][0]["workflow_stage"], "raw_transcribed")
            self.assertEqual(source.read_bytes(), original_source)

    def test_rejects_path_outside_source_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, unit = make_queue_source(Path(tmp), "needs_transcript")
            (source.parent / "items.yml").write_text(yaml.safe_dump({"items": [
                {"path": "../../outside", "workflow_stage": "needs_transcript"}
            ]}))
            with patch.object(transcribe_queue.subprocess, "run") as call:
                with self.assertRaises(ValueError):
                    transcribe_queue.transcribe(source, "whisper", Path("validator.py"))
                call.assert_not_called()

    def test_failed_validation_leaves_unit_queued_for_safe_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source, unit = make_queue_source(Path(tmp), "needs_transcript")
            (unit / "transcript.txt").write_text("saved transcript", encoding="utf-8")
            with patch.object(transcribe_queue.subprocess, "run", side_effect=
                subprocess.CalledProcessError(1, ["validator"])):
                with self.assertRaises(subprocess.CalledProcessError):
                    transcribe_queue.transcribe(source, "whisper", Path("validator.py"))
            unit_card = yaml.safe_load((unit / "item.yml").read_text())
            self.assertEqual(unit_card["workflow_stage"], "needs_transcript")
            self.assertEqual((unit / "transcript.txt").read_text(), "saved transcript")
            with patch.object(transcribe_queue.subprocess, "run", return_value=
                subprocess.CompletedProcess([], 0)) as call:
                self.assertEqual(
                    transcribe_queue.transcribe(source, "whisper", Path("validator.py")), 0
                )
                self.assertEqual(call.call_count, 1)
                self.assertEqual(call.call_args.args[0][0], "python3")
            unit_card = yaml.safe_load((unit / "item.yml").read_text())
            self.assertEqual(unit_card["workflow_stage"], "raw_transcribed")

    def test_selects_the_only_media_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            media = directory / "recording.tmp.mp3"
            media.write_bytes(b"audio")

            self.assertEqual(transcribe_queue.media_file(directory), media)

    def test_rejects_ambiguous_media_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "first.tmp.mp3").write_bytes(b"audio")
            (directory / "second.tmp.wav").write_bytes(b"audio")

            self.assertIsNone(transcribe_queue.media_file(directory))


if __name__ == "__main__":
    unittest.main()
