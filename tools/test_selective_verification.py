from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / ".apm"
    / "skills"
    / "ait-impact-analysis"
    / "scripts"
    / "selective_verification.py"
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


def graph() -> dict:
    return {
        "schema_version": 1,
        "graph": {
            "name": "test-project",
            "description": "Граф тестового проекта.",
            "default_facet": "semantic",
            "unmapped_paths": "block",
            "ignore": [".git/**"],
        },
        "nodes": [
            {
                "id": "code",
                "title": "Код",
                "kind": "implementation",
                "paths": ["src/**"],
                "checks": ["code-check"],
            },
            {
                "id": "tests",
                "title": "Тесты",
                "kind": "test",
                "paths": ["tests/**"],
                "checks": ["test-check"],
            },
            {
                "id": "configuration",
                "title": "Настройки",
                "kind": "configuration",
                "paths": ["requirements.txt", "project-verification.json"],
                "checks": ["configuration-check"],
            },
        ],
        "edges": [
            {
                "from": "code",
                "to": "tests",
                "relation": "verifies",
                "facets": ["any"],
                "rationale": "Тесты проверяют код.",
            },
        ],
    }


def configuration(counter: Path, result: str = "ok") -> dict:
    check = [sys.executable, "check.py", str(counter), result]
    return {
        "schema_version": 1,
        "verification": {
            "name": "Тестовый проект",
            "impact_graph": "project-impact.json",
            "full_checks": ["local-check", "full-check"],
            "full_coverage_paths": [
                "project-impact.json",
                "project-verification.json",
                "requirements.txt",
            ],
            "global_inputs": [
                "project-impact.json",
                "project-verification.json",
                "requirements.txt",
            ],
            "output_limit": 160,
        },
        "areas": [
            {
                "id": "local-module",
                "title": "Локальный модуль",
                "impact_nodes": ["code", "tests"],
                "checks": ["local-check"],
            },
        ],
        "checks": [
            {
                "id": "local-check",
                "title": "Проверка локального модуля",
                "command": check,
                "cwd": ".",
                "inputs": ["src/**", "tests/**", "check.py"],
                "environment": {"inherit": ["PATH"], "set": {}},
                "tool_version_command": [sys.executable, "--version"],
            },
            {
                "id": "full-check",
                "title": "Полная проверка",
                "command": check,
                "cwd": ".",
                "inputs": ["src/**", "tests/**", "check.py"],
                "environment": {"inherit": ["PATH"], "set": {}},
                "tool_version_command": [sys.executable, "--version"],
            },
        ],
    }


class SelectiveVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Test User")
        write(self.repo / "src" / "local.py", "VALUE = 1\n")
        write(self.repo / "tests" / "test_local.py", "assert True\n")
        write(self.repo / "requirements.txt", "example==1\n")
        write(
            self.repo / "check.py",
            "from pathlib import Path\n"
            "import sys\n"
            "counter = Path(sys.argv[1])\n"
            "count = int(counter.read_text() if counter.exists() else '0') + 1\n"
            "counter.write_text(str(count))\n"
            "print('check run', count)\n"
            "raise SystemExit(7 if sys.argv[2] == 'fail' else 0)\n",
        )
        self.counter = self.root / "counter.txt"
        write(
            self.repo / "project-impact.json",
            json.dumps(graph(), ensure_ascii=False, indent=2),
        )
        write(
            self.repo / "project-verification.json",
            json.dumps(configuration(self.counter), ensure_ascii=False, indent=2),
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Начальное состояние")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self) -> tuple[int, dict]:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "run",
                "--repo",
                str(self.repo),
                "--config",
                str(self.repo / "project-verification.json"),
                "--base",
                "HEAD",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_validation_accepts_complete_declaration(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "validate",
                "--repo",
                str(self.repo),
                "--config",
                str(self.repo / "project-verification.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["status"], "passed")

    def test_import_does_not_write_bytecode(self) -> None:
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("selective_verification.py", "impact_graph.py"):
            shutil.copy2(SCRIPT.parent / name, scripts / name)

        completed = subprocess.run(
            [
                sys.executable,
                str(scripts / "selective_verification.py"),
                "validate",
                "--repo",
                str(self.repo),
                "--config",
                str(self.repo / "project-verification.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertFalse((scripts / "__pycache__").exists())

    def test_clean_tree_does_not_run_a_check(self) -> None:
        code, report = self.invoke()

        self.assertEqual(code, 0)
        self.assertEqual(report["selection"]["mode"], "selective")
        statuses = {item["id"]: item["status"] for item in report["checks"]}
        self.assertEqual(
            statuses,
            {"local-check": "not_required", "full-check": "not_required"},
        )
        self.assertFalse(self.counter.exists())

    def test_reuses_successful_local_check_without_running_full_check(self) -> None:
        write(self.repo / "src" / "local.py", "VALUE = 2\n")

        first_code, first = self.invoke()

        self.assertEqual(first_code, 0)
        self.assertEqual(first["selection"]["mode"], "selective")
        self.assertEqual(first["impact"]["changed_nodes"], ["code"])
        self.assertEqual(first["impact"]["affected_nodes"], ["tests"])
        statuses = {item["id"]: item["status"] for item in first["checks"]}
        self.assertEqual(statuses, {"local-check": "executed", "full-check": "not_required"})
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "1")

        second_code, second = self.invoke()

        self.assertEqual(second_code, 0)
        statuses = {item["id"]: item["status"] for item in second["checks"]}
        self.assertEqual(statuses, {"local-check": "cached", "full-check": "not_required"})
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "1")

    def test_changed_declared_input_invalidates_cached_result(self) -> None:
        write(self.repo / "src" / "local.py", "VALUE = 2\n")
        first_code, _ = self.invoke()

        write(self.repo / "tests" / "test_local.py", "assert 1 == 1\n")
        second_code, second = self.invoke()

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        statuses = {item["id"]: item["status"] for item in second["checks"]}
        self.assertEqual(statuses["local-check"], "executed")
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "2")

    def test_untracked_local_file_stays_selective(self) -> None:
        write(self.repo / "src" / "new.py", "VALUE = 3\n")

        code, report = self.invoke()

        self.assertEqual(code, 0)
        self.assertEqual(report["selection"]["mode"], "selective")
        self.assertIn("src/new.py", report["changes"]["paths"]["items"])
        entries = report["changes"]["entries"]["items"]
        self.assertIn(
            {"origin": "untracked", "status": "??", "paths": ["src/new.py"]},
            entries,
        )

    def test_global_input_change_runs_the_full_set(self) -> None:
        write(self.repo / "requirements.txt", "example==2\n")

        code, report = self.invoke()

        self.assertEqual(code, 0)
        self.assertEqual(report["selection"]["mode"], "full")
        self.assertTrue(report["selection"]["reasons"])
        statuses = {item["id"]: item["status"] for item in report["checks"]}
        self.assertEqual(statuses, {"local-check": "executed", "full-check": "executed"})
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "2")

    def test_indexed_rename_and_deletion_are_reported(self) -> None:
        git(self.repo, "mv", "src/local.py", "src/renamed.py")
        git(self.repo, "rm", "tests/test_local.py")

        code, report = self.invoke()

        self.assertEqual(code, 0)
        self.assertEqual(report["selection"]["mode"], "selective")
        paths = report["changes"]["paths"]["items"]
        self.assertEqual(paths, ["src/local.py", "src/renamed.py", "tests/test_local.py"])
        entries = report["changes"]["entries"]["items"]
        self.assertTrue(any(entry["status"].startswith("R") for entry in entries))
        self.assertIn(
            {"origin": "index", "status": "D", "paths": ["tests/test_local.py"]},
            entries,
        )

    def test_unmapped_path_expands_to_the_full_set(self) -> None:
        write(self.repo / "notes.txt", "Неизвестная область.\n")

        code, report = self.invoke()

        self.assertEqual(code, 0)
        self.assertEqual(report["selection"]["mode"], "full")
        self.assertIn("анализ влияния недоступен", report["selection"]["reasons"][0])
        statuses = {item["id"]: item["status"] for item in report["checks"]}
        self.assertEqual(statuses, {"local-check": "executed", "full-check": "executed"})

    def test_failed_check_is_not_cached(self) -> None:
        write(self.repo / "src" / "local.py", "VALUE = 2\n")
        write(
            self.repo / "project-verification.json",
            json.dumps(configuration(self.counter, "fail"), ensure_ascii=False, indent=2),
        )
        git(self.repo, "add", "project-verification.json")
        git(self.repo, "commit", "-m", "Настроена неуспешная проверка")
        write(self.repo / "src" / "local.py", "VALUE = 3\n")

        first_code, first = self.invoke()
        second_code, second = self.invoke()

        self.assertEqual(first_code, 1)
        self.assertEqual(second_code, 1)
        self.assertEqual(first["checks"][0]["status"], "executed")
        self.assertEqual(second["checks"][0]["status"], "executed")
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "2")


if __name__ == "__main__":
    unittest.main()
