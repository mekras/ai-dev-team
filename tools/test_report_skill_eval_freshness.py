import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("report-skill-eval-freshness.py")
SPEC = importlib.util.spec_from_file_location(
    "report_skill_eval_freshness",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
REPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORTER)


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


class FreshnessReportTests(unittest.TestCase):
    def test_reports_case_never_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_skill(root, "example-skill", ["example-skill-a"])
            record_path = root / "runs.json"

            skill_dirs = REPORTER.find_skill_dirs([root])
            case_ids = REPORTER.collect_case_ids(skill_dirs)
            runs = REPORTER.load_record(record_path)

            self.assertEqual(case_ids, {"example-skill-a": "example-skill"})
            self.assertEqual(runs, {})

    def test_recent_run_is_not_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_skill(root, "example-skill", ["example-skill-a"])
            record_path = root / "runs.json"
            record_path.write_text(
                json.dumps(
                    {"schema_version": 1, "runs": {"example-skill-a": "2026-09-01"}},
                ),
                encoding="utf-8",
            )

            import sys

            argv = sys.argv
            sys.argv = [
                "report-skill-eval-freshness.py",
                str(root),
                "--record",
                str(record_path),
                "--threshold-days",
                "30",
                "--today",
                "2026-09-10",
            ]
            try:
                output = StringIO()
                with redirect_stdout(output):
                    exit_code = REPORTER.main()
            finally:
                sys.argv = argv

            self.assertEqual(exit_code, 0)
            self.assertIn("исполнялись в пределах", output.getvalue())

    def test_old_run_is_reported_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_skill(root, "example-skill", ["example-skill-a"])
            record_path = root / "runs.json"
            record_path.write_text(
                json.dumps(
                    {"schema_version": 1, "runs": {"example-skill-a": "2026-01-01"}},
                ),
                encoding="utf-8",
            )

            import sys

            argv = sys.argv
            sys.argv = [
                "report-skill-eval-freshness.py",
                str(root),
                "--record",
                str(record_path),
                "--threshold-days",
                "30",
                "--today",
                "2026-09-10",
            ]
            try:
                output = StringIO()
                with redirect_stdout(output):
                    exit_code = REPORTER.main()
            finally:
                sys.argv = argv

            self.assertEqual(exit_code, 0)
            self.assertIn("Не исполнялись дольше 30 дней", output.getvalue())
            self.assertIn("example-skill-a", output.getvalue())


if __name__ == "__main__":
    unittest.main()
