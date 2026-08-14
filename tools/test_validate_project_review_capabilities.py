from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-project-review-capabilities.py")
SPEC = importlib.util.spec_from_file_location("capabilities_validator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CapabilityValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / ".apm/agents").mkdir(parents=True)
        (self.root / ".apm/skills/example").mkdir(parents=True)
        (self.root / ".apm/instructions").mkdir(parents=True)
        (self.root / ".apm/agents/analyst.agent.md").write_text(
            "# Аналитик\n",
            encoding="utf-8",
        )
        (self.root / ".apm/skills/example/SKILL.md").write_text(
            "# Example\n",
            encoding="utf-8",
        )
        (self.root / ".apm/instructions/rule.md").write_text(
            "# Правило\n",
            encoding="utf-8",
        )
        self.classification = self.root / "capabilities.json"
        self.data = {
            "version": 1,
            "stages": ["repository"],
            "capabilities": [
                self.entry(
                    "role-analyst",
                    "role",
                    ".apm/agents/analyst.agent.md",
                ),
                self.entry("skill-example", "skill", ".apm/skills/example"),
                self.entry(
                    "rule-example",
                    "rule",
                    ".apm/instructions/rule.md",
                ),
            ],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def entry(identifier: str, kind: str, path: str) -> dict[str, object]:
        return {
            "id": identifier,
            "kind": kind,
            "path": path,
            "purpose": "Проверка",
            "participation": "check",
            "stage": "repository",
            "applicability": "model",
        }

    def write(self) -> None:
        self.classification.write_text(
            json.dumps(self.data),
            encoding="utf-8",
        )

    def test_complete_classification_passes(self) -> None:
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_component_name_derives_portable_path(self) -> None:
        entry = self.data["capabilities"][0]
        entry.pop("path")
        entry["name"] = "analyst"
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_new_skill_without_entry_fails(self) -> None:
        (self.root / ".apm/skills/new-skill").mkdir()
        self.write()
        with self.assertRaisesRegex(MODULE.CapabilityError, "new-skill"):
            MODULE.validate(self.root, self.classification)

    def test_added_entry_closes_missing_skill(self) -> None:
        (self.root / ".apm/skills/new-skill").mkdir()
        self.data["capabilities"].append(
            self.entry(
                "skill-new",
                "skill",
                ".apm/skills/new-skill",
            ),
        )
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_orphaned_entry_fails(self) -> None:
        self.data["capabilities"].append(
            self.entry(
                "skill-missing",
                "skill",
                ".apm/skills/missing",
            ),
        )
        self.write()
        with self.assertRaisesRegex(MODULE.CapabilityError, "не существует"):
            MODULE.validate(self.root, self.classification)

    def test_external_component_is_explicitly_allowed(self) -> None:
        entry = self.entry(
            "skill-external",
            "skill",
            ".external/skills/example",
        )
        entry["external"] = True
        self.data["capabilities"].append(entry)
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_external_component_cannot_hide_local_component(self) -> None:
        entry = self.data["capabilities"][1]
        entry["external"] = True
        self.write()
        with self.assertRaisesRegex(MODULE.CapabilityError, "не может быть локальным"):
            MODULE.validate(self.root, self.classification)

    def test_not_applicable_component_remains_accounted_for(self) -> None:
        entry = self.data["capabilities"][1]
        entry["participation"] = "not_applicable"
        entry["applicability"] = "never"
        entry["stage"] = None
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_unknown_stage_fails(self) -> None:
        self.data["capabilities"][0]["stage"] = "unknown"
        self.write()
        with self.assertRaisesRegex(MODULE.CapabilityError, "неизвестный этап"):
            MODULE.validate(self.root, self.classification)

    def test_unknown_participation_fails(self) -> None:
        self.data["capabilities"][0]["participation"] = "mystery"
        self.write()
        with self.assertRaisesRegex(
            MODULE.CapabilityError,
            "неизвестный participation",
        ):
            MODULE.validate(self.root, self.classification)

    def test_review_criteria_contract_passes(self) -> None:
        entry = self.data["capabilities"][1]
        entry["subject_discovery_required"] = True
        entry["review_criteria"] = [
            {
                "id": "traceability",
                "description": "Проверить направление связей.",
                "coverage": "each_subject",
            },
        ]
        self.write()
        MODULE.validate(self.root, self.classification)

    def test_unknown_review_criterion_coverage_fails(self) -> None:
        entry = self.data["capabilities"][1]
        entry["review_criteria"] = [
            {
                "id": "traceability",
                "description": "Проверить направление связей.",
                "coverage": "sometimes",
            },
        ]
        self.write()
        with self.assertRaisesRegex(
            MODULE.CapabilityError,
            "неизвестный охват критерия",
        ):
            MODULE.validate(self.root, self.classification)


if __name__ == "__main__":
    unittest.main()
