from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / ".apm/skills/ait-project-revalidation/scripts/project_review.py"
)
SPEC = importlib.util.spec_from_file_location("project_review", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run(*arguments: str, cwd: Path) -> None:
    subprocess.run(arguments, cwd=cwd, check=True, stdout=subprocess.DEVNULL)


class ProjectReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        run("git", "init", "-q", cwd=self.root)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.root)
        run("git", "config", "user.name", "Test", cwd=self.root)
        self.write(".gitignore", "ignored.txt\n")
        self.write("tracked.txt", "before\n")
        run("git", "add", ".gitignore", "tracked.txt", cwd=self.root)

        self.write(
            ".agents/skills/core-check/SKILL.md",
            "---\nname: core-check\ndescription: Проверяет ядро.\n---\n",
        )
        self.write(
            ".claude/skills/core-check/SKILL.md",
            "---\nname: core-check\ndescription: Проверяет ядро.\n---\n",
        )
        self.write(
            ".agents/skills/dep-check/SKILL.md",
            "---\nname: dep-check\ndescription: Проверяет зависимость.\n---\n",
        )
        self.write(".agents/skills/project-check/SKILL.md", "---\nname: x\n---\n")
        self.write(
            "apm.lock.yaml",
            "lockfile_version: '2'\n"
            "dependencies:\n"
            "- repo_url: example/dependency\n"
            "  deployed_files:\n"
            "  - .agents/skills/dep-check/SKILL.md\n"
            "  deployed_file_hashes:\n"
            "    value: hash\n",
        )
        self.classification = self.root / "capabilities.json"
        self.classification.write_text(
            json.dumps(
                {
                    "version": 1,
                    "stages": [
                        "repository",
                        "requirements",
                        "design",
                        "code",
                        "tests",
                        "assurance",
                        "impact",
                    ],
                    "capabilities": [
                        {
                            "id": "skill-core-check",
                            "kind": "skill",
                            "path": ".apm/skills/core-check",
                            "purpose": "Проверка ядра",
                            "participation": "check",
                            "stage": "repository",
                            "applicability": "always",
                        },
                    ],
                },
            ),
            encoding="utf-8",
        )
        self.original_classification = MODULE.CLASSIFICATION
        MODULE.CLASSIFICATION = self.classification

    def tearDown(self) -> None:
        MODULE.CLASSIFICATION = self.original_classification
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_snapshot_uses_git_scope(self) -> None:
        self.write("untracked.txt", "included\n")
        self.write("ignored.txt", "excluded\n")
        snapshot = MODULE.repository_snapshot(self.root)
        self.assertIn("tracked.txt", snapshot["files"])
        self.assertIn("untracked.txt", snapshot["files"])
        self.assertNotIn("ignored.txt", snapshot["files"])
        self.assertFalse(any(".git" in Path(name).parts for name in snapshot["files"]))

    def test_inventory_deduplicates_and_tracks_origins(self) -> None:
        inventory = MODULE.inventory(self.root, self.classification)
        by_id = {item["id"]: item for item in inventory["capabilities"]}
        core = by_id["skill:core-check"]
        self.assertEqual(core["origin"], "core")
        self.assertEqual(len(core["paths"]), 2)
        self.assertEqual(
            by_id["skill:dep-check"]["origin"],
            "dependency:example/dependency",
        )
        self.assertEqual(by_id["skill:project-check"]["origin"], "project")
        self.assertEqual(
            by_id["skill:project-check"]["classification"]["status"],
            "unknown",
        )

    def test_inventory_changes_when_lock_changes(self) -> None:
        before = MODULE.inventory(self.root, self.classification)["fingerprint"]
        self.write("apm.lock.yaml", "lockfile_version: '2'\n")
        after = MODULE.inventory(self.root, self.classification)["fingerprint"]
        self.assertNotEqual(before, after)

    def test_inventory_is_reproducible_and_discovers_new_project_skill(self) -> None:
        before = MODULE.inventory(self.root, self.classification)
        again = MODULE.inventory(self.root, self.classification)
        self.assertEqual(before, again)
        self.write(
            ".claude/skills/new-project-check/SKILL.md",
            "---\nname: new-project-check\ndescription: Проверяет дополнение.\n---\n",
        )
        after = MODULE.inventory(self.root, self.classification)
        by_id = {item["id"]: item for item in after["capabilities"]}
        self.assertIn("skill:new-project-check", by_id)
        self.assertEqual(
            by_id["skill:new-project-check"]["classification"]["status"],
            "unclassified",
        )
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])

    def test_inventory_works_without_apm_lock(self) -> None:
        (self.root / "apm.lock.yaml").unlink()
        inventory = MODULE.inventory(self.root, self.classification)
        by_id = {item["id"]: item for item in inventory["capabilities"]}
        self.assertEqual(by_id["skill:project-check"]["origin"], "project")
        self.assertEqual(
            by_id["skill:project-check"]["classification"]["status"],
            "unknown",
        )

    def test_managed_state_requires_proven_controller(self) -> None:
        with self.assertRaisesRegex(MODULE.ReviewError, "контроллера"):
            MODULE.new_state(self.root, "managed", "codex-goal", False)
        state = MODULE.new_state(self.root, "managed", "codex-goal", True)
        self.assertTrue(state["controller"]["proven"])

    def test_state_path_is_inside_git_service_directory(self) -> None:
        path = MODULE.state_path(self.root)
        git_dir = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--absolute-git-dir"],
                cwd=self.root,
                text=True,
            ).strip(),
        )
        self.assertTrue(path.is_relative_to(git_dir))

    def test_atomic_write_preserves_complete_document(self) -> None:
        path = MODULE.state_path(self.root)
        MODULE.atomic_write(path, {"value": 1})
        leftover = path.parent / f".{path.name}.interrupted"
        leftover.write_text('{"value":', encoding="utf-8")
        self.assertEqual(MODULE.load_json(path)["value"], 1)
        MODULE.atomic_write(path, {"value": 2})
        self.assertEqual(MODULE.load_json(path)["value"], 2)

    def test_state_restores_exact_next_action_after_interruption(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        MODULE.set_next(state, "Проверить входы этапа repository.")
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        _, restored = MODULE.load_state(self.root)
        self.assertEqual(
            restored["next_action"],
            "Проверить входы этапа repository.",
        )

    def test_invalid_transition_is_rejected(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        state["status"] = "complete"
        with self.assertRaisesRegex(MODULE.ReviewError, "недопустимый переход"):
            MODULE.transition(state, "running", "Повторить.")

    def test_external_change_interrupts_state(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        self.write("tracked.txt", "outside\n")
        MODULE.refresh(state, self.root)
        self.assertEqual(state["status"], "interrupted")
        self.assertIn("tracked.txt", state["history"][-1]["paths"])

    def test_approved_change_does_not_count_as_external(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Исправить файл",
            blocking=True,
            evidence=["tracked.txt"],
            group="group-1",
            allowed_path=["tracked.txt"],
            verification="test",
        )
        MODULE.record_finding(state, finding)
        decision = argparse.Namespace(
            finding="finding-1",
            decision="fix",
            reason=None,
            revisit_condition=None,
        )
        MODULE.record_decision(state, decision)
        self.write("tracked.txt", "approved\n")
        MODULE.refresh(state, self.root)
        self.assertNotEqual(state["status"], "interrupted")

    def test_unchanged_stage_is_reused_and_changed_capability_reopens_its_stage(
        self,
    ) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        state["stages"]["requirements"]["status"] = "complete"
        MODULE.refresh(state, self.root)
        self.assertEqual(state["stages"]["requirements"]["status"], "complete")
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-core-change",
                stage="repository",
                summary="Обновить проверку ядра",
                blocking=False,
                evidence=[],
                group=None,
                allowed_path=[".agents/skills/core-check/SKILL.md"],
                verification="inventory",
            ),
        )
        MODULE.record_decision(
            state,
            argparse.Namespace(
                finding="finding-core-change",
                decision="fix",
                reason=None,
                revisit_condition=None,
            ),
        )
        self.write(
            ".agents/skills/core-check/SKILL.md",
            "---\nname: core-check\ndescription: Изменённая проверка ядра.\n---\n",
        )
        MODULE.refresh(state, self.root)
        self.assertEqual(state["stages"]["repository"]["status"], "pending")
        self.assertEqual(state["stages"]["requirements"]["status"], "complete")

    def test_blocking_finding_prevents_stage_completion(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Блокер",
            blocking=True,
            evidence=[],
            group=None,
            allowed_path=[],
            verification=None,
        )
        MODULE.record_finding(state, finding)
        with self.assertRaisesRegex(MODULE.ReviewError, "нерешённые проблемы"):
            MODULE.set_stage(state, "repository", "complete")

    def test_one_decision_applies_to_whole_group(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        for identifier in ("finding-1", "finding-2"):
            MODULE.record_finding(
                state,
                argparse.Namespace(
                    id=identifier,
                    stage="repository",
                    summary=identifier,
                    blocking=False,
                    evidence=[],
                    group="group-1",
                    allowed_path=[f"{identifier}.txt"],
                    verification="test",
                ),
            )
        MODULE.record_decision(
            state,
            argparse.Namespace(
                finding="finding-1",
                decision="fix",
                reason=None,
                revisit_condition=None,
            ),
        )
        self.assertEqual(state["findings"]["finding-1"]["status"], "approved")
        self.assertEqual(state["findings"]["finding-2"]["status"], "approved")
        self.assertEqual(
            state["history"][-1]["targets"],
            ["finding-1", "finding-2"],
        )

    def test_fix_requires_boundary_and_verification(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Нет границы",
                blocking=False,
                evidence=[],
                group=None,
                allowed_path=[],
                verification=None,
            ),
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "разрешённых путей"):
            MODULE.record_decision(
                state,
                argparse.Namespace(
                    finding="finding-1",
                    decision="fix",
                    reason=None,
                    revisit_condition=None,
                ),
            )

    def test_blocking_finding_cannot_be_accepted(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Блокер",
            blocking=True,
            evidence=[],
            group=None,
            allowed_path=[],
            verification=None,
        )
        MODULE.record_finding(state, finding)
        decision = argparse.Namespace(
            finding="finding-1",
            decision="accept",
            reason="Дорого",
            revisit_condition="После выпуска",
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "блокирующую"):
            MODULE.record_decision(state, decision)

    def test_accepted_risk_requires_reason_and_revisit_condition(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Риск",
            blocking=False,
            evidence=[],
            group=None,
            allowed_path=[],
            verification=None,
        )
        MODULE.record_finding(state, finding)
        decision = argparse.Namespace(
            finding="finding-1",
            decision="accept",
            reason=None,
            revisit_condition=None,
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "причины"):
            MODULE.record_decision(state, decision)

    def test_completion_rejects_unclassified_capability(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        for stage in state["stages"].values():
            stage["status"] = "complete"
        with self.assertRaisesRegex(MODULE.ReviewError, "не классифицированы"):
            MODULE.validate_completion(state, "complete")

    def test_stage_requires_applicable_check_result(self) -> None:
        state = MODULE.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(MODULE.ReviewError, "не применил проверки"):
            MODULE.set_stage(state, "repository", "complete")
        MODULE.record_check(
            state,
            argparse.Namespace(
                id="check-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                status="passed",
                evidence=["test"],
            ),
        )
        MODULE.set_stage(state, "repository", "complete")
        self.assertEqual(state["stages"]["repository"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
