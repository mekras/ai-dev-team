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
