#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SKILLS = {
    "ait-docs-concept",
    "ait-setup",
    "analysis",
    "documentation-structure-audit",
    "documentation-structure-design",
    "documentation-structure-rules",
    "private-project-knowledge",
    "project-management",
    "project-readme",
    "requirements-analysis",
    "requirements-elicitation",
    "requirements-management",
    "requirements-specification",
    "requirements-validation",
    "software-architecture",
    "technical-writing",
}

REQUIRED_AGENTS = {
    "analyst",
    "coder",
    "legal",
    "normalizer",
    "project-manager",
    "security-engineer",
    "software-architect",
    "source-inventory",
    "statement-extractor",
    "technical-writer",
    "ux-specialist",
}

REQUIRED_CONTEXTS = {
    "primary-data.context.md",
    "principles.context.md",
    "source-licenses.context.md",
}

FORBIDDEN_TEXT = (
    "team/skills",
    "team/roles",
    "team/foundation",
    "team/templates",
    ".apm/context/skill-index.context.md",
    "--single-agents",
    "subagent-model-routing",
)

PROJECT_README_REGRESSION_NEEDLES = {
    ".apm/skills/project-readme/SKILL.md": (
        "slug",
        "человекочитаемый заголовок",
        "references/apm-skill-collections.md",
    ),
    ".apm/skills/project-readme/references/apm-skill-collections.md": (
        "пакет APM",
        "Не делай Codex",
        "apm install --frozen",
        "git status --short",
    ),
    ".apm/skills/project-readme/evals/openclaw-skills-regression.md": (
        "# openclaw-skills",
        "Навыки для OpenClaw",
        "APM-пакет",
        "пакет APM",
        "OpenClaw skills",
        "apm compile --target codex",
        "git status --short",
    ),
}

TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
}

SKIP_DIRS = {
    ".git",
    ".agents",
    ".claude",
    ".idea",
    "apm_modules",
    "build",
    "local",
    "node_modules",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path.relative_to(ROOT)} is not a YAML mapping")
    return data


def check_manifest() -> None:
    manifest = read_yaml(ROOT / "apm.yml")
    if manifest.get("type") != "hybrid":
        fail("apm.yml must declare type: hybrid")
    if manifest.get("includes") != "auto":
        fail("apm.yml must declare includes: auto")
    tests = manifest.get("scripts", {}).get("tests")
    if not isinstance(tests, str) or "validate-apm-package-structure.py" not in tests:
        fail("apm.yml scripts.tests must run the package structure validator")


def check_tree() -> None:
    if (ROOT / "team").exists():
        fail("legacy team/ directory must not exist")

    skill_root = ROOT / ".apm" / "skills"
    actual_skills = {path.name for path in skill_root.iterdir() if path.is_dir()}
    missing_skills = sorted(REQUIRED_SKILLS - actual_skills)
    if missing_skills:
        fail(f"missing .apm skills: {', '.join(missing_skills)}")
    for skill in sorted(REQUIRED_SKILLS):
        if not (skill_root / skill / "SKILL.md").is_file():
            fail(f"missing .apm/skills/{skill}/SKILL.md")
    skill_index = skill_root / "project-management" / "references" / "skill-index.md"
    if not skill_index.is_file():
        fail("missing .apm/skills/project-management/references/skill-index.md")

    agent_root = ROOT / ".apm" / "agents"
    actual_agents = {path.name.removesuffix(".agent.md") for path in agent_root.glob("*.agent.md")}
    missing_agents = sorted(REQUIRED_AGENTS - actual_agents)
    if missing_agents:
        fail(f"missing .apm agents: {', '.join(missing_agents)}")
    for agent in sorted(REQUIRED_AGENTS):
        check_agent_frontmatter(agent_root / f"{agent}.agent.md", agent)

    context_root = ROOT / ".apm" / "context"
    actual_contexts = {path.name for path in context_root.glob("*.md")}
    missing_contexts = sorted(REQUIRED_CONTEXTS - actual_contexts)
    if missing_contexts:
        fail(f"missing .apm context files: {', '.join(missing_contexts)}")


def check_agent_frontmatter(path: Path, expected_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        fail(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    metadata = yaml.safe_load(match.group(1)) or {}
    if metadata.get("name") != expected_name:
        fail(f"{path.relative_to(ROOT)} has wrong agent name")
    if not metadata.get("description"):
        fail(f"{path.relative_to(ROOT)} has no description")


def iter_project_text_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path == Path(__file__).resolve():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in TEXT_SUFFIXES:
            result.append(path)
    return result


def check_forbidden_references() -> None:
    for path in iter_project_text_files():
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_TEXT:
            if needle in text:
                fail(f"{path.relative_to(ROOT)} still references {needle}")


def check_project_readme_regression() -> None:
    for relative_path, needles in PROJECT_README_REGRESSION_NEEDLES.items():
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing project-readme regression surface: {relative_path}")
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                fail(
                    f"{relative_path} does not cover project-readme "
                    f"regression marker {needle!r}",
                )


def main() -> None:
    check_manifest()
    check_tree()
    check_forbidden_references()
    check_project_readme_regression()
    print("APM package structure OK")


if __name__ == "__main__":
    main()
