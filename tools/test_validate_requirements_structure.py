import importlib.util
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("validate-requirements-structure.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_requirements_structure",
    MODULE_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class BusinessRequirementValidationTests(unittest.TestCase):
    def write_requirement(self, root: Path, text: str) -> Path:
        path = root / "docs/requirements/business/bt-1.md"
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self, text: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_requirement(root, text)
            with mock.patch.object(VALIDATOR, "ROOT", root):
                VALIDATOR.check_requirement_file(path, "БТ-1")

    def test_accepts_explanation_before_evidence(self) -> None:
        self.check(
            """# БТ-1. Понятное требование

[К списку требований](../../requirements.md)

## Требование

Продукт должен давать проверяемый результат.

## Проверка

БТ-1 считается выполненным, если результат можно проверить.

1. Результат содержит свидетельство.
""",
        )

    def test_rejects_identifier_without_title(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                self.check(
                    """# БТ-1

[К списку требований](../../requirements.md)

## Требование

Продукт должен давать проверяемый результат.

## Проверка

БТ-1 считается выполненным, если результат можно проверить.
""",
                )

    def test_rejects_evidence_without_explanation(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                self.check(
                    """# БТ-1. Понятное требование

[К списку требований](../../requirements.md)

## Требование

Продукт должен давать проверяемый результат.

## Проверка

1. Результат содержит свидетельство.
""",
                )

    def test_rejects_abstract_check_explanation(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                self.check(
                    """# БТ-1. Понятное требование

[К списку требований](../../requirements.md)

## Требование

Продукт должен давать проверяемый результат.

## Проверка

Проверка БТ-1 показывает общий результат и границу вывода.

1. Результат содержит свидетельство.
""",
                )


class RequirementTitleValidationTests(unittest.TestCase):
    def check_requirement(
        self,
        category: str,
        filename: str,
        identifier: str,
        heading: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / f"docs/requirements/{category}/{filename}"
            path.parent.mkdir(parents=True)
            path.write_text(
                f"""# {heading}

[К списку требований](../../requirements.md)

## Требование

Продукт должен давать проверяемый результат.

## Проверка

Результат содержит свидетельство.
""",
                encoding="utf-8",
            )
            with mock.patch.object(VALIDATOR, "ROOT", root):
                VALIDATOR.check_requirement_file(path, identifier)

    def test_rejects_functional_identifier_without_title(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                self.check_requirement("functional", "ft-1.md", "ФТ-1", "ФТ-1")

    def test_rejects_rule_identifier_without_title(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                self.check_requirement("rules", "pr-1.md", "ПР-1", "ПР-1")

    def test_index_requires_full_title_for_every_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "docs/requirements.md"
            requirement = root / "docs/requirements/functional/ft-1.md"
            requirement.parent.mkdir(parents=True)
            index.write_text(
                """# Требования

- [ФТ-1](requirements/functional/ft-1.md)
""",
                encoding="utf-8",
            )
            requirement.write_text(
                "# ФТ-1. Содержательное название\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(VALIDATOR, "ROOT", root),
                mock.patch.object(VALIDATOR, "INDEX", index),
                redirect_stderr(StringIO()),
                self.assertRaises(SystemExit),
            ):
                VALIDATOR.check_index({requirement: "ФТ-1"})


if __name__ == "__main__":
    unittest.main()
