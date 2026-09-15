import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "validate-skill-eval-scenario-executability.py",
)
SPEC = importlib.util.spec_from_file_location(
    "validate_skill_eval_scenario_executability",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def write_skill(
    root: Path,
    name: str,
    cases: list[dict],
) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n# {name}\n",
        encoding="utf-8",
    )
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir()
    (evals_dir / "result-scenarios.json").write_text(
        json.dumps({"skill_name": name, "cases": cases}, ensure_ascii=False),
        encoding="utf-8",
    )
    return skill_dir


def base_case(
    case_id: str,
    prompt: str,
    input_files: list[dict],
    artifact_change: bool | None = False,
) -> dict:
    case = {
        "id": case_id,
        "prompt": prompt,
        "input_files": input_files,
        "oracle": {"success_criteria": [], "failure_indicators": []},
        "expected_output": {"report_structure": []},
    }
    if artifact_change is not None:
        case["artifact_change"] = artifact_change
    return case


class ScenarioExecutabilityTests(unittest.TestCase):
    def test_rejects_prompt_artifact_without_content_or_real_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-draft",
                        "Доработай черновик `docs/decisions/ddr/0001-x.md`.",
                        [
                            {
                                "path": "docs/decisions/ddr/0001-x.md",
                                "purpose": "черновик",
                            },
                        ],
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(len(errors), 1)
            self.assertIn("0001-x.md", errors[0])

    def test_accepts_artifact_with_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-draft",
                        "Доработай черновик `docs/decisions/ddr/0001-x.md`.",
                        [
                            {
                                "path": "docs/decisions/ddr/0001-x.md",
                                "purpose": "черновик",
                                "content": "# черновик\n",
                            },
                        ],
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(errors, [])

    def test_accepts_artifact_that_really_exists_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            (repo_root / "docs").mkdir()
            (repo_root / "docs" / "real.md").write_text("x", encoding="utf-8")
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-real",
                        "Проверь файл `docs/real.md`.",
                        [
                            {"path": "docs/real.md", "purpose": "существующий файл"},
                        ],
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(errors, [])

    def test_ignores_case_without_referenced_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-new",
                        "Подготовь новую запись решения с нуля.",
                        [{"path": "docs/README.md", "purpose": "справка"}],
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(errors, [])

    def test_flags_artifact_referenced_only_in_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            case = base_case(
                "example-skill-oracle",
                "Подготовь новую запись решения.",
                [{"path": "docs/README.md", "purpose": "справка"}],
            )
            case["oracle"]["success_criteria"] = [
                "результат ссылается на `docs/decisions/ddr/0002-y.md`",
            ]
            skill_dir = write_skill(repo_root, "example-skill", [case])
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(len(errors), 1)
            self.assertIn("0002-y.md", errors[0])

    def test_requires_artifact_change_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-undeclared",
                        "Подготовь разбор без правки файлов.",
                        [{"path": "docs/README.md", "purpose": "справка"}],
                        artifact_change=None,
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(len(errors), 1)
            self.assertIn("artifact_change", errors[0])

    def test_rejects_declared_change_without_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-declared",
                        "Доработай черновик записи решения.",
                        [{"path": "docs/README.md", "purpose": "справка"}],
                        artifact_change=True,
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(len(errors), 1)
            self.assertIn("не кладёт его в рабочую копию", errors[0])

    def test_accepts_declared_change_with_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            skill_dir = write_skill(
                repo_root,
                "example-skill",
                [
                    base_case(
                        "example-skill-declared-ok",
                        "Доработай черновик записи решения.",
                        [
                            {
                                "path": "docs/decisions/adr/0001-x.md",
                                "purpose": "черновик",
                                "content": "# черновик\n",
                            },
                        ],
                        artifact_change=True,
                    ),
                ],
            )
            errors = VALIDATOR.validate_result_file(skill_dir, repo_root)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
