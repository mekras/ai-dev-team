#!/usr/bin/env python3
"""Проверки переносимого развёртывания исполняемых навыков."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".apm" / "skills"
EXECUTABLE_AREAS = ("SKILL.md", "references", "assets", "scripts")
FORBIDDEN_DEPLOYMENT_PATH = re.compile(
    r"(?:\.apm/|\.agents/|\.claude/|\.codex/|"
    r"(?:^|[^./])skills/[a-z0-9_-]+/(?:SKILL\.md|references|assets|scripts)|"
    r"(?:^|[^./])agents/[a-z0-9_-]+\.agent\.md)"
)


def executable_files() -> list[Path]:
    result: list[Path] = []
    for skill in SKILLS.iterdir():
        if not skill.is_dir():
            continue
        for area in EXECUTABLE_AREAS:
            path = skill / area
            if path.is_file():
                result.append(path)
            elif path.is_dir():
                result.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(result)


class SkillDeploymentPortabilityTests(unittest.TestCase):
    def test_context_rules_reach_both_consumer_targets(self) -> None:
        """Проверяет команду чтения и файлы после установки и компиляции."""
        apm = shutil.which("apm")
        self.assertIsNotNone(apm, "для проверки нужен apm")
        contexts = sorted((ROOT / ".apm" / "context").glob("*.context.md"))
        self.assertEqual(len(contexts), 3)
        local_rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(".agents/skills/ait-routing/SKILL.md", local_rules)
        manifest = yaml.safe_load((ROOT / "apm.yml").read_text(encoding="utf-8"))
        (ROOT / ".ai-dev-team" / "local").mkdir(exist_ok=True)
        cases = (
            ("codex", "AGENTS.md", False),
            ("codex", "AGENTS.md", True),
            ("claude", "CLAUDE.md", False),
        )
        for target, entry, handwritten in cases:
            with (
                self.subTest(target=target, handwritten=handwritten),
                tempfile.TemporaryDirectory(
                    prefix="context-delivery-", dir=ROOT / ".ai-dev-team" / "local"
                ) as temporary,
            ):
                sandbox = Path(temporary)
                package = sandbox / "package"
                consumer = sandbox / "consumer"
                consumer.mkdir()
                if handwritten:
                    (consumer / entry).write_text(
                        "Открой .agents/skills/ait-routing/SKILL.md перед работой.\n",
                        encoding="utf-8",
                    )
                for area in ("context", "instructions"):
                    shutil.copytree(ROOT / ".apm" / area, package / ".apm" / area)
                shutil.copytree(
                    SKILLS / "ait-routing", package / ".apm" / "skills" / "ait-routing"
                )
                # Проверяется доставка контекста, остальные примитивы и зависимости
                # пакета не нужны для этой границы.
                (package / "apm.yml").write_text(
                    yaml.safe_dump({
                        "name": manifest["name"], "version": manifest["version"],
                        "type": "hybrid", "includes": "auto", "targets": [target],
                    }), encoding="utf-8",
                )
                (consumer / "apm.yml").write_text(
                    yaml.safe_dump({
                        "name": "context-consumer", "version": "0.0.0",
                        "targets": [target],
                        "dependencies": {"apm": ["../package"]},
                    }), encoding="utf-8",
                )
                commands = (
                    [apm, "install", "--target", target],
                    [apm, "compile", "--target", target],
                    [apm, "audit", "--ci"],
                )
                for command in commands:
                    completed = subprocess.run(
                        command, cwd=consumer,
                        env={**os.environ, "APM_POLICY_DISABLE": "1"},
                        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        check=False, timeout=120,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stdout)
                surfaces = [consumer / entry]
                if target == "claude":
                    surfaces.extend((consumer / ".claude" / "rules").glob("*.md"))
                self.assertTrue(any(
                    "ait-routing/SKILL.md" in path.read_text(encoding="utf-8")
                    for path in surfaces if path.is_file()
                ), "нет команды загрузки маршрутизатора")
                skill_root = ".agents" if target == "codex" else ".claude"
                routing = consumer / skill_root / "skills" / "ait-routing" / "SKILL.md"
                self.assertEqual(
                    routing.read_bytes(),
                    (SKILLS / "ait-routing" / "SKILL.md").read_bytes(),
                )
                rules = routing.read_text(encoding="utf-8")
                self.assertIn("Перед первой предметной работой в сессии прочитай полностью", rules)
                self.assertIn("name: ai-dev-team", rules)
                self.assertIn("apm_modules/", rules)
                package_roots = [
                    path.parent
                    for path in (consumer / "apm_modules").rglob("apm.yml")
                    if yaml.safe_load(path.read_text(encoding="utf-8")).get("name")
                    == manifest["name"]
                ]
                self.assertEqual(len(package_roots), 1, package_roots)
                for source in contexts:
                    relative = ".apm/context/" + source.name
                    self.assertIn(source.name, rules)
                    installed = package_roots[0] / relative
                    self.assertTrue(installed.is_relative_to(consumer), installed)
                    self.assertTrue(installed.is_file(), installed)
                    self.assertEqual(source.read_bytes(), installed.read_bytes())

    def test_executable_materials_use_only_local_resource_paths(self) -> None:
        findings: list[str] = []
        for path in executable_files():
            if path.suffix not in {".md", ".json", ".py", ".sh", ".yaml", ".yml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for match in FORBIDDEN_DEPLOYMENT_PATH.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
        self.assertEqual(findings, [])

    def test_each_target_installs_skill_resources_without_other_client(self) -> None:
        apm = shutil.which("apm")
        self.assertIsNotNone(apm, "для проверки нужен apm")
        targets = {
            "claude": Path(".claude") / "skills",
            "codex": Path(".agents") / "skills",
        }
        for target, skill_root in targets.items():
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary)
                shutil.copy2(ROOT / "apm.lock.yaml", destination / "apm.lock.yaml")
                completed = subprocess.run(
                    [apm, "install", "--frozen", "--target", target, "--root", temporary],
                    cwd=ROOT,
                    env={**os.environ, "APM_POLICY_DISABLE": "1"},
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout)
                other = ".codex" if target == "claude" else ".claude"
                self.assertFalse((destination / other).exists())
                for source in executable_files():
                    relative = source.relative_to(SKILLS)
                    installed = destination / skill_root / relative
                    self.assertTrue(installed.is_file(), installed)
                    self.assertEqual(source.read_bytes(), installed.read_bytes())


if __name__ == "__main__":
    unittest.main()
