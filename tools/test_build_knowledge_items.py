#!/usr/bin/env python3
"""Проверки безопасного интерфейса сборщика элементов корпуса."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("build-knowledge-items.py")
SPEC = importlib.util.spec_from_file_location("build_knowledge_items", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BuildKnowledgeItemsCliTest(unittest.TestCase):
    def test_help_does_not_start_rebuild(self):
        output = io.StringIO()
        with (
            mock.patch.object(MODULE, "rebuild_all") as rebuild,
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            MODULE.main(["--help"])

        self.assertEqual(0, raised.exception.code)
        self.assertIn("--all", output.getvalue())
        rebuild.assert_not_called()

    def test_missing_all_does_not_start_rebuild(self):
        errors = io.StringIO()
        with (
            mock.patch.object(MODULE, "rebuild_all") as rebuild,
            contextlib.redirect_stderr(errors),
            self.assertRaises(SystemExit) as raised,
        ):
            MODULE.main([])

        self.assertEqual(2, raised.exception.code)
        self.assertIn("--all", errors.getvalue())
        rebuild.assert_not_called()

    def test_all_starts_rebuild(self):
        with mock.patch.object(MODULE, "rebuild_all", return_value=0) as rebuild:
            result = MODULE.main(["--all"])

        self.assertEqual(0, result)
        rebuild.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
