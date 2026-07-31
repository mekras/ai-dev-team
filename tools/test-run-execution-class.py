#!/usr/bin/env python3
"""Регрессионные проверки запуска классов исполнения подагентов."""

from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run-execution-class"


class RunExecutionClassTests(unittest.TestCase):
    def test_records_model_agent_path_and_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            adapter = temporary / "adapter"
            adapter.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import sys

                    model, effort, sandbox = sys.argv[1:]
                    request = json.load(sys.stdin)
                    print(json.dumps({"model": model, "usage": {"input_tokens": 3}}))
                    print(json.dumps({"status": "ok", "class": request["execution_class"]}))
                    """
                ),
                encoding="utf-8",
            )
            adapter.chmod(0o755)
            config = temporary / "subagents.local.toml"
            config.write_text(
                textwrap.dedent(
                    f"""\
                    [execution_classes.research]
                    writes = false
                    result = "status, evidence"

                    [targets.codex.execution_classes.research]
                    model = "test-model"
                    effort = "low"
                    sandbox = "read-only"
                    adapter = ["{adapter}"]
                    """
                ),
                encoding="utf-8",
            )
            output = temporary / "output"

            completed = subprocess.run(
                [
                    str(RUNNER),
                    "research",
                    "--target",
                    "codex",
                    "--config",
                    str(config),
                    "--out",
                    str(output),
                ],
                input="Проверь один факт.",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            record = json.loads(completed.stdout)
            self.assertEqual(record["assigned_model"], "test-model")
            self.assertEqual(record["actual_model"], "test-model")
            self.assertTrue(record["model_matches"])
            self.assertEqual(record["agent_path"], str(adapter.resolve()))
            self.assertEqual(record["contract"]["writes"], False)
            self.assertTrue(Path(record["journal"]).name.endswith(".jsonl"))

    def test_rejects_write_contract_with_read_only_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            adapter = temporary / "adapter"
            adapter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            adapter.chmod(0o755)
            config = temporary / "subagents.local.toml"
            config.write_text(
                textwrap.dedent(
                    f"""\
                    [execution_classes.patch]
                    writes = true

                    [targets.codex.execution_classes.patch]
                    model = "test-model"
                    effort = "low"
                    sandbox = "read-only"
                    adapter = ["{adapter}"]
                    """
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    str(RUNNER),
                    "patch",
                    "--target",
                    "codex",
                    "--config",
                    str(config),
                    "--out",
                    str(temporary / "output"),
                ],
                input="Правка.",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn(
                "writes класса не соответствует sandbox назначения",
                completed.stderr,
            )


if __name__ == "__main__":
    unittest.main()
