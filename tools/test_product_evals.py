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

    def test_decision_request_does_not_require_question_mark(self):
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
            "answer": (
                "Нужно ваше решение о политике для повторяющихся "
                "идентификаторов. Выберите один из вариантов."
            ),
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": (
                "Критерий и проверка готовы, риск указан. Передаю на приёмку."
            ),
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
                with mock.patch.object(MODULE, "compile_connection_instructions"):
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

    def test_connection_is_compiled_for_the_client(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            workdir = root / "project"
            source.mkdir()
            workdir.mkdir()
            with mock.patch.object(MODULE, "run") as run_mock:
                MODULE.compile_connection_instructions(workdir, source, "codex")
        command = run_mock.call_args.args[0]
        self.assertEqual(
            [
                "apm",
                "compile",
                "--local-only",
                "--target",
                "codex",
                "--root",
                str(workdir),
            ],
            command,
        )
        self.assertEqual(source, run_mock.call_args.args[1])

    def test_connection_compilation_preserves_fixture_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            workdir = root / "project"
            source.mkdir()
            workdir.mkdir()
            agents_path = workdir / "AGENTS.md"
            agents_path.write_text(
                "# Правила проекта\n\nНе выполняй commit и push.\n",
                encoding="utf-8",
            )

            def compile_agents(*_args, **_kwargs):
                agents_path.write_text(
                    "# AGENTS.md\n\nОткрой ait-routing/SKILL.md.\n",
                    encoding="utf-8",
                )

            with mock.patch.object(
                MODULE,
                "run",
                side_effect=compile_agents,
            ):
                MODULE.compile_connection_instructions(workdir, source, "codex")

            compiled = agents_path.read_text(encoding="utf-8")
        self.assertIn("Не выполняй commit и push.", compiled)
        self.assertIn("Открой ait-routing/SKILL.md.", compiled)

    def test_rescore_preserves_routing_trace_evidence(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "результат", "any_of": ["result.txt"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "routing_markers": ["режим менеджера", "маршрут"],
            "decision_marker_groups": [["повтор"]],
        }
        result = {
            "turns": [
                "Режим менеджера: полный. Маршрут: запросить решение о повторе.",
                (
                    "Критерий и проверка готовы, риск указан. "
                    "Передаю на приёмку."
                ),
            ],
            "before_owner": {"status": "", "diff": ""},
            "final_state": {"status": " M result.txt\n", "diff": ""},
            "metrics": {
                "commands": ["python3 -m unittest"],
                "usage": {},
                "routing_opened": True,
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "result.txt").write_text("done", encoding="utf-8")
            metrics = MODULE.rescore_result(scenario, result, workdir)
        self.assertTrue(metrics["routing_opened"])
        self.assertNotIn(
            "Новая сессия не открыла ait-routing/SKILL.md.",
            metrics["missed_mandatory_actions"],
        )

    def test_routing_requires_trace_and_first_response(self):
        scenario = {
            "expected_artifact_groups": [
                {"label": "результат", "any_of": ["result.txt"]},
            ],
            "required_commands": ["python3 -m unittest"],
            "handoff_markers": ["приём", "критер", "проверк", "риск"],
            "routing_markers": ["режим менеджера", "маршрут"],
            "decision_marker_groups": [["повтор"]],
        }
        first = {
            "answer": "Режим менеджера: полный. Маршрут: ait-routing.",
            "commands": [],
            "usage": {},
        }
        second = {
            "answer": "Критерий и проверка готовы, риск указан. Передаю на приёмку.",
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
                routing_opened=False,
            )
        self.assertIn(
            "Новая сессия не открыла ait-routing/SKILL.md.",
            metrics["missed_mandatory_actions"],
        )


if __name__ == "__main__":
    unittest.main()
