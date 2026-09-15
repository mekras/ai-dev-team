import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("record-skill-eval-run.py")
SPEC = importlib.util.spec_from_file_location(
    "record_skill_eval_run",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
RECORDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECORDER)


def write_skill(root: Path, name: str, case_ids: list[str]) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n# {name}\n",
        encoding="utf-8",
    )
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir()
    cases = [{"id": case_id, "prompt": "x"} for case_id in case_ids]
    (evals_dir / "result-scenarios.json").write_text(
        json.dumps({"skill_name": name, "cases": cases}, ensure_ascii=False),
        encoding="utf-8",
    )
    return skill_dir


class RecordRunTests(unittest.TestCase):
    def run_recorder(self, argv: list[str]) -> int:
        old_argv = sys.argv
        sys.argv = ["record-skill-eval-run.py", *argv]
        try:
            output = StringIO()
            with redirect_stdout(output):
                return RECORDER.main()
        finally:
            sys.argv = old_argv

    def test_records_run_date_for_every_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_skill(root, "example-skill", ["example-skill-a", "example-skill-b"])
            record_path = root / "runs.json"

            exit_code = self.run_recorder(
                [str(root), "--record", str(record_path), "--today", "2026-09-15"],
            )

            self.assertEqual(exit_code, 0)
            data = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["runs"],
                {
                    "example-skill-a": "2026-09-15",
                    "example-skill-b": "2026-09-15",
                },
            )

    def test_preserves_and_updates_existing_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_skill(root, "example-skill", ["example-skill-a"])
            record_path = root / "runs.json"
            record_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "runs": {
                            "example-skill-a": "2026-01-01",
                            "other-skill-x": "2026-02-02",
                        },
                    },
                ),
                encoding="utf-8",
            )

            self.run_recorder(
                [str(root), "--record", str(record_path), "--today", "2026-09-15"],
            )

            data = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["runs"],
                {
                    "example-skill-a": "2026-09-15",
                    "other-skill-x": "2026-02-02",
                },
            )


if __name__ == "__main__":
    unittest.main()
