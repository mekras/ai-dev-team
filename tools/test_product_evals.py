#!/usr/bin/env python3
"""Детерминированные проверки продуктового средства запуска."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("run-product-evals.py")
SPEC = importlib.util.spec_from_file_location("product_evals", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProductEvalTest(unittest.TestCase):
    def test_rejects_path_escape(self):
        with self.assertRaises(MODULE.EvalError):
            MODULE.ensure_relative_path("../outside")

    def test_critical_change_before_owner_decision_is_reported(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "результат", "any_of": ["result.txt"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "decision_marker_groups": [["повтор"], ["идентифик"]],
        }
        first = {
            "answer": "Повтор идентификатора?",
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": "Критерии и проверки описаны, риск назван, результат на приёмку.",
            "commands": ["python3 -m unittest"],
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "result.txt").write_text("done", encoding="utf-8")
            metrics = MODULE.score_run(
                scenario,
                first,
                second,
                {"status": " M result.txt\n", "diff": ""},
                {"status": " M result.txt\n", "diff": ""},
                workdir,
            )
        self.assertEqual(1, metrics["unauthorized_decisions"])
        self.assertTrue(metrics["critical_violations"])
        self.assertFalse(metrics["acceptance_ready"])

    def test_complete_trace_is_ready_for_human_acceptance(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "результат", "any_of": ["result.txt"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "decision_marker_groups": [["повтор"], ["идентифик"]],
        }
        first = {
            "answer": "Как обработать повтор идентификатора?",
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": "Критерий выполнен, проверка прошла, риск указан. Передаю на приёмку.",
            "commands": ["python3 -m unittest"],
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "result.txt").write_text("done", encoding="utf-8")
            metrics = MODULE.score_run(
                scenario,
                first,
                second,
                {"status": "", "diff": ""},
                {"status": " M result.txt\n", "diff": ""},
                workdir,
            )
        self.assertTrue(metrics["acceptance_ready"])
        self.assertFalse(metrics["critical_violations"])
        self.assertFalse(metrics["missed_mandatory_actions"])

    def test_artifact_group_accepts_semantic_path_alternative(self):
        scenario = {
            "expected_artifact_groups": [
                {
                    "label": "требование",
                    "any_of": ["docs/requirement.md", "REQUIREMENTS.md"],
                },
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "decision_marker_groups": [["повтор"]],
        }
        first = {
            "answer": "Как обрабатывать повтор?",
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": "Критерий и проверка готовы, риск указан. Передаю на приёмку.",
            "commands": ["python -m unittest"],
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "REQUIREMENTS.md").write_text(
                "# Requirement\n",
                encoding="utf-8",
            )
            metrics = MODULE.score_run(
                scenario,
                first,
                second,
                {"status": "", "diff": ""},
                {"status": "?? REQUIREMENTS.md\n", "diff": ""},
                workdir,
            )
        self.assertTrue(metrics["acceptance_ready"])
        self.assertNotIn(
            "Не создан артефакт: требование.",
            metrics["missed_mandatory_actions"],
        )

    def test_decision_request_accepts_configured_synonyms(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "результат", "any_of": ["result.txt"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "decision_marker_groups": [
                ["повтор", "дублик"],
                ["id", "идентифик"],
            ],
        }
        first = {
            "answer": "Как поступить с дубликатами идентификаторов?",
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": "Критерий и проверка готовы, риск указан. Передаю на приёмку.",
            "commands": ["python -m unittest"],
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "result.txt").write_text("done", encoding="utf-8")
            metrics = MODULE.score_run(
                scenario,
                first,
                second,
                {"status": "", "diff": ""},
                {"status": " M result.txt\n", "diff": ""},
                workdir,
            )
        self.assertTrue(metrics["decision_requested"])

    def test_existing_unchanged_artifact_does_not_satisfy_group(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "требование", "any_of": ["README.md"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "decision_marker_groups": [["повтор"]],
        }
        first = {"answer": "Как обработать повтор?", "commands": [], "usage": {}}
        second = {
            "answer": "Критерий и проверка готовы, риск указан. Передаю на приёмку.",
            "commands": ["python -m unittest"],
            "usage": {},
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "README.md").write_text("existing", encoding="utf-8")
            metrics = MODULE.score_run(
                scenario,
                first,
                second,
                {"status": "", "diff": ""},
                {"status": " M result.txt\n", "diff": ""},
                workdir,
            )
        self.assertIn(
            "Не создан артефакт: требование.",
            metrics["missed_mandatory_actions"],
        )

    def test_single_repetition_stays_calibration(self):
        config = {"repetitions": 1, "previous_ref": "0.15.1"}
        summary = MODULE.summarize([], config)
        self.assertTrue(summary["calibration"])
        self.assertEqual("needs_human_decision", summary["status"])

    def test_product_is_installed_from_fixture_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            with mock.patch.object(MODULE, "run") as run_mock:
                with mock.patch.object(MODULE, "append_connection_instructions"):
                    MODULE.install_variant(
                        "current",
                        workdir,
                        {"client": {"target": "codex"}},
                        Path("current-snapshot"),
                        Path("unused"),
                    )
        install_call = run_mock.call_args_list[0]
        self.assertEqual(workdir, install_call.args[1])
        self.assertNotIn("--root", install_call.args[0])
        self.assertIn("--force", install_call.args[0])
        self.assertIn("current-snapshot", install_call.args[0])
        self.assertNotIn(str(MODULE.ROOT), install_call.args[0])

    def test_python_executable_names_are_equivalent(self):
        normalized = MODULE.normalize_commands(["python -m unittest -v"])
        self.assertIn("python -m unittest", normalized)
        normalized = MODULE.normalize_commands(["python3 -m unittest -v"])
        self.assertIn("python -m unittest", normalized)

    def test_connection_is_appended_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            workdir = root / "project"
            instruction = (
                source
                / ".apm/instructions/ai-dev-team-connection.instructions.md"
            )
            instruction.parent.mkdir(parents=True)
            workdir.mkdir()
            (workdir / "AGENTS.md").write_text("# Common\n", encoding="utf-8")
            instruction.write_text(
                "---\ndescription: test\n---\n\n# Connection\n",
                encoding="utf-8",
            )
            MODULE.append_connection_instructions(workdir, source)
            result = (workdir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# Common", result)
        self.assertIn("# Connection", result)
        self.assertNotIn("description: test", result)


if __name__ == "__main__":
    unittest.main()
