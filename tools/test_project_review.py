from __future__ import annotations

import argparse
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True


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
        self.write(".gitignore", "ignored.txt\n.ai-dev-team/local/\n")
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

    def new_state(
        self,
        repo: Path,
        mode: str,
        controller: str | None,
        controller_proven: bool,
    ) -> dict[str, object]:
        state = self.pending_concept_state(
            mode=mode,
            controller=controller,
            controller_proven=controller_proven,
        )
        self.complete_concept_review(state)
        self.complete_knowledge_review(state)
        state["stages"]["requirements"]["status"] = "pending"
        state["stages"]["repository"]["status"] = "pending"
        state["current_stage"] = None
        return state

    def pending_concept_state(
        self,
        mode: str = "manual",
        controller: str | None = None,
        controller_proven: bool = False,
    ) -> dict[str, object]:
        self.write(
            "AGENTS.md",
            "Главный ориентир проекта находится в `docs/concept.md`.\n",
        )
        self.write(
            "docs/concept.md",
            "# Концепция\n\n"
            "Проблема проекта связана с ручной работой. Цель состоит в её "
            "сокращении через автоматизацию. Итогом станет рабочий инструмент. "
            "Проект ограничен локальным применением.\n",
        )
        concept_skill = (
            "---\n"
            "name: ait-docs-concept\n"
            "description: Проверяет концепцию проекта.\n"
            "---\n"
        )
        self.write(
            ".agents/skills/ait-docs-concept/SKILL.md",
            concept_skill,
        )
        self.write(
            ".claude/skills/ait-docs-concept/SKILL.md",
            concept_skill,
        )
        knowledge_skill = (
            "---\n"
            "name: kc-validation\n"
            "description: Проверяет корпус знаний.\n"
            "---\n"
        )
        self.write(
            ".agents/skills/kc-validation/SKILL.md",
            knowledge_skill,
        )
        self.write(
            ".claude/skills/kc-validation/SKILL.md",
            knowledge_skill,
        )
        self.write("knowledge/corpus.yml", "version: 2\n")
        self.write("knowledge/catalog.yml", "sources: [test]\n")
        self.write(
            "knowledge/data/test/source.yml",
            "id: TEST\nname: Проверяемый источник\n",
        )
        self.write(
            "knowledge/data/test/statements.yml",
            "statements:\n  - id: TEST-001\n    text: Основание проекта.\n",
        )
        classification = json.loads(
            self.classification.read_text(encoding="utf-8"),
        )
        classification["capabilities"].append(
            {
                "id": "skill-ait-docs-concept",
                "kind": "skill",
                "path": ".apm/skills/ait-docs-concept",
                "purpose": "Проверка концепции проекта",
                "participation": "check",
                "stage": "requirements",
                "applicability": "always",
                "review_criteria": [
                    {
                        "id": "problem-goal-method-result",
                        "description": "Проверить связь проблемы и цели.",
                        "coverage": "surface",
                    },
                    {
                        "id": "essential-frames",
                        "description": "Проверить существенные рамки замысла.",
                        "coverage": "surface",
                    },
                    {
                        "id": "meaning-and-modality",
                        "description": "Проверить согласованность положений.",
                        "coverage": "surface",
                    },
                ],
            },
        )
        classification["capabilities"].append(
            {
                "id": "skill-kc-validation",
                "kind": "skill",
                "path": ".apm/skills/kc-validation",
                "purpose": "Проверка корпуса знаний",
                "participation": "check",
                "stage": "repository",
                "applicability": "always",
            },
        )
        self.classification.write_text(
            json.dumps(classification),
            encoding="utf-8",
        )
        return MODULE.new_state(
            self.root,
            mode,
            controller,
            controller_proven,
        )

    def locate_concept(self, state: dict[str, object]) -> None:
        MODULE.record_concept_discovery(
            state,
            argparse.Namespace(
                result="found",
                instructions="AGENTS.md",
                concept=["docs/concept.md"],
                evidence=[
                    "Корневые инструкции содержат точный путь к концепции.",
                ],
            ),
            self.root,
        )

    def complete_concept_review(self, state: dict[str, object]) -> None:
        self.locate_concept(state)
        capability = state["concept_review"]["capability"]
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="concept-review",
                stage="requirements",
                capability=capability,
                finding=None,
                method="review",
                surface="Полная найденная концепция проекта.",
                action="Содержательно проверить концепцию.",
                priority_rationale=(
                    "Концепция является обязательным основанием остальных "
                    "областей."
                ),
                subject=["docs/concept.md"],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        for index, criterion_id in enumerate(
            (
                "problem-goal-method-result",
                "essential-frames",
                "meaning-and-modality",
            ),
            start=1,
        ):
            MODULE.record_observation(
                state,
                argparse.Namespace(
                    application="concept-review",
                    artifact="docs/concept.md",
                    start_line=1,
                    end_line=3,
                    criterion_id=criterion_id,
                    criterion=None,
                    result="supports",
                    note=f"Содержание подтверждает критерий {criterion_id}.",
                ),
                self.root,
            )
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="concept-review",
                outcome="passed",
                decision="accept",
                evidence=["Проверены все профильные критерии концепции."],
                artifact=["docs/concept.md"],
                coverage="Весь найденный документ концепции.",
                claim=["Концепция содержит согласованное смысловое основание."],
                claim_support=["observation-001"],
                challenge=(
                    "Возможно, текст описывает только функции без цели проекта."
                ),
                challenge_outcome="refuted",
                challenge_support=["observation-001", "observation-003"],
                command=None,
            ),
            self.root,
        )

    def locate_knowledge(self, state: dict[str, object]) -> None:
        MODULE.record_knowledge_discovery(
            state,
            argparse.Namespace(
                result="found",
                root="knowledge",
                evidence=[
                    "Корневые правила и договор корпуса указывают на knowledge.",
                ],
            ),
            self.root,
        )

    def complete_knowledge_review(self, state: dict[str, object]) -> None:
        self.locate_knowledge(state)
        capability = state["knowledge_review"]["capability"]
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="knowledge-technical",
                stage="repository",
                capability=capability,
                finding=None,
                method="validation",
                surface="Полный доступный состав корпуса знаний.",
                action="Проверить технический допуск корпуса.",
                priority_rationale=(
                    "Технический допуск обязателен перед смысловым проходом."
                ),
                knowledge_phase="technical",
                subject=[],
                subject_index=[],
                subject_pattern=["knowledge/**"],
            ),
            self.root,
        )
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="knowledge-technical",
                outcome="passed",
                decision=None,
                evidence=["Состав и происхождение корпуса доступны."],
                artifact=["knowledge/corpus.yml"],
                coverage="Весь доступный состав корпуса.",
                claim=["Корпус доступен для смысловой проверки."],
                claim_support=[],
                challenge=None,
                challenge_outcome=None,
                challenge_support=[],
                command=None,
            ),
            self.root,
        )
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="knowledge-semantic",
                stage="repository",
                capability=capability,
                finding=None,
                method="review",
                surface="Источники и утверждения корпуса относительно концепции.",
                action="Содержательно проверить корпус относительно концепции.",
                priority_rationale=(
                    "Корпус является обязательным вторым основанием проверки."
                ),
                knowledge_phase="semantic",
                subject=[],
                subject_index=[],
                subject_pattern=[
                    "knowledge/corpus.yml",
                    "knowledge/catalog.yml",
                    "knowledge/**/source.yml",
                    "knowledge/**/statements.yml",
                ],
            ),
            self.root,
        )
        observation_ids = []
        for artifact in (
            "knowledge/catalog.yml",
            "knowledge/corpus.yml",
            "knowledge/data/test/source.yml",
            "knowledge/data/test/statements.yml",
        ):
            observation = MODULE.record_observation(
                state,
                argparse.Namespace(
                    application="knowledge-semantic",
                    artifact=artifact,
                    start_line=1,
                    end_line=1,
                    criterion_id="source-concept-fit",
                    criterion=None,
                    result="supports",
                    note=(
                        "Содержание файла "
                        f"{artifact} связано с проблемой и целью концепции."
                    ),
                ),
                self.root,
            )
            observation_ids.append(observation["id"])
        for criterion_id in (
            "statement-consistency",
            "coverage-gaps",
            "decision-value",
        ):
            observation = MODULE.record_observation(
                state,
                argparse.Namespace(
                    application="knowledge-semantic",
                    artifact="knowledge/data/test/statements.yml",
                    start_line=1,
                    end_line=2,
                    criterion_id=criterion_id,
                    criterion=None,
                    result="supports",
                    note=f"Корпус подтверждает критерий {criterion_id}.",
                ),
                self.root,
            )
            observation_ids.append(observation["id"])
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="knowledge-semantic",
                outcome="passed",
                decision="accept",
                evidence=["Источники и утверждения сопоставлены с концепцией."],
                artifact=[
                    "knowledge/data/test/source.yml",
                    "knowledge/data/test/statements.yml",
                ],
                coverage="Все источники, утверждения и договор корпуса.",
                claim=["Доступный корпус соответствует концепции проекта."],
                claim_support=[observation_ids[0]],
                challenge=(
                    "Возможно, источник относится к цели только формально."
                ),
                challenge_outcome="refuted",
                challenge_support=[observation_ids[-1]],
                command=None,
            ),
            self.root,
        )

    def prepare_decision(
        self,
        state: dict[str, object],
        finding: str = "finding-1",
        problems: list[str] | None = None,
    ) -> dict[str, object]:
        return MODULE.prepare_decision(
            state,
            argparse.Namespace(
                finding=finding,
                review_context="Полная проверка тестового проекта",
                checked_subject="механизм, который управляет тестовым проходом",
                relation=(
                    "этот механизм определяет достоверность результатов "
                    "остальных областей"
                ),
                problem=problems or ["Механизм допускает неверный результат."],
                impact=(
                    "проверка может сообщить об успехе при оставшейся проблеме"
                ),
                proposed_change="исправить механизм в указанной границе",
                decision_question="Одобряете исправление этой группы?",
            ),
            self.root,
        )

    def accept_snapshot(
        self,
        state: dict[str, object],
        finding_ids: list[str] | None = None,
        external_paths: list[str] | None = None,
        external_reason: str | None = None,
        reopen_stages: list[str] | None = None,
    ) -> None:
        MODULE.accept_pending_snapshot(
            state,
            self.root,
            finding_ids,
            external_paths,
            external_reason,
            reopen_stages or ["repository"],
            "Изменение затрагивает проверку репозитория.",
        )

    def test_snapshot_uses_git_scope(self) -> None:
        self.write("untracked.txt", "included\n")
        self.write("ignored.txt", "excluded\n")
        snapshot = MODULE.repository_snapshot(self.root)
        self.assertIn("tracked.txt", snapshot["files"])
        self.assertIn("untracked.txt", snapshot["files"])
        self.assertNotIn("ignored.txt", snapshot["files"])
        self.assertFalse(any(".git" in Path(name).parts for name in snapshot["files"]))

    def test_snapshot_changes_when_executable_mode_changes(self) -> None:
        before = MODULE.repository_snapshot(self.root)
        tracked = self.root / "tracked.txt"
        tracked.chmod(tracked.stat().st_mode | 0o111)
        after = MODULE.repository_snapshot(self.root)

        self.assertNotEqual(before["id"], after["id"])
        self.assertTrue(after["metadata"]["tracked.txt"]["worktree_executable"])

    def test_snapshot_tracks_gitlink_object(self) -> None:
        empty_tree = subprocess.check_output(
            ["git", "mktree"],
            cwd=self.root,
            input=b"",
        ).decode().strip()
        first = subprocess.check_output(
            ["git", "commit-tree", empty_tree, "-m", "first"],
            cwd=self.root,
        ).decode().strip()
        second = subprocess.check_output(
            ["git", "commit-tree", empty_tree, "-m", "second"],
            cwd=self.root,
        ).decode().strip()
        run(
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{first},vendor/module",
            cwd=self.root,
        )
        before = MODULE.repository_snapshot(self.root)
        run(
            "git",
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{second},vendor/module",
            cwd=self.root,
        )
        after = MODULE.repository_snapshot(self.root)

        self.assertNotEqual(before["id"], after["id"])
        entry = after["metadata"]["vendor/module"]["index"][0]
        self.assertEqual(entry["mode"], "160000")
        self.assertEqual(entry["object"], second)

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

    def test_inventory_ignores_local_files_outside_git_scope(self) -> None:
        self.write(
            ".ai-dev-team/local/skills/ignored-check/SKILL.md",
            "---\nname: ignored-check\ndescription: Не учитывать.\n---\n",
        )

        inventory = MODULE.inventory(self.root, self.classification)
        identifiers = {item["id"] for item in inventory["capabilities"]}

        self.assertNotIn("skill:ignored-check", identifiers)

    def test_inventory_changes_when_lock_changes(self) -> None:
        before = MODULE.inventory(self.root, self.classification)["fingerprint"]
        self.write("apm.lock.yaml", "lockfile_version: '2'\n")
        after = MODULE.inventory(self.root, self.classification)["fingerprint"]
        self.assertNotEqual(before, after)

    def test_inventory_input_hash_includes_supplied_classification(self) -> None:
        before = MODULE.inventory(self.root, self.classification)
        before_item = next(
            item
            for item in before["capabilities"]
            if item["id"] == "skill:core-check"
        )
        classification = json.loads(
            self.classification.read_text(encoding="utf-8"),
        )
        classification["capabilities"][0]["stage"] = "design"
        self.classification.write_text(
            json.dumps(classification),
            encoding="utf-8",
        )
        after = MODULE.inventory(self.root, self.classification)
        after_item = next(
            item
            for item in after["capabilities"]
            if item["id"] == "skill:core-check"
        )

        self.assertNotEqual(before_item["input_hash"], after_item["input_hash"])
        self.assertEqual(after_item["classification"]["stage"], "design")

    def test_refresh_migrates_legacy_component_hash_without_reclassification(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        item = next(
            item
            for item in state["capability_inventory"]["capabilities"]
            if item["id"] == "skill:core-check"
        )
        decision = state["capability_decisions"]["skill:core-check"]
        decision["input_hash"] = item["component_input_hash"]
        decision["reason"] = "Проверенное прежнее решение."
        state["capability_inventory"]["fingerprint"] = "legacy"

        MODULE.refresh(state, self.root)

        migrated = state["capability_decisions"]["skill:core-check"]
        self.assertEqual(
            migrated["input_hash"],
            MODULE.stable_hash(
                {
                    "capability": item["input_hash"],
                    "ontology_scope": migrated["ontology_scope"],
                },
            ),
        )
        self.assertEqual(migrated["reason"], "Проверенное прежнее решение.")
        self.assertEqual(state["status"], "running")

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
            self.new_state(self.root, "managed", "codex-goal", False)
        state = self.new_state(self.root, "managed", "codex-goal", True)
        self.assertTrue(state["controller"]["proven"])

    def test_new_state_rejects_technical_first_application(self) -> None:
        state = self.pending_concept_state()

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "найдите концепцию",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="technical-first",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Код контроллера.",
                    action="Проверить код контроллера.",
                    priority_rationale="Техническая проверка выполняется быстро.",
                ),
                self.root,
            )

    def test_missing_concept_blocks_full_review(self) -> None:
        state = self.pending_concept_state()
        self.write(
            "AGENTS.md",
            "Корневые инструкции не содержат указателя на концепцию.\n",
        )
        (self.root / "docs/concept.md").unlink()
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        MODULE.record_concept_discovery(
            state,
            argparse.Namespace(
                result="missing",
                instructions="AGENTS.md",
                concept=[],
                evidence=[
                    "Корневые инструкции и точки входа не называют концепцию.",
                ],
            ),
            self.root,
        )

        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["concept_review"]["status"], "blocked")
        self.assertEqual(
            state["concept_review"]["instructions"]["reference"],
            "AGENTS.md",
        )
        self.assertTrue(state["concept_review"]["instructions"]["sha256"])
        self.assertTrue(state["concept_review"]["evidence"])
        MODULE.validate_state(state)

    def test_ambiguous_concept_blocks_full_review(self) -> None:
        state = self.pending_concept_state()
        self.write(
            "docs/concept-alternative.md",
            "# Другая концепция\n\nИной замысел проекта.\n",
        )
        self.write(
            "AGENTS.md",
            "В проекте упомянуты `docs/concept.md` и "
            "`docs/concept-alternative.md` без выбора основного документа.\n",
        )
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        MODULE.record_concept_discovery(
            state,
            argparse.Namespace(
                result="ambiguous",
                instructions="AGENTS.md",
                concept=[
                    "docs/concept.md",
                    "docs/concept-alternative.md",
                ],
                evidence=[
                    "Две точки входа называют разные документы концепцией.",
                ],
            ),
            self.root,
        )

        self.assertEqual(state["status"], "blocked")
        self.assertIn("указатель", state["next_action"])
        self.assertEqual(len(state["concept_review"]["subjects"]), 2)
        self.assertTrue(
            all(
                item["sha256"]
                for item in state["concept_review"]["subjects"]
            ),
        )

    def test_concept_discovery_accepts_file_ignored_by_git(self) -> None:
        state = self.pending_concept_state()
        self.write(".gitignore", "ignored-concept.md\n")
        self.write("docs/ignored-concept.md", "# Концепция\n")
        self.write(
            "AGENTS.md",
            "Концепция проекта: `docs/ignored-concept.md`.\n",
        )
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        self.assertNotIn("docs/ignored-concept.md", state["snapshot"]["files"])

        MODULE.record_concept_discovery(
            state,
            argparse.Namespace(
                result="found",
                instructions="AGENTS.md",
                concept=["docs/ignored-concept.md"],
                evidence=["Инструкции указывают на представление концепции."],
            ),
            self.root,
        )

        self.assertEqual(state["concept_review"]["status"], "located")
        self.assertEqual(
            state["concept_review"]["subjects"][0]["reference"],
            "docs/ignored-concept.md",
        )

    def test_concept_discovery_requires_exact_root_pointer(self) -> None:
        state = self.pending_concept_state()
        self.write(
            "AGENTS.md",
            "Перед работой учитывайте главный ориентир проекта.\n",
        )
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "точный путь",
        ):
            self.locate_concept(state)

    def test_only_concept_capability_can_be_first_application(self) -> None:
        state = self.pending_concept_state()
        self.locate_concept(state)

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "первым применением",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="requirements-first",
                    stage="requirements",
                    capability="skill:core-check",
                    finding=None,
                    method="review",
                    surface="Другие требования.",
                    action="Проверить требования.",
                    priority_rationale=(
                        "Требования влияют на дальнейшую реализацию."
                    ),
                ),
                self.root,
            )

    def test_completed_concept_review_opens_only_knowledge_stage(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)

        self.assertEqual(state["concept_review"]["status"], "checked")
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "зарегистрируйте корпус",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="technical-after-concept",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Состав репозитория.",
                    action="Проверить состав репозитория.",
                    priority_rationale=(
                        "После концепции эта проверка даёт наибольшую пользу."
                    ),
                ),
                self.root,
            )

    def test_absent_knowledge_corpus_records_second_stage(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)

        MODULE.record_knowledge_discovery(
            state,
            argparse.Namespace(
                result="absent",
                root=None,
                evidence=[
                    "Правила проекта и область Git не объявляют корпус знаний.",
                ],
            ),
            self.root,
        )

        self.assertEqual(state["knowledge_review"]["status"], "absent")
        self.assertTrue(MODULE.knowledge_review_is_proven(state))

    def test_absent_knowledge_rejects_unrelated_technical_phase(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        MODULE.record_knowledge_discovery(
            state,
            argparse.Namespace(
                result="absent",
                root=None,
                evidence=["Корпус знаний в проекте не объявлен."],
            ),
            self.root,
        )

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "knowledge-phase недопустим",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="security-technical-phase",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Граница безопасности.",
                    action="Проверить границу безопасности.",
                    priority_rationale="Проверка относится к репозиторию.",
                    knowledge_phase="technical",
                    subject=[],
                    subject_index=[],
                    subject_pattern=[],
                ),
                self.root,
            )

    def test_validate_rejects_phase_recorded_for_absent_knowledge(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        MODULE.record_knowledge_discovery(
            state,
            argparse.Namespace(
                result="absent",
                root=None,
                evidence=["Корпус знаний в проекте не объявлен."],
            ),
            self.root,
        )
        state["knowledge_review"]["technical_application"] = "security-check"

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "отсутствующий корпус",
        ):
            MODULE.validate_state(state)

    def test_validate_rejects_phase_before_knowledge_admission(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        self.locate_knowledge(state)
        state["knowledge_review"]["technical_application"] = "security-check"

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "без запущенной фазы",
        ):
            MODULE.validate_state(state)

    def test_validate_rejects_knowledge_phase_in_another_stage(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        self.complete_knowledge_review(state)
        technical = state["knowledge_review"]["technical_application"]
        state["applications"][technical]["stage"] = "assurance"

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "фаза корпуса должна относиться",
        ):
            MODULE.validate_state(state)

    def test_validate_does_not_report_running_review_as_complete(self) -> None:
        state = self.pending_concept_state()
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        arguments = [str(SCRIPT), "validate", "--repo", str(self.root)]
        output = io.StringIO()

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(sys, "stdout", output),
        ):
            MODULE.main()

        self.assertIn("remains in progress", output.getvalue())

    def test_technical_admission_precedes_semantic_knowledge_review(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        self.locate_knowledge(state)
        capability = state["knowledge_review"]["capability"]

        with self.assertRaisesRegex(MODULE.ReviewError, "текущую фазу technical"):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="knowledge-semantic-too-early",
                    stage="repository",
                    capability=capability,
                    finding=None,
                    method="review",
                    surface="Корпус относительно концепции.",
                    action="Смыслово проверить корпус.",
                    priority_rationale="Корпус является вторым основанием.",
                    knowledge_phase="semantic",
                    subject=[],
                    subject_index=[],
                    subject_pattern=["knowledge/**"],
                ),
                self.root,
            )

    def test_semantic_retry_clears_previous_outcome(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        knowledge = state["knowledge_review"]
        previous = state["applications"]["knowledge-semantic"]
        previous["outcome"] = "failed"
        previous["decision"] = "revise"
        knowledge["status"] = "semantic_failed"
        knowledge["semantic_outcome"] = "failed"

        MODULE.start_application(
            state,
            argparse.Namespace(
                id="knowledge-semantic-retry",
                stage="repository",
                capability=knowledge["capability"],
                finding=None,
                method="review",
                surface="Корпус относительно концепции.",
                action="Повторить смысловую проверку корпуса.",
                priority_rationale=(
                    "Повторная проверка обязательна после снятия находки."
                ),
                knowledge_phase="semantic",
                subject=[],
                subject_index=[],
                subject_pattern=[
                    "knowledge/corpus.yml",
                    "knowledge/catalog.yml",
                    "knowledge/**/source.yml",
                    "knowledge/**/statements.yml",
                ],
            ),
            self.root,
        )

        self.assertEqual(knowledge["status"], "semantic_running")
        self.assertIsNone(knowledge["semantic_outcome"])
        MODULE.validate_state(state)

    def test_failed_concept_review_does_not_open_other_work(self) -> None:
        state = self.pending_concept_state()
        self.locate_concept(state)
        capability = state["concept_review"]["capability"]
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="concept-failed",
                stage="requirements",
                capability=capability,
                finding=None,
                method="review",
                surface="Полная найденная концепция проекта.",
                action="Содержательно проверить концепцию.",
                priority_rationale=(
                    "Концепция является обязательным основанием остальных "
                    "областей."
                ),
                subject=["docs/concept.md"],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        for index, criterion_id in enumerate(
            (
                "problem-goal-method-result",
                "essential-frames",
                "meaning-and-modality",
            ),
            start=1,
        ):
            MODULE.record_observation(
                state,
                argparse.Namespace(
                    application="concept-failed",
                    artifact="docs/concept.md",
                    start_line=1,
                    end_line=3,
                    criterion_id=criterion_id,
                    criterion=None,
                    result="problem" if index == 1 else "supports",
                    note=f"Проверен критерий {criterion_id}.",
                ),
                self.root,
            )
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="concept-problem",
                stage="requirements",
                summary="Цель не следует из описанной проблемы.",
                blocking=True,
                evidence=["Наблюдение observation-001."],
                observation=["observation-001"],
                group=None,
                allowed_path=["docs/concept.md"],
                verification="Повторить смысловую проверку концепции.",
            ),
        )
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="concept-failed",
                outcome="failed",
                decision="revise",
                evidence=["Связь проблемы и цели не подтверждена."],
                artifact=["docs/concept.md"],
                coverage="Весь найденный документ концепции.",
                claim=["Концепция содержит смысловое противоречие."],
                claim_support=["observation-001"],
                challenge="Возможно, связь цели раскрыта в том же документе.",
                challenge_outcome="confirmed",
                challenge_support=["observation-001"],
                command=None,
            ),
            self.root,
        )

        self.assertEqual(state["concept_review"]["status"], "failed")
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "только её исправление",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="technical-after-failure",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Код контроллера.",
                    action="Проверить код.",
                    priority_rationale="Код влияет на дальнейшие проверки.",
                ),
                self.root,
            )

    def test_fabricated_checked_concept_is_rejected(self) -> None:
        state = self.pending_concept_state()
        state["concept_review"]["status"] = "checked"
        state["concept_review"]["outcome"] = "passed"

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанное применение",
        ):
            MODULE.validate_state(state)
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "найдите концепцию",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="technical-with-fabricated-gate",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Код контроллера.",
                    action="Проверить код.",
                    priority_rationale="Код влияет на дальнейшие проверки.",
                ),
                self.root,
            )

    def test_checked_concept_with_incomplete_application_is_rejected(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        application_id = state["concept_review"]["application"]
        state["applications"][application_id]["coverage"] = None

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанное применение",
        ):
            MODULE.validate_state(state)
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "найдите концепцию",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="technical-with-incomplete-proof",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Код контроллера.",
                    action="Проверить код.",
                    priority_rationale="Код влияет на дальнейшие проверки.",
                ),
                self.root,
            )

    def test_applicable_classification_requires_stage(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(MODULE.ReviewError, "требует область"):
            MODULE.classify_capability(
                state,
                argparse.Namespace(
                    id="skill:project-check",
                    participation="check",
                    stage=None,
                    applicable="yes",
                    reason="Проверка нужна.",
                ),
            )

    def test_last_unknown_classification_restores_running_state(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        target = "skill:project-check"
        for identifier, decision in state["capability_decisions"].items():
            if identifier == target:
                decision["status"] = "unknown"
                decision["applicable"] = None
                continue
            decision.update(
                {
                    "status": "classified",
                    "participation": "not_applicable",
                    "applicable": False,
                },
            )
        state["status"] = "blocked"
        state["next_action"] = "Классифицировать изменившиеся возможности."

        MODULE.classify_capability(
            state,
            argparse.Namespace(
                id=target,
                participation="check",
                stage="code",
                applicable="yes",
                reason="Возможность проверяет исполняемый код.",
            ),
        )

        self.assertEqual(state["status"], "running")
        self.assertIn(target, state["stages"]["code"]["capabilities"])
        self.assertEqual(state["stages"]["code"]["status"], "pending")

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
        state = self.new_state(self.root, "manual", None, False)
        MODULE.set_next(state, "Проверить входы этапа repository.")
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        _, restored = MODULE.load_state(self.root)
        self.assertEqual(
            restored["next_action"],
            "Проверить входы этапа repository.",
        )

    def test_invalid_transition_is_rejected(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["status"] = "complete"
        with self.assertRaisesRegex(MODULE.ReviewError, "недопустимый переход"):
            MODULE.transition(state, "running", "Повторить.")

    def test_terminal_state_rejects_mutating_functions(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["status"] = "complete"
        finding = argparse.Namespace(
            id="late-finding",
            stage="repository",
            summary="Поздняя проблема.",
            blocking=True,
            evidence=["Проблема найдена после завершения."],
            group=None,
            allowed_path=["tracked.txt"],
            verification="test",
        )

        with self.assertRaisesRegex(MODULE.ReviewError, "через restart"):
            MODULE.record_finding(state, finding)
        with self.assertRaisesRegex(MODULE.ReviewError, "через restart"):
            MODULE.refresh(state, self.root)

    def test_restart_archives_terminal_state_and_starts_new_cycle(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["status"] = "complete"
        path = MODULE.state_path(self.root)
        MODULE.atomic_write(path, state)

        restarted, archive = MODULE.restart_review(
            self.root,
            path,
            state,
            "manual",
            None,
            False,
        )

        self.assertTrue(archive.is_file())
        self.assertEqual(MODULE.load_json(archive)["status"], "complete")
        self.assertEqual(restarted["status"], "running")
        self.assertEqual(restarted["previous_review"]["archive"], str(archive))

    def test_restart_discards_incomplete_state_only_when_requested(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        path = MODULE.state_path(self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "только после"):
            MODULE.restart_review(self.root, path, state, "manual", None, False)

        restarted, archive = MODULE.restart_review(
            self.root,
            path,
            state,
            "manual",
            None,
            False,
            discard_incomplete=True,
        )

        archived = MODULE.load_json(archive)
        self.assertIn("discarded_at", archived)
        self.assertEqual(restarted["status"], "running")
        self.assertTrue(restarted["history"][-1]["discarded_incomplete"])

    def test_terminal_assertion_rejects_incomplete_review(self) -> None:
        state = self.new_state(self.root, "manual", None, False)

        with self.assertRaisesRegex(MODULE.ReviewError, "не завершена"):
            MODULE.require_terminal_state(state)

        state["status"] = "complete"
        MODULE.require_terminal_state(state)

    def test_external_change_interrupts_state(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("tracked.txt", "outside\n")
        MODULE.refresh(state, self.root)
        self.assertEqual(state["status"], "interrupted")
        self.assertIn("tracked.txt", state["history"][-1]["paths"])

    def test_approved_change_does_not_count_as_external(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
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
        self.prepare_decision(state)
        MODULE.record_decision(state, decision)
        self.write("tracked.txt", "approved\n")
        MODULE.refresh(state, self.root)
        self.assertNotEqual(state["status"], "interrupted")

    def test_check_before_change_cannot_accept_pending_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_verified_finding(state)
        self.write("tracked.txt", "verified\n")
        MODULE.refresh(state, self.root)
        self.assertEqual(state["status"], "interrupted")

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "нет проверки принимаемого снимка",
        ):
            self.accept_snapshot(state, ["finding-1"])

    def test_check_after_change_can_accept_pending_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)
        self.assertEqual(state["status"], "interrupted")

        self.accept_snapshot(state, ["finding-1"])

        self.assertEqual(state["status"], "running")
        self.assertIsNone(state["pending_snapshot"])
        self.assertEqual(
            state["snapshot"],
            MODULE.repository_snapshot(self.root),
        )

    def test_accepted_snapshot_preserves_independent_completed_stage(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["stages"]["assurance"]["status"] = "complete"
        state["stages"]["assurance"]["input_snapshot"] = state["snapshot"]["id"]
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        _, restored = MODULE.load_state(self.root)

        self.accept_snapshot(restored, ["finding-1"])

        self.assertIsNone(restored["current_stage"])
        self.assertEqual(restored["stages"]["repository"]["status"], "pending")
        self.assertEqual(restored["stages"]["assurance"]["status"], "complete")

    def test_accepted_snapshot_invalidates_active_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="stale-check",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Проверка прежнего снимка.",
                action="Проверить прежний снимок.",
                priority_rationale=(
                    "Проверка нужна до использования прежнего снимка."
                ),
                knowledge_phase=None,
                subject=[],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        previous_input = state["applications"]["stale-check"]["input_snapshot"]
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)
        accepted_snapshot = state["pending_snapshot"]["id"]

        self.accept_snapshot(
            state,
            external_paths=["outside.txt"],
            external_reason="Пользователь подтвердил новое входное состояние.",
        )

        application = state["applications"]["stale-check"]
        self.assertIsNone(state["active_application"])
        self.assertEqual(application["status"], "invalidated")
        self.assertEqual(application["input_snapshot"], previous_input)
        self.assertEqual(
            application["invalidated_snapshot"],
            accepted_snapshot,
        )
        self.assertEqual(
            application["invalidation_reason"],
            "accepted_snapshot_changed",
        )
        self.assertEqual(
            state["history"][-2]["invalidated_application"],
            "stale-check",
        )

        MODULE.start_application(
            state,
            argparse.Namespace(
                id="current-check",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Проверка принятого снимка.",
                action="Проверить принятый снимок.",
                priority_rationale=(
                    "Проверка подтверждает продолжение на принятом снимке."
                ),
                knowledge_phase=None,
                subject=[],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        self.assertEqual(state["active_application"], "current-check")

    def test_refresh_recovers_stale_active_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="stale-check",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Проверка прежнего снимка.",
                action="Проверить прежний снимок.",
                priority_rationale=(
                    "Проверка нужна до использования прежнего снимка."
                ),
                knowledge_phase=None,
                subject=[],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        previous_input = state["applications"]["stale-check"]["input_snapshot"]
        self.write("outside.txt", "accepted by an older controller\n")
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        MODULE.refresh(state, self.root)

        application = state["applications"]["stale-check"]
        self.assertIsNone(state["active_application"])
        self.assertEqual(application["status"], "invalidated")
        self.assertEqual(application["input_snapshot"], previous_input)
        self.assertEqual(
            application["invalidated_snapshot"],
            state["snapshot"]["id"],
        )
        self.assertEqual(
            state["history"][-2]["event"],
            "active_application_invalidated",
        )
        self.assertEqual(state["history"][-1]["event"], "refreshed")

    def test_accepted_snapshot_invalidates_older_capability_application(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)
        self.accept_snapshot(state, ["finding-1"])

        MODULE.set_stage(state, "repository", "running")
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанного применения",
        ):
            MODULE.set_stage(state, "repository", "complete")

    def test_pending_snapshot_rejects_unapproved_path(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.write("outside.txt", "outside\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "неразрешённые пути"):
            self.accept_snapshot(state, ["finding-1"])

    def test_pending_snapshot_rejects_later_change(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)
        self.write("tracked.txt", "changed later\n")

        with self.assertRaisesRegex(MODULE.ReviewError, "изменилась"):
            self.accept_snapshot(state, ["finding-1"])

    def test_confirmed_external_paths_can_accept_pending_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        previous_snapshot = state["snapshot"]["id"]
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)
        accepted_snapshot = state["pending_snapshot"]["id"]

        self.accept_snapshot(
            state,
            external_paths=["outside.txt"],
            external_reason="Пользователь подтвердил новое входное состояние.",
        )

        self.assertEqual(state["status"], "running")
        self.assertEqual(
            state["history"][-2]["confirmed_external_paths"],
            ["outside.txt"],
        )
        self.assertEqual(
            state["history"][-2]["previous_snapshot"],
            previous_snapshot,
        )
        self.assertEqual(
            state["history"][-2]["accepted_snapshot"],
            accepted_snapshot,
        )

    def test_changed_concept_capability_reopens_only_concept_barrier(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.assertEqual(state["concept_review"]["status"], "checked")
        self.assertEqual(state["knowledge_review"]["status"], "checked")
        self.write(
            ".agents/skills/ait-docs-concept/SKILL.md",
            "---\n"
            "name: ait-docs-concept\n"
            "description: Проверяет краткий замысел проекта.\n"
            "---\n",
        )
        MODULE.refresh(state, self.root)

        self.accept_snapshot(
            state,
            external_paths=[
                ".agents/skills/ait-docs-concept/SKILL.md",
            ],
            external_reason="Пользователь подтвердил изменение навыка.",
            reopen_stages=["requirements"],
        )

        self.assertEqual(state["status"], "running")
        self.assertEqual(state["concept_review"]["status"], "located")
        self.assertIsNone(state["concept_review"]["application"])
        self.assertIsNone(state["concept_review"]["outcome"])
        self.assertEqual(state["knowledge_review"]["status"], "checked")
        self.assertTrue(MODULE.knowledge_review_is_proven(state))
        self.assertEqual(
            state["history"][-1]["invalidated_mandatory_reviews"],
            ["concept"],
        )

    def test_changed_knowledge_content_reopens_corpus_barrier(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write(
            "knowledge/data/test/statements.yml",
            "- statement: updated evidence\n",
        )
        MODULE.refresh(state, self.root)

        self.accept_snapshot(
            state,
            external_paths=["knowledge/data/test/statements.yml"],
            external_reason="Пользователь подтвердил изменение корпуса.",
            reopen_stages=["repository"],
        )

        knowledge = state["knowledge_review"]
        self.assertEqual(knowledge["status"], "located")
        self.assertIsNone(knowledge["technical_application"])
        self.assertIsNone(knowledge["semantic_application"])
        self.assertFalse(MODULE.knowledge_review_is_proven(state))
        self.assertIn(
            "knowledge_review_invalidated",
            [entry["event"] for entry in state["history"]],
        )

    def test_content_pattern_makes_check_mandatory(self) -> None:
        inventory = {
            "capabilities": [
                {
                    "id": "skill-docs",
                    "classification": {
                        "status": "classified",
                        "participation": "check",
                        "stage": "assurance",
                        "applicability": "model",
                        "activation_patterns": ["docs/**/*.md"],
                    },
                    "input_hash": "hash",
                    "origin": "core",
                },
            ],
        }
        snapshot = {"files": {"docs/guide/start.md": "hash"}}

        decisions = MODULE.initial_capability_decisions(inventory, snapshot)

        self.assertTrue(decisions["skill-docs"]["applicable"])

    def test_required_subject_patterns_cover_full_discovered_class(self) -> None:
        decision = {"required_subject_patterns": ["docs/**/*.md"]}
        snapshot = {
            "files": {
                "docs/guide/first.md": "first",
                "docs/guide/second.md": "second",
                "README.md": "readme",
            },
        }

        required = MODULE.required_subjects_for_decision(decision, snapshot)

        self.assertEqual(
            required,
            {"docs/guide/first.md", "docs/guide/second.md"},
        )

    def test_confirmed_external_paths_require_reason(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "нужна причина"):
            self.accept_snapshot(
                state,
                external_paths=["outside.txt"],
            )

    def test_accepted_snapshot_requires_impacted_stage_and_rationale(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "затронутую область"):
            MODULE.accept_pending_snapshot(
                state,
                self.root,
                external_paths=["outside.txt"],
                external_reason="Пользователь подтвердил вход.",
            )
        with self.assertRaisesRegex(MODULE.ReviewError, "обоснование влияния"):
            MODULE.accept_pending_snapshot(
                state,
                self.root,
                external_paths=["outside.txt"],
                external_reason="Пользователь подтвердил вход.",
                reopen_stages=["repository"],
            )

    def test_confirmed_external_paths_reject_whitespace_reason(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "нужна причина"):
            self.accept_snapshot(
                state,
                external_paths=["outside.txt"],
                external_reason="   ",
            )

    def test_external_reason_requires_external_path(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)

        with self.assertRaisesRegex(MODULE.ReviewError, "только с внешним путём"):
            self.accept_snapshot(
                state,
                ["finding-1"],
                external_reason="Лишняя причина.",
            )

    def test_finding_and_external_path_can_share_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.record_approved_finding(state)
        self.write("tracked.txt", "verified\n")
        self.write("outside.txt", "confirmed input\n")
        self.record_passed_check(state)
        MODULE.refresh(state, self.root)

        self.accept_snapshot(
            state,
            ["finding-1"],
            ["outside.txt"],
            "Пользователь подтвердил дополнительный вход.",
        )

        event = state["history"][-2]
        self.assertEqual(event["findings"], ["finding-1"])
        self.assertEqual(event["confirmed_external_paths"], ["outside.txt"])

    def test_confirmed_external_path_must_be_changed(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)
        before = json.loads(json.dumps(state))

        with self.assertRaisesRegex(MODULE.ReviewError, "отсутствуют"):
            self.accept_snapshot(
                state,
                external_paths=["tracked.txt"],
                external_reason="Указан неверный путь.",
            )

        self.assertEqual(state, before)

    def test_pending_snapshot_rejects_unconfirmed_external_path(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.write("confirmed.txt", "confirmed input\n")
        self.write("unconfirmed.txt", "unconfirmed input\n")
        MODULE.refresh(state, self.root)
        before = json.loads(json.dumps(state))

        with self.assertRaisesRegex(MODULE.ReviewError, "неразрешённые пути"):
            self.accept_snapshot(
                state,
                external_paths=["confirmed.txt"],
                external_reason=(
                    "Пользователь подтвердил только один входной файл."
                ),
            )

        self.assertEqual(state, before)

    def test_accept_external_snapshot_cli_persists_audit(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        previous_snapshot = state["snapshot"]["id"]
        self.write("outside.txt", "confirmed input\n")
        MODULE.refresh(state, self.root)
        accepted_snapshot = state["pending_snapshot"]["id"]
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        arguments = [
            str(SCRIPT),
            "accept-snapshot",
            "--repo",
            str(self.root),
            "--external-path",
            "outside.txt",
            "--external-reason",
            "  Пользователь подтвердил вход.  ",
            "--reopen-stage",
            "repository",
            "--impact-rationale",
            "Изменение относится к проверке репозитория.",
        ]

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(sys, "stdout", io.StringIO()),
        ):
            MODULE.main()

        _, restored = MODULE.load_state(self.root)
        event = restored["history"][-2]
        self.assertEqual(event["external_reason"], "Пользователь подтвердил вход.")
        self.assertEqual(event["previous_snapshot"], previous_snapshot)
        self.assertEqual(event["accepted_snapshot"], accepted_snapshot)

    def record_approved_finding(self, state: dict[str, object]) -> None:
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Исправить файл",
                blocking=False,
                evidence=["tracked.txt"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="test",
            ),
        )
        self.prepare_decision(state)
        MODULE.record_decision(
            state,
            argparse.Namespace(
                finding="finding-1",
                decision="fix",
                reason=None,
                revisit_condition=None,
            ),
        )

    def record_passed_check(self, state: dict[str, object]) -> None:
        self.apply(
            state,
            identifier="check-1",
            finding="finding-1",
            outcome="passed",
        )

    def apply(
        self,
        state: dict[str, object],
        *,
        identifier: str,
        capability: str | None = None,
        finding: str | None = None,
        stage: str = "repository",
        method: str = "validation",
        outcome: str = "passed",
        decision: str | None = None,
        artifacts: list[str] | None = None,
        command: str | None = None,
    ) -> None:
        semantic = method == "review" or (
            capability is not None
            and state["capability_decisions"][capability].get(
                "semantic_required",
                False,
            )
        )
        MODULE.start_application(
            state,
            argparse.Namespace(
                id=identifier,
                stage=stage,
                capability=capability,
                finding=finding,
                method=method,
                surface=f"Поверхность {identifier}",
                action=f"Применить {identifier}.",
                priority_rationale=(
                    "Эта работа даёт наибольшую ожидаемую пользу в тестовом "
                    "состоянии."
                ),
                subject=["tracked.txt"] if semantic else [],
            ),
            self.root,
        )
        if semantic:
            MODULE.record_observation(
                state,
                argparse.Namespace(
                    application=identifier,
                    artifact="tracked.txt",
                    start_line=1,
                    end_line=1,
                    criterion_id="custom",
                    criterion="Соответствие предметному критерию.",
                    result="supports",
                    note=f"Наблюдение для {identifier}.",
                ),
                self.root,
            )
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application=identifier,
                outcome=outcome,
                decision=decision,
                evidence=[f"Наблюдаемый результат {identifier}"],
                artifact=["tracked.txt"] if artifacts is None else artifacts,
                coverage=f"Охват {identifier}",
                claim=[f"Проверяемый вывод {identifier}"],
                claim_support=["observation-001"] if semantic else [],
                challenge=(
                    f"Предположение для опровержения {identifier}."
                    if semantic
                    else None
                ),
                challenge_outcome="refuted" if semantic else None,
                challenge_support=["observation-001"] if semantic else [],
                command=command,
            ),
            self.root,
        )

    def record_verified_finding(self, state: dict[str, object]) -> None:
        self.record_approved_finding(state)
        self.record_passed_check(state)

    def test_passed_check_requires_fix_decision(self) -> None:
        for blocking in (False, True):
            with self.subTest(blocking=blocking):
                state = self.new_state(self.root, "manual", None, False)
                MODULE.record_finding(
                    state,
                    argparse.Namespace(
                        id="finding-1",
                        stage="repository",
                        summary="Исправить файл",
                        blocking=blocking,
                        evidence=["tracked.txt"],
                        group=None,
                        allowed_path=["tracked.txt"],
                        verification="test",
                    ),
                )

                with self.assertRaisesRegex(
                    MODULE.ReviewError,
                    "требует решения fix",
                ):
                    self.record_passed_check(state)

                self.assertEqual(state["findings"]["finding-1"]["status"], "open")

    def test_unchanged_stage_is_reused_and_changed_capability_reopens_its_stage(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
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
                evidence=["Свидетельство"],
                group=None,
                allowed_path=[".agents/skills/core-check/SKILL.md"],
                verification="inventory",
            ),
        )
        self.prepare_decision(state, "finding-core-change")
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
        state = self.new_state(self.root, "manual", None, False)
        MODULE.set_stage(state, "repository", "running")
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Блокер",
            blocking=True,
            evidence=["Свидетельство"],
            group=None,
            allowed_path=[],
            verification=None,
        )
        MODULE.record_finding(state, finding)
        with self.assertRaisesRegex(MODULE.ReviewError, "нерешённые проблемы"):
            MODULE.set_stage(state, "repository", "complete")

    def test_one_decision_applies_to_whole_group(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        for identifier in ("finding-1", "finding-2"):
            MODULE.record_finding(
                state,
                argparse.Namespace(
                    id=identifier,
                    stage="repository",
                    summary=identifier,
                    blocking=False,
                    evidence=["Свидетельство"],
                    group="group-1",
                    allowed_path=[f"{identifier}.txt"],
                    verification="test",
                ),
            )
        self.prepare_decision(
            state,
            problems=[
                "Первая часть группы работает неверно.",
                "Вторая часть группы работает неверно.",
            ],
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

    def test_surface_checks_are_required_before_decision(self) -> None:
        self.write("README.md", "# Project\n")
        state = self.new_state(self.root, "manual", None, False)
        state["capability_decisions"]["skill:core-check"][
            "decision_paths"
        ] = ["README.md"]
        finding = argparse.Namespace(
            id="finding-readme",
            stage="repository",
            summary="Исправить README",
            blocking=True,
            evidence=["README.md"],
            group=None,
            allowed_path=["README.md"],
            verification="test",
        )
        MODULE.record_finding(state, finding)

        self.assertEqual(state["status"], "running")
        self.assertEqual(
            state["findings"]["finding-readme"][
                "required_capability_paths"
            ],
            {"skill:core-check": ["README.md"]},
        )
        decision = argparse.Namespace(
            finding="finding-readme",
            decision="fix",
            reason=None,
            revisit_condition=None,
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "группа не готова"):
            self.prepare_decision(state, "finding-readme")
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "prepare-decision",
        ):
            MODULE.transition(
                state,
                "waiting_decision",
                "Получить решение.",
            )

        self.apply(
            state,
            identifier="check-readme",
            capability="skill:core-check",
            artifacts=["README.md"],
        )

        self.assertEqual(state["status"], "running")
        brief = self.prepare_decision(state, "finding-readme")
        self.assertEqual(state["status"], "waiting_decision")
        self.assertIn("Полная проверка тестового проекта", brief["message"])
        self.assertIn("Нужно решение:", brief["message"])
        self.assertIn("Подробности проверки", brief["message"])
        self.assertNotIn("Граница изменения:", brief["message"])
        self.assertNotIn("Проверка после изменения:", brief["message"])
        MODULE.record_decision(state, decision)
        self.assertEqual(
            state["findings"]["finding-readme"]["status"],
            "approved",
        )

    def test_decision_message_normalizes_terminal_punctuation(self) -> None:
        message = MODULE.render_decision_message(
            {
                "review_context": "Полная проверка тестового проекта.",
                "checked_subject": "Пользовательский маршрут.",
                "relation": "Он влияет на остальные проверки!",
                "problems": ["Найдена повторяющаяся ошибка."],
                "impact": "Читатель может неверно понять сообщение?",
                "proposed_change": "Нормализовать завершение предложений.",
                "allowed_paths": ["README.md"],
                "verifications": ["Проверить итоговое сообщение."],
                "decision_question": "Одобряете исправление?",
            }
        )

        self.assertIn(
            "Полная проверка тестового проекта.\n\n"
            "Нужно решение: Одобряете исправление?",
            message,
        )
        self.assertIn(
            "Почему это важно: Читатель может неверно понять сообщение?",
            message,
        )
        self.assertNotIn("Пользовательский маршрут", message)
        self.assertNotIn("Он влияет на остальные проверки", message)
        self.assertNotIn("README.md", message)
        self.assertNotIn("Проверить итоговое сообщение", message)
        self.assertNotIn("..", message)
        self.assertNotIn("!.", message)
        self.assertNotIn("?.", message)

    def test_surface_check_must_cover_finding_path(self) -> None:
        self.write("README.md", "# Project\n")
        state = self.new_state(self.root, "manual", None, False)
        state["capability_decisions"]["skill:core-check"][
            "decision_paths"
        ] = ["README.md"]
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-readme",
                stage="repository",
                summary="Исправить README",
                blocking=True,
                evidence=["README.md"],
                group=None,
                allowed_path=["README.md"],
                verification="test",
            ),
        )
        self.apply(
            state,
            identifier="check-other-file",
            capability="skill:core-check",
            artifacts=["tracked.txt"],
        )

        with self.assertRaisesRegex(MODULE.ReviewError, "группа не готова"):
            self.prepare_decision(state, "finding-readme")

    def test_decision_refreshes_surface_requirements(self) -> None:
        self.write("README.md", "# Project\n")
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-readme",
                stage="repository",
                summary="Исправить README",
                blocking=False,
                evidence=["README.md"],
                group=None,
                allowed_path=["README.md"],
                verification="test",
            ),
        )
        self.assertEqual(
            state["findings"]["finding-readme"][
                "required_capability_paths"
            ],
            {},
        )
        state["capability_decisions"]["skill:core-check"][
            "decision_paths"
        ] = ["README.md"]

        with self.assertRaisesRegex(MODULE.ReviewError, "группа не готова"):
            self.prepare_decision(state, "finding-readme")
        self.assertEqual(
            state["findings"]["finding-readme"][
                "required_capability_paths"
            ],
            {"skill:core-check": ["README.md"]},
        )

    def test_surface_finding_requires_classified_capability(self) -> None:
        self.write("README.md", "# Project\n")
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["decision_paths"] = ["README.md"]
        decision["status"] = "unknown"
        decision["applicable"] = None

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "не классифицирована связанная проверка",
        ):
            MODULE.record_finding(
                state,
                argparse.Namespace(
                    id="finding-readme",
                    stage="repository",
                    summary="Исправить README",
                    blocking=True,
                    evidence=["README.md"],
                    group=None,
                    allowed_path=["README.md"],
                    verification="test",
                ),
            )

    def test_fix_requires_boundary_and_verification(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Нет границы",
                blocking=False,
                evidence=["Свидетельство"],
                group=None,
                allowed_path=[],
                verification=None,
            ),
        )
        self.prepare_decision(state)
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

    def test_finding_rejects_empty_evidence(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(MODULE.ReviewError, "свидетельство"):
            MODULE.record_finding(
                state,
                argparse.Namespace(
                    id="finding-empty-evidence",
                    stage="repository",
                    summary="Есть проблема.",
                    blocking=False,
                    evidence=["   "],
                    group=None,
                    allowed_path=["tracked.txt"],
                    verification="test",
                ),
            )

    def test_blocking_finding_cannot_be_accepted(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Блокер",
            blocking=True,
            evidence=["Свидетельство"],
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
        self.prepare_decision(state)
        with self.assertRaisesRegex(MODULE.ReviewError, "блокирующую"):
            MODULE.record_decision(state, decision)

    def test_accepted_risk_requires_reason_and_revisit_condition(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        finding = argparse.Namespace(
            id="finding-1",
            stage="repository",
            summary="Риск",
            blocking=False,
            evidence=["Свидетельство"],
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
        self.prepare_decision(state)
        with self.assertRaisesRegex(MODULE.ReviewError, "причины"):
            MODULE.record_decision(state, decision)

    def test_accepted_risk_rejects_whitespace_basis(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Риск",
                blocking=False,
                evidence=["Наблюдаемый риск."],
                group=None,
                allowed_path=[],
                verification=None,
            ),
        )
        self.prepare_decision(state)
        with self.assertRaisesRegex(MODULE.ReviewError, "причины"):
            MODULE.record_decision(
                state,
                argparse.Namespace(
                    finding="finding-1",
                    decision="accept",
                    reason=" ",
                    revisit_condition=" ",
                ),
            )

    def test_waiting_decision_requires_self_contained_brief(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["status"] = "waiting_decision"
        state["next_action"] = "Получить решение."

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "самодостаточный запрос",
        ):
            MODULE.validate_state(state)

    def test_record_decision_requires_prepared_brief(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Исправить файл",
                blocking=False,
                evidence=["Свидетельство"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="test",
            ),
        )

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "самодостаточного запроса",
        ):
            MODULE.record_decision(
                state,
                argparse.Namespace(
                    finding="finding-1",
                    decision="fix",
                    reason=None,
                    revisit_condition=None,
                ),
            )

    def test_decision_brief_requires_current_live_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Исправить файл",
                blocking=False,
                evidence=["Свидетельство"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="test",
            ),
        )
        self.write("outside.txt", "new input\n")

        with self.assertRaisesRegex(MODULE.ReviewError, "выполните refresh"):
            self.prepare_decision(state)

    def test_external_change_clears_prepared_decision_brief(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-1",
                stage="repository",
                summary="Исправить файл",
                blocking=False,
                evidence=["Свидетельство"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="test",
            ),
        )
        self.prepare_decision(state)
        self.write("outside.txt", "new input\n")

        MODULE.refresh(state, self.root)

        self.assertEqual(state["status"], "interrupted")
        self.assertIsNone(state["decision_brief"])

    def test_completion_rejects_unclassified_capability(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        for stage in state["stages"].values():
            stage["status"] = "complete"
        with self.assertRaisesRegex(MODULE.ReviewError, "не классифицированы"):
            MODULE.validate_completion(state, "complete")

    def test_stage_requires_applicable_check_result(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.set_stage(state, "repository", "running")
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанного применения",
        ):
            MODULE.set_stage(state, "repository", "complete")
        with self.assertRaisesRegex(MODULE.ReviewError, "record-check"):
            MODULE.record_check(
                state,
                argparse.Namespace(),
            )
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        MODULE.set_stage(state, "repository", "complete")
        self.assertEqual(state["stages"]["repository"]["status"], "complete")

    def test_free_text_cannot_finish_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="check-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Ядро",
                action="Проверить ядро.",
                priority_rationale="Проверка устраняет основной риск.",
            ),
            self.root,
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "свободный текст"):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="check-core",
                    outcome="passed",
                    decision=None,
                    evidence=["Всё хорошо"],
                    artifact=[],
                    command=None,
                ),
                self.root,
            )

    def test_check_rejects_generic_command_without_subject_artifact(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="check-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Содержание проекта",
                action="Проверить содержание проекта.",
                priority_rationale="Проверка устраняет основной смысловой риск.",
            ),
            self.root,
        )

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "артефакт проверяемой поверхности",
        ):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="check-core",
                    outcome="passed",
                    decision=None,
                    evidence=["Формальная команда завершилась без ошибок."],
                    artifact=[],
                    coverage="Концепция, требования и решения.",
                    claim=["Содержание соответствует основаниям."],
                    command="git diff --cached --check",
                ),
                self.root,
            )

    def test_capability_contract_is_not_subject_artifact(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "контракт возможности не является предметом проверки",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="check-core",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="review",
                    surface="Содержание проекта",
                    action="Проверить содержание проекта.",
                    priority_rationale=(
                        "Проверка устраняет основной смысловой риск."
                    ),
                    subject=[".agents/skills/core-check/SKILL.md"],
                ),
                self.root,
            )

    def test_validation_in_requirements_does_not_require_semantic_trace(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Структурный договор требований",
                action="Проверить структурный договор требований.",
                priority_rationale=(
                    "Ошибка основания обесценит зависимые решения."
                ),
                subject=[],
            ),
            self.root,
        )
        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="requirements-core",
                outcome="passed",
                decision="accept",
                evidence=["Структурный валидатор завершился без ошибок."],
                artifact=["tracked.txt"],
                coverage="Структурный договор требований.",
                claim=["Структурный договор соблюдён."],
                claim_support=[],
                challenge=None,
                challenge_outcome=None,
                challenge_support=[],
                command="git diff --cached --check",
            ),
            self.root,
        )

    def test_semantic_review_rejects_self_attested_fields(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Концепция и требования",
                action="Проверить смысл концепции и требований.",
                priority_rationale=(
                    "Ошибка основания обесценит зависимые решения."
                ),
                subject=["tracked.txt"],
            ),
            self.root,
        )

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "требует наблюдений по предметным файлам",
        ):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="requirements-core",
                    outcome="passed",
                    decision="accept",
                    evidence=["Структурный валидатор завершился без ошибок."],
                    artifact=["tracked.txt"],
                    coverage="Концепция и все требования.",
                    claim=["Содержание согласовано."],
                    claim_support=[],
                    challenge=None,
                    challenge_outcome=None,
                    challenge_support=[],
                    command="git diff --cached --check",
                ),
                self.root,
            )

    def test_semantic_review_requires_observation_for_every_subject(self) -> None:
        self.write("second.txt", "second\n")
        run("git", "add", "second.txt", cwd=self.root)
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Два требования",
                action="Сопоставить два требования.",
                priority_rationale="Связь требований влияет на реализацию.",
                subject=["tracked.txt", "second.txt"],
            ),
            self.root,
        )
        MODULE.record_observation(
            state,
            argparse.Namespace(
                application="requirements-core",
                artifact="tracked.txt",
                start_line=1,
                end_line=1,
                criterion_id="custom",
                criterion="Наличие обязательства.",
                result="supports",
                note="Первое требование содержит обязательство.",
            ),
            self.root,
        )

        with self.assertRaisesRegex(MODULE.ReviewError, "second.txt"):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="requirements-core",
                    outcome="passed",
                    decision="accept",
                    evidence=["Проверены оба требования."],
                    artifact=["tracked.txt", "second.txt"],
                    coverage="Два требования.",
                    claim=["Требования согласованы."],
                    claim_support=["observation-001"],
                    challenge="Второе требование противоречит первому.",
                    challenge_outcome="refuted",
                    challenge_support=["observation-001"],
                    command="python3 -c 'pass'",
                ),
                self.root,
            )

    def test_validate_rejects_observation_without_controller_receipt(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Требования",
                action="Проверить требования.",
                priority_rationale="Требования определяют поведение продукта.",
                subject=["tracked.txt"],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        observation = MODULE.record_observation(
            state,
            argparse.Namespace(
                application="requirements-core",
                artifact="tracked.txt",
                start_line=1,
                end_line=1,
                criterion_id="custom",
                criterion="Наличие обязательства.",
                result="supports",
                note="Требование содержит обязательство.",
            ),
            self.root,
        )
        state["history"] = [
            event
            for event in state["history"]
            if event.get("observation") != observation["id"]
        ]

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "не записано через record-observation",
        ):
            MODULE.validate_state(state)

    def test_full_requirements_review_rejects_handpicked_subjects(self) -> None:
        self.write(
            "docs/requirements.md",
            "# Требования\n\n- [БТ-1](requirements/business/bt-1.md)\n",
        )
        self.write(
            "docs/requirements/business/bt-1.md",
            "# БТ-1\n\nПродукт снижает риск.\n",
        )
        run("git", "add", "docs", cwd=self.root)
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        decision["subject_discovery_required"] = True

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "требует обнаружить предметную область",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="requirements-core",
                    stage="requirements",
                    capability="skill:core-check",
                    finding=None,
                    method="review",
                    surface="Все требования",
                    action="Проверить все требования.",
                    priority_rationale=(
                        "Ошибки требований обесценят зависимые решения."
                    ),
                    subject=["docs/requirements.md"],
                    subject_index=[],
                    subject_pattern=[],
                ),
                self.root,
            )

    def test_requirements_revalidation_waits_for_ontology_predecessors(self) -> None:
        for name in ("ait-req-revalidation", "ait-req-validation", "ait-ux-design"):
            skill = f"---\nname: {name}\ndescription: Проверяет проект.\n---\n"
            self.write(f".agents/skills/{name}/SKILL.md", skill)
            self.write(f".claude/skills/{name}/SKILL.md", skill)
        classification = json.loads(self.classification.read_text(encoding="utf-8"))
        classification["capabilities"].extend(
            [
                {
                    "id": "skill-ait-req-revalidation",
                    "kind": "skill",
                    "path": ".apm/skills/ait-req-revalidation",
                    "purpose": "Полная проверка требований",
                    "participation": "check",
                    "stage": "requirements",
                    "applicability": "model",
                    "ontology_scope": {"node_kinds": ["requirements"]},
                },
                {
                    "id": "skill-ait-req-validation",
                    "kind": "skill",
                    "path": ".apm/skills/ait-req-validation",
                    "purpose": "Проверка требований",
                    "participation": "check",
                    "stage": "requirements",
                    "applicability": "model",
                },
                {
                    "id": "skill-ait-ux-design",
                    "kind": "skill",
                    "path": ".apm/skills/ait-ux-design",
                    "purpose": "Проверка пользовательской модели",
                    "participation": "check",
                    "stage": "design",
                    "applicability": "model",
                },
            ],
        )
        self.classification.write_text(json.dumps(classification), encoding="utf-8")
        self.write("docs/users/alex.md", "# Алекс\n")
        self.write("docs/scenarios/create.md", "# Создание\n")
        self.write("docs/specification.md", "# Требования\n")
        self.write(
            ".ai-dev-team/project-impact.json",
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "personas",
                            "title": "Модели пользователей",
                            "kind": "requirements",
                            "paths": ["docs/users/**"],
                            "checks": ["ait-ux-design"],
                            "review_stages": ["requirements"],
                        },
                        {
                            "id": "use-cases",
                            "title": "Варианты использования",
                            "kind": "requirements",
                            "paths": ["docs/scenarios/**"],
                            "checks": ["ait-req-validation"],
                            "review_stages": ["requirements"],
                        },
                        {
                            "id": "requirements",
                            "title": "Требования",
                            "kind": "requirements",
                            "paths": ["docs/specification.md"],
                            "checks": ["ait-req-validation"],
                            "review_stages": ["requirements"],
                        },
                    ],
                    "edges": [
                        {"from": "personas", "to": "use-cases"},
                        {"from": "use-cases", "to": "requirements"},
                    ],
                },
            ),
        )
        run("git", "add", "docs", ".ai-dev-team/project-impact.json", cwd=self.root)
        state = self.new_state(self.root, "manual", None, False)

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "(?=.*Модели пользователей)(?=.*Варианты использования)",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="requirements-revalidation",
                    stage="requirements",
                    capability="skill:ait-req-revalidation",
                    finding=None,
                    method="review",
                    surface="Полный набор требований.",
                    action="Проверить требования после их оснований.",
                    priority_rationale="Требования зависят от моделей и сценариев.",
                    subject=[],
                    subject_index=[],
                    subject_pattern=["docs/specification.md"],
                ),
                self.root,
            )

    def test_proven_knowledge_review_covers_ontology_prerequisite(self) -> None:
        self.write("knowledge/auxiliary.md", "# Дополнительный индекс\n")
        run("git", "add", "knowledge", cwd=self.root)
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        self.complete_knowledge_review(state)

        decision = {
            "ontology_scope": {
                "prerequisites": [
                    {
                        "title": "Корпус знаний",
                        "subjects": [
                            "knowledge/catalog.yml",
                            "knowledge/auxiliary.md",
                        ],
                        "checks": ["kc-validation"],
                    },
                ],
            },
        }

        self.assertEqual(
            MODULE.unverified_ontology_prerequisites(state, decision),
            [],
        )

    def test_knowledge_impact_audit_requires_changed_subjects_only(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["capability_inventory"]["capabilities"].append(
            {"id": "skill:kc-impact-audit", "name": "kc-impact-audit"},
        )
        state["capability_decisions"]["skill:kc-impact-audit"] = {
            "input_hash": "impact-audit-input",
            "participation": "check",
        }
        state["applications"]["knowledge-impact"] = {
            "capability": "skill:kc-impact-audit",
            "status": "complete",
            "outcome": "passed",
            "capability_input_hash": "impact-audit-input",
            "input_snapshot": state["snapshot"]["id"],
            "completed_snapshot": state["snapshot"]["id"],
            "evidence_fingerprint": "evidence",
            "coverage": "Изменённые утверждения.",
            "claims": ["Влияние проверено."],
            "subject_artifacts": ["tracked.txt"],
        }
        decision = {
            "ontology_scope": {
                "prerequisites": [
                    {
                        "title": "Корпус знаний",
                        "subjects": ["knowledge/whole-corpus.yml"],
                        "checks": ["kc-impact-audit"],
                    },
                ],
            },
        }

        self.assertEqual(
            MODULE.unverified_ontology_prerequisites(state, decision),
            [],
        )

    def test_proven_knowledge_review_closes_repository_capability(self) -> None:
        state = self.pending_concept_state()
        self.complete_concept_review(state)
        self.complete_knowledge_review(state)

        self.assertIn(
            state["knowledge_review"]["capability"],
            MODULE.successful_capability_applications(state, "repository"),
        )

    def test_subject_index_expands_linked_business_requirements(self) -> None:
        self.write(
            "docs/requirements.md",
            "# Требования\n\n"
            "- [БТ-1](requirements/business/bt-1.md)\n"
            "- [БТ-2](requirements/business/bt-2.md)\n",
        )
        self.write(
            "docs/requirements/business/bt-1.md",
            "# БТ-1\n\nПродукт снижает риск.\n",
        )
        self.write(
            "docs/requirements/business/bt-2.md",
            "# БТ-2\n\nЭффект требует порога.\n",
        )
        run("git", "add", "docs", cwd=self.root)
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        decision["subject_discovery_required"] = True
        decision["review_criteria"] = [
            {
                "id": "requirement-quality",
                "description": "Качество отдельного требования.",
                "coverage": "each_subject",
            },
        ]
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Все требования",
                action="Проверить все требования.",
                priority_rationale=(
                    "Ошибки требований обесценят зависимые решения."
                ),
                subject=[],
                subject_index=["docs/requirements.md"],
                subject_pattern=[],
            ),
            self.root,
        )
        application = state["applications"]["requirements-core"]
        self.assertEqual(
            {
                item["reference"]
                for item in application["subject_scope"]
            },
            {
                "docs/requirements.md",
                "docs/requirements/business/bt-1.md",
                "docs/requirements/business/bt-2.md",
            },
        )
        MODULE.record_observation(
            state,
            argparse.Namespace(
                application="requirements-core",
                artifact="docs/requirements.md",
                start_line=1,
                end_line=3,
                criterion_id="requirement-quality",
                criterion=None,
                result="supports",
                note="Индекс перечисляет два бизнес-требования.",
            ),
            self.root,
        )
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "bt-1.md",
        ):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="requirements-core",
                    outcome="passed",
                    decision="accept",
                    evidence=["Проверен индекс требований."],
                    artifact=["docs/requirements.md"],
                    coverage="Индекс и связанные бизнес-требования.",
                    claim=["Индекс содержит ссылки на требования."],
                    claim_support=["observation-001"],
                    challenge="Связанный файл мог быть пропущен.",
                    challenge_outcome="refuted",
                    challenge_support=["observation-001"],
                    command=None,
                ),
                self.root,
        )

    def test_subject_scope_includes_ontology_file_ignored_by_git(self) -> None:
        self.write(".gitignore", "ignored.md\n")
        self.write("docs/ignored.md", "# Представление\n")
        snapshot = MODULE.repository_snapshot(self.root)

        self.assertNotIn("docs/ignored.md", snapshot["files"])
        scope, _ = MODULE.resolve_subject_scope(
            self.root,
            snapshot,
            [],
            [],
            ["docs/ignored.md"],
        )

        self.assertEqual(
            scope,
            [{
                "reference": "docs/ignored.md",
                "sha256": MODULE.file_hash(self.root / "docs/ignored.md"),
            }],
        )

    def test_refresh_recomputes_ontology_scope_after_graph_change(self) -> None:
        classification = json.loads(self.classification.read_text(encoding="utf-8"))
        classification["capabilities"][0]["ontology_scope"] = {
            "node_kinds": ["knowledge"],
        }
        self.classification.write_text(json.dumps(classification), encoding="utf-8")
        self.write(
            ".ai-dev-team/project-impact.json",
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "knowledge",
                            "title": "Корпус знаний",
                            "kind": "knowledge",
                            "paths": ["knowledge/**"],
                            "checks": ["core-check"],
                            "review_stages": ["repository"],
                        },
                    ],
                    "edges": [],
                },
            ),
        )
        state = self.new_state(self.root, "manual", None, False)
        previous_scope = state["capability_decisions"]["skill:core-check"][
            "ontology_scope"
        ]
        previous_hash = state["capability_decisions"]["skill:core-check"][
            "input_hash"
        ]
        previous_inventory = state["capability_inventory"]["fingerprint"]

        self.write(
            ".ai-dev-team/project-impact.json",
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "knowledge",
                            "title": "Корпус знаний",
                            "kind": "knowledge",
                            "paths": ["knowledge/data/**"],
                            "checks": ["core-check"],
                            "review_stages": ["repository"],
                        },
                    ],
                    "edges": [],
                },
            ),
        )
        state["snapshot"] = MODULE.repository_snapshot(self.root)

        MODULE.refresh(state, self.root)

        decision = state["capability_decisions"]["skill:core-check"]
        self.assertEqual(previous_inventory, state["capability_inventory"]["fingerprint"])
        self.assertNotEqual(previous_hash, decision["input_hash"])
        self.assertNotEqual(previous_scope, decision["ontology_scope"])
        self.assertEqual(
            ["knowledge/data/test/source.yml", "knowledge/data/test/statements.yml"],
            decision["ontology_scope"]["targets"][0]["subjects"],
        )

    def test_failed_semantic_application_requires_linked_finding(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-failed",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Требование",
                action="Проверить требование.",
                priority_rationale="Ошибка требования влияет на реализацию.",
                subject=["tracked.txt"],
            ),
            self.root,
        )
        MODULE.record_observation(
            state,
            argparse.Namespace(
                application="requirements-failed",
                artifact="tracked.txt",
                start_line=1,
                end_line=1,
                criterion_id="custom",
                criterion="Непротиворечивость требования.",
                result="problem",
                note="Найдено противоречие.",
            ),
            self.root,
        )
        finish = argparse.Namespace(
            application="requirements-failed",
            outcome="failed",
            decision="revise",
            evidence=["Проверка выявила противоречие."],
            artifact=["tracked.txt"],
            coverage="Весь файл требования.",
            claim=["Требование содержит противоречие."],
            claim_support=["observation-001"],
            challenge="Возможно, противоречие разрешено соседним положением.",
            challenge_outcome="confirmed",
            challenge_support=["observation-001"],
            command=None,
        )

        with self.assertRaisesRegex(MODULE.ReviewError, "связанных находок"):
            MODULE.finish_application(state, finish, self.root)

        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-linked-problem",
                stage="requirements",
                summary="Устранить противоречие требования.",
                blocking=True,
                evidence=["Наблюдение observation-001."],
                observation=["observation-001"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="Повторить смысловую проверку.",
            ),
        )
        MODULE.finish_application(state, finish, self.root)

        self.assertEqual(
            state["findings"]["finding-linked-problem"]["observation_ids"],
            ["observation-001"],
        )
        self.assertEqual(
            state["applications"]["requirements-failed"]["outcome"],
            "failed",
        )

    def test_semantic_problem_cannot_be_recorded_as_passed(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "requirements"
        decision["review_criteria"] = [
            {
                "id": "traceability",
                "description": "Направление связей между требованиями.",
                "coverage": "each_subject",
            },
        ]
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="requirements-core",
                stage="requirements",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Трассировка требования",
                action="Проверить направление связи.",
                priority_rationale=(
                    "Циклическое основание обесценит анализ влияния."
                ),
                subject=["tracked.txt"],
                subject_index=[],
                subject_pattern=[],
            ),
            self.root,
        )
        MODULE.record_observation(
            state,
            argparse.Namespace(
                application="requirements-core",
                artifact="tracked.txt",
                start_line=1,
                end_line=1,
                criterion_id="traceability",
                criterion=None,
                result="problem",
                note="Файл содержит обратную связь на производное требование.",
            ),
            self.root,
        )
        MODULE.record_finding(
            state,
            argparse.Namespace(
                id="finding-semantic-problem",
                stage="requirements",
                summary="Исправить обратную связь требования.",
                blocking=True,
                evidence=["Наблюдение observation-001."],
                observation=["observation-001"],
                group=None,
                allowed_path=["tracked.txt"],
                verification="Повторить смысловую проверку.",
            ),
        )

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "найденная смысловая проблема",
        ):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="requirements-core",
                    outcome="passed",
                    decision="accept",
                    evidence=["Проверено направление связи."],
                    artifact=["tracked.txt"],
                    coverage="Связи требования.",
                    claim=["Связь направлена правильно."],
                    claim_support=["observation-001"],
                    challenge="Связь могла быть обратной.",
                    challenge_outcome="refuted",
                    challenge_support=["observation-001"],
                    command=None,
                ),
                self.root,
            )

    def test_semantic_review_records_observations_and_falsification(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "design"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="design-core",
                stage="design",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Проектное решение",
                action="Проверить основание и следствие решения.",
                priority_rationale="Ошибка решения вызовет дорогую переделку.",
                subject=["tracked.txt"],
            ),
            self.root,
        )
        observation = MODULE.record_observation(
            state,
            argparse.Namespace(
                application="design-core",
                artifact="tracked.txt",
                start_line=1,
                end_line=1,
                criterion_id="custom",
                criterion="Связь основания и решения.",
                result="supports",
                note="Строка закрепляет проверяемое основание.",
            ),
            self.root,
        )
        self.assertEqual(observation["excerpt"], "before")

        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "требует попытку опровержения",
        ):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="design-core",
                    outcome="passed",
                    decision="accept",
                    evidence=["Основание сопоставлено с решением."],
                    artifact=["tracked.txt"],
                    coverage="Основание и решение.",
                    claim=["Решение следует из указанного основания."],
                    claim_support=["observation-001"],
                    challenge=None,
                    challenge_outcome=None,
                    challenge_support=[],
                    command="git diff --cached --check",
                ),
                self.root,
            )

        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="design-core",
                outcome="passed",
                decision="accept",
                evidence=["Основание сопоставлено с решением."],
                artifact=["tracked.txt"],
                coverage="Основание и решение.",
                claim=["Решение следует из указанного основания."],
                claim_support=["observation-001"],
                challenge="Решение не следует из основания.",
                challenge_outcome="refuted",
                challenge_support=["observation-001"],
                command="git diff --cached --check",
            ),
            self.root,
        )

        application = state["applications"]["design-core"]
        self.assertEqual(application["challenge"]["outcome"], "refuted")
        self.assertEqual(
            application["claim_support"],
            ["observation-001"],
        )

    def test_semantic_review_records_binary_artifact_metadata(self) -> None:
        binary = self.root / "artifact.bin"
        binary.write_bytes(b"\x00\xff\x10")
        state = self.new_state(self.root, "manual", None, False)
        decision = state["capability_decisions"]["skill:core-check"]
        decision["stage"] = "design"
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="binary-design",
                stage="design",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Двоичный артефакт",
                action="Проверить метаданные двоичного артефакта.",
                priority_rationale="Двоичный артефакт входит в предметную область.",
                subject=["artifact.bin"],
            ),
            self.root,
        )
        observation = MODULE.record_observation(
            state,
            argparse.Namespace(
                application="binary-design",
                artifact="artifact.bin",
                start_line=1,
                end_line=1,
                criterion_id="custom",
                criterion="Метаданные двоичного артефакта.",
                result="supports",
                note="Размер и контрольная сумма позволяют идентифицировать артефакт.",
            ),
            self.root,
        )
        self.assertIn("Двоичный артефакт", observation["excerpt"])

    def test_changed_snapshot_allows_only_failed_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="check-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Ядро",
                action="Проверить ядро.",
                priority_rationale="Проверка устраняет основной риск.",
            ),
            self.root,
        )
        input_snapshot = state["applications"]["check-core"]["input_snapshot"]
        self.write("tracked.txt", "changed\n")

        MODULE.finish_application(
            state,
            argparse.Namespace(
                application="check-core",
                outcome="passed",
                decision=None,
                evidence=["Проверка завершилась."],
                artifact=["tracked.txt"],
                command=None,
            ),
            self.root,
        )
        application = state["applications"]["check-core"]
        self.assertEqual(application["status"], "complete")
        self.assertEqual(application["outcome"], "failed")
        self.assertNotEqual(application["completed_snapshot"], input_snapshot)
        self.assertIsNone(state["active_application"])
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(
            state["pending_snapshot"],
            MODULE.repository_snapshot(self.root),
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "состоянии running"):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="next-check",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Ядро",
                    action="Продолжить проверку.",
                    priority_rationale="Проверка устраняет основной риск.",
                ),
                self.root,
            )

    def test_finish_cli_persists_interrupted_after_snapshot_change(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="check-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="validation",
                surface="Ядро",
                action="Проверить ядро.",
                priority_rationale="Проверка устраняет основной риск.",
            ),
            self.root,
        )
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        self.write("tracked.txt", "changed\n")
        arguments = [
            str(SCRIPT),
            "finish-application",
            "--repo",
            str(self.root),
            "--application",
            "check-core",
            "--outcome",
            "passed",
            "--evidence",
            "Проверка завершилась.",
            "--artifact",
            "tracked.txt",
        ]

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(sys, "stdout", io.StringIO()),
        ):
            MODULE.main()

        _, restored = MODULE.load_state(self.root)
        application = restored["applications"]["check-core"]
        self.assertEqual(application["outcome"], "failed")
        self.assertEqual(restored["status"], "interrupted")
        self.assertIsNone(restored["active_application"])
        self.assertEqual(
            restored["pending_snapshot"],
            MODULE.repository_snapshot(self.root),
        )

    def test_review_requires_accept_decision(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.start_application(
            state,
            argparse.Namespace(
                id="review-core",
                stage="repository",
                capability="skill:core-check",
                finding=None,
                method="review",
                surface="Ядро",
                action="Проверить ядро.",
                priority_rationale="Обзор устраняет основной риск.",
                subject=["tracked.txt"],
            ),
            self.root,
        )
        with self.assertRaisesRegex(MODULE.ReviewError, "не допускает"):
            MODULE.finish_application(
                state,
                argparse.Namespace(
                    application="review-core",
                    outcome="passed",
                    decision="needs_human_decision",
                    evidence=["Нужно решение"],
                    artifact=["tracked.txt"],
                    command=None,
                ),
                self.root,
            )

    def test_observation_command_is_executed_by_controller(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(MODULE.ReviewError, "кода завершения 0"):
            self.apply(
                state,
                identifier="check-core",
                capability="skill:core-check",
                artifacts=[],
                command="exit 7",
            )

    def test_finish_parser_preserves_operation_and_observation_command(self) -> None:
        args = MODULE.build_parser().parse_args(
            [
                "finish-application",
                "--application",
                "check-core",
                "--outcome",
                "passed",
                "--evidence",
                "Проверка завершилась.",
                "--command",
                "test -f tracked.txt",
            ],
        )
        self.assertEqual(args.operation, "finish-application")
        self.assertEqual(args.command, "test -f tracked.txt")

    def test_noncheck_capability_requires_applied_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.set_stage(state, "repository", "running")
        decision = state["capability_decisions"]["skill:core-check"]
        decision["participation"] = "constraint"
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанного применения",
        ):
            MODULE.set_stage(state, "repository", "complete")
        self.apply(
            state,
            identifier="constraint-core",
            capability="skill:core-check",
            outcome="applied",
        )
        MODULE.set_stage(state, "repository", "complete")

    def test_application_requires_priority_rationale(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "наибольшей ожидаемой пользы",
        ):
            MODULE.start_application(
                state,
                argparse.Namespace(
                    id="check-core",
                    stage="repository",
                    capability="skill:core-check",
                    finding=None,
                    method="validation",
                    surface="Ядро",
                    action="Проверить ядро.",
                    priority_rationale=None,
                ),
                self.root,
            )

    def test_work_areas_do_not_impose_declared_order(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        MODULE.set_stage(state, "requirements", "running")
        self.assertEqual(state["stages"]["requirements"]["status"], "running")
        MODULE.set_stage(state, "design", "running")
        self.assertEqual(state["stages"]["requirements"]["status"], "pending")
        self.assertEqual(state["stages"]["design"]["status"], "running")

    def test_reopening_area_does_not_assume_downstream_dependencies(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        for stage in state["stages"].values():
            stage["status"] = "complete"
            stage["input_snapshot"] = state["snapshot"]["id"]

        MODULE.set_stage(state, "requirements", "pending")

        self.assertEqual(state["stages"]["repository"]["status"], "complete")
        self.assertEqual(state["stages"]["requirements"]["status"], "pending")
        self.assertIsNone(state["stages"]["requirements"]["input_snapshot"])
        for name in ("design", "code", "tests", "assurance", "impact"):
            self.assertEqual(state["stages"][name]["status"], "complete")

    def test_reopening_later_stage_preserves_completed_predecessor_evidence(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        MODULE.set_stage(state, "repository", "complete")
        state["snapshot"]["id"] = "later-snapshot"

        MODULE.set_stage(state, "requirements", "pending")

        self.assertIn(
            "skill:core-check",
            MODULE.successful_capability_applications(state),
        )

    def test_successful_retry_supersedes_failed_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core-failed",
            capability="skill:core-check",
            outcome="failed",
        )
        self.apply(
            state,
            identifier="check-core-passed",
            capability="skill:core-check",
        )
        MODULE.set_stage(state, "repository", "complete")

    def test_capability_change_invalidates_application(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        state["capability_decisions"]["skill:core-check"]["input_hash"] = "new"
        with self.assertRaisesRegex(
            MODULE.ReviewError,
            "доказанного применения",
        ):
            MODULE.set_stage(state, "repository", "complete")

    def test_terminal_transition_rechecks_live_snapshot(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        for identifier, decision in state["capability_decisions"].items():
            if identifier != "skill:core-check":
                decision.update(
                    {
                        "status": "classified",
                        "applicable": False,
                        "participation": "not_applicable",
                    },
                )
        for stage in state["stages"].values():
            stage["status"] = "complete"
        self.write("tracked.txt", "later\n")
        with self.assertRaisesRegex(MODULE.ReviewError, "область Git"):
            MODULE.transition(state, "complete", None, self.root)

    def test_terminal_transition_accepts_current_live_inputs(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        self.apply(
            state,
            identifier="check-core",
            capability="skill:core-check",
        )
        for identifier, decision in state["capability_decisions"].items():
            if identifier != "skill:core-check":
                decision.update(
                    {
                        "status": "classified",
                        "applicable": False,
                        "participation": "not_applicable",
                    },
                )
        for stage in state["stages"].values():
            stage["status"] = "complete"
        MODULE.transition(state, "complete", None, self.root)
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["history"][-2]["event"], "terminal_inputs_verified")

    def test_migration_invalidates_legacy_checks(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 1
        state["checks"]["legacy"] = {
            "stage": "repository",
            "capability": "skill:core-check",
            "finding": None,
            "status": "passed",
            "evidence": ["Самооценка"],
        }
        for stage in state["stages"].values():
            stage["status"] = "complete"
        MODULE.migrate_state(state)
        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["checks"], {})
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["stages"]["repository"]["status"], "pending")
        self.assertIsNone(state["current_stage"])

    def test_migration_invalidates_version_two_applications_without_priority(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 2
        state["applications"]["legacy"] = {
            "status": "complete",
            "capability": "skill:core-check",
        }
        state["stages"]["repository"]["status"] = "complete"

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["stages"]["repository"]["status"], "pending")
        self.assertIn("найти концепцию", state["next_action"].lower())

    def test_migration_invalidates_version_three_formal_applications(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 3
        state["applications"]["formal-only"] = {
            "status": "complete",
            "capability": "skill:core-check",
            "outcome": "passed",
            "command": {"value": "git diff --cached --check", "exit_code": 0},
        }
        state["stages"]["repository"]["status"] = "complete"

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["stages"]["repository"]["status"], "pending")
        self.assertIn("найти концепцию", state["next_action"].lower())

    def test_migration_invalidates_version_four_self_attestation(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 4
        state["applications"]["formal-only"] = {
            "status": "complete",
            "capability": "skill:core-check",
            "outcome": "passed",
            "coverage": "Все требования.",
            "claims": ["Требования согласованы."],
            "subject_artifacts": ["tracked.txt"],
        }
        state["stages"]["requirements"]["status"] = "complete"

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["stages"]["requirements"]["status"], "pending")

    def test_migration_invalidates_version_five_partial_subject_scope(
        self,
    ) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 5
        state["applications"]["partial-requirements"] = {
            "status": "complete",
            "capability": "skill:core-check",
            "outcome": "passed",
            "coverage": "Все требования.",
            "claims": ["Требования согласованы."],
            "subject_scope": [{"reference": "tracked.txt"}],
            "observations": [{"artifact": "tracked.txt"}],
            "claim_support": ["observation-001"],
            "challenge": {"outcome": "refuted"},
        }
        state["stages"]["requirements"]["status"] = "complete"

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["stages"]["requirements"]["status"], "pending")

    def test_migration_from_version_six_restarts_with_concept(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 6
        state["status"] = "waiting_decision"
        state["next_action"] = "Получить решение по проблеме finding-1."
        state["applications"]["completed"] = {
            "status": "complete",
            "outcome": "passed",
        }

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["applications"], {})
        self.assertIsNone(state["decision_brief"])
        self.assertEqual(state["concept_review"]["status"], "pending")
        self.assertIn("найти концепцию", state["next_action"].lower())
        self.assertTrue(state["history"][-1]["previous_checks_invalidated"])

    def test_migration_from_version_seven_restarts_with_concept(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 7
        state["applications"]["technical-first"] = {
            "status": "complete",
            "outcome": "passed",
        }
        state["findings"]["technical-finding"] = {
            "status": "open",
        }

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["applications"], {})
        self.assertEqual(state["findings"], {})
        self.assertEqual(state["concept_review"]["status"], "pending")
        self.assertEqual(
            state["history"][-1]["invalidated_applications"],
            4,
        )
        self.assertEqual(state["history"][-1]["invalidated_findings"], 1)

    def test_migration_from_version_eight_adds_knowledge_barrier(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 8
        state.pop("knowledge_review")

        MODULE.migrate_state(state)

        self.assertEqual(state["schema_version"], MODULE.STATE_SCHEMA_VERSION)
        self.assertEqual(state["knowledge_review"]["status"], "pending")
        self.assertEqual(state["applications"], {})
        self.assertIn("найти концепцию", state["next_action"].lower())

    def test_migration_cli_archives_previous_state(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 7
        state["applications"]["technical-first"] = {
            "status": "complete",
            "outcome": "passed",
        }
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        arguments = [
            str(SCRIPT),
            "migrate",
            "--repo",
            str(self.root),
        ]
        output = io.StringIO()

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(sys, "stdout", output),
        ):
            MODULE.main()

        result = json.loads(output.getvalue())
        archive = Path(result["archive"])
        self.assertTrue(archive.is_file())
        archived = MODULE.load_json(archive)
        self.assertIn("technical-first", archived["applications"])
        _, restored = MODULE.load_state(self.root)
        self.assertEqual(restored["concept_review"]["status"], "pending")

    def test_terminal_version_seven_state_can_be_migrated(self) -> None:
        state = self.new_state(self.root, "manual", None, False)
        state["schema_version"] = 7
        state["status"] = "complete"
        state["next_action"] = None
        MODULE.atomic_write(MODULE.state_path(self.root), state)
        arguments = [
            str(SCRIPT),
            "migrate",
            "--repo",
            str(self.root),
        ]

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(sys, "stdout", io.StringIO()),
        ):
            MODULE.main()

        _, restored = MODULE.load_state(self.root)
        self.assertEqual(
            restored["schema_version"],
            MODULE.STATE_SCHEMA_VERSION,
        )
        self.assertEqual(restored["status"], "running")
        self.assertEqual(restored["concept_review"]["status"], "pending")

    def test_semantic_table_requires_a_type_for_every_subject(self) -> None:
        scope = [
            {"reference": "docs/alex.md", "sha256": "a"},
            {"reference": "docs/regina.md", "sha256": "b"},
        ]
        criteria = [
            {"id": "persona", "subject_types": ["persona"]},
            {"id": "actor", "subject_types": ["external-actor"]},
        ]
        with self.assertRaisesRegex(MODULE.ReviewError, "каждый предмет"):
            MODULE.parse_subject_types(
                ["docs/alex.md=persona"],
                scope,
                criteria,
            )

    def test_typed_criterion_excludes_another_subject_type(self) -> None:
        application = {
            "subject_scope": [
                {"reference": "docs/alex.md", "semantic_type": "persona"},
                {
                    "reference": "docs/regina.md",
                    "semantic_type": "external-actor",
                },
            ],
        }
        criterion = {"id": "persona", "subject_types": ["persona"]}
        self.assertEqual(
            MODULE.criterion_subjects(application, criterion),
            {"docs/alex.md"},
        )


if __name__ == "__main__":
    unittest.main()
