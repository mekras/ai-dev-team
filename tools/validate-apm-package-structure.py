#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_APM_DEPENDENCIES = {
    "mekras/ai-agent-supervisor",
    "mekras/ai-russian-language",
    "mekras/project-knowlege-corpus",
}

REQUIRED_SKILLS = {
    "ait-docs-concept",
    "ait-setup",
    "ait-analysis",
    "ait-arch-revalidation",
    "ait-interface-design",
    "ait-ui-kit",
    "ait-code-construction",
    "ait-code-review",
    "ait-code-testing",
    "ait-ux-design",
    "ait-ux-audit",
    "ait-docs-structure-audit",
    "ait-docs-structure-design",
    "ait-docs-structure-rules",
    "ait-hypotheses",
    "ait-licensing",
    "ait-personal-data",
    "ait-private-knowledge",
    "ait-routing",
    "ait-readme",
    "ait-reconstructability",
    "ait-reliability",
    "ait-req-analysis",
    "ait-req-elicitation",
    "ait-req-management",
    "ait-req-specification",
    "ait-req-validation",
    "ait-req-revalidation",
    "ait-architecture",
    "ait-decisions",
    "ait-scrum",
    "ait-twelve-factor",
    "ait-sec-access-control",
    "ait-sec-audit",
    "ait-sec-threat-modeling",
    "ait-sec-tooling",
    "ait-writing",
}

REQUIRED_AGENTS = {
    "analyst",
    "coder",
    "documentation-reader",
    "legal",
    "normalizer",
    "project-manager",
    "reliability-engineer",
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

REQUIRED_TEST_FRAGMENTS = (
    "validate-apm-package-structure.py",
    "validate-requirements-structure.py",
    "validate-knowledge-operational.py",
    "validate-corpus-layout.py",
    "validate-hidden-unicode.py",
    "validate-skill-descriptions.py",
    "validate-trigger-evals.py",
    "validate-skill-result-evals.py",
    "tools/validate-portable-corpus-references.py",
    "npm run lint:md",
    "apm compile --validate --local-only --target codex",
    "apm compile --validate --local-only --target claude",
    "apm pack --dry-run",
)

ORGANIZATION_PRINCIPLE_SKILLS = {
    "ait-architecture",
    "ait-code-construction",
    "ait-code-review",
    "ait-docs-structure-audit",
    "ait-docs-structure-design",
    "ait-docs-structure-rules",
}

DECISION_STATUSES = (
    "Предложено",
    "Принято",
    "Отклонено",
    "Устарело",
    "Заменено",
)

FORBIDDEN_TEXT = (
    "team/skills",
    "team/roles",
    "team/foundation",
    "team/templates",
    ".apm/context/skill-index.context.md",
    "--single-agents",
    "subagent-model-routing",
)

PORTABLE_CORE_FORBIDDEN_PATTERNS = (
    (r"docs/adr/\d{4}-", "fixed project ADR path"),
    (
        r"docs/requirements/(?:business|constraints|functional|quality|rules|user)/"
        r"(?:bt|ogr|ft|kach|pr|pt)-\d+\.md",
        "project requirement path",
    ),
    (
        r"knowledge/index/source-impact/\d{4}-\d{2}-\d{2}-",
        "dated project impact report",
    ),
)

PORTABLE_CORE_FORBIDDEN_TEXT = (
    "выпуску этого репозитория",
)

PROJECT_README_REGRESSION_NEEDLES = {
    ".apm/skills/ait-readme/SKILL.md": (
        "slug",
        "человекочитаемый заголовок",
        "references/apm-skill-collections.md",
    ),
    ".apm/skills/ait-readme/references/apm-skill-collections.md": (
        "пакет APM",
        "Не делай Codex",
        "apm install --frozen",
        "git status --short",
    ),
    ".apm/skills/ait-readme/evals/openclaw-skills-regression.md": (
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
    dependencies = manifest.get("dependencies", {}).get("apm")
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) for dependency in dependencies
    ):
        fail("apm.yml dependencies.apm must be a list of package references")
    actual_dependencies = {
        dependency.split("#", maxsplit=1)[0] for dependency in dependencies
    }
    missing_dependencies = sorted(REQUIRED_APM_DEPENDENCIES - actual_dependencies)
    if missing_dependencies:
        fail(f"missing APM dependencies: {', '.join(missing_dependencies)}")
    tests = manifest.get("scripts", {}).get("tests")
    if not isinstance(tests, str) or "validate-apm-package-structure.py" not in tests:
        fail("apm.yml scripts.tests must run the package structure validator")
    missing_test_fragments = [
        fragment for fragment in REQUIRED_TEST_FRAGMENTS if fragment not in tests
    ]
    if missing_test_fragments:
        fail(
            "apm.yml scripts.tests is missing collection checks: "
            + ", ".join(missing_test_fragments),
        )
    evals = manifest.get("scripts", {}).get("evals")
    if not isinstance(evals, str) or "run-skill-evals.py" not in evals:
        fail("apm.yml scripts.evals must run the optional model evaluations")
    if "run-skill-evals.py" in tests:
        fail("apm.yml scripts.tests must not run model evaluations")
    product_evals = manifest.get("scripts", {}).get("product-evals")
    if not isinstance(product_evals, str) or "run-product-evals.py" not in product_evals:
        fail("apm.yml scripts.product-evals must run the product evaluation")
    if "run-product-evals.py --validate" not in tests:
        fail("apm.yml scripts.tests must validate product scenarios")
    if "test_product_evals.py" not in tests:
        fail("apm.yml scripts.tests must test deterministic product scoring")


def check_tree() -> None:
    if (ROOT / "team").exists():
        fail("legacy team/ directory must not exist")

    skill_root = ROOT / ".apm" / "skills"
    skill_entries = list(skill_root.iterdir())
    loose_skill_entries = sorted(
        path.name for path in skill_entries if not path.is_dir() or path.is_symlink()
    )
    if loose_skill_entries:
        fail(
            ".apm/skills must contain only isolated skill directories: "
            + ", ".join(loose_skill_entries),
        )
    actual_skills = {path.name for path in skill_entries}
    invalid_skill_names = sorted(
        skill for skill in actual_skills if not skill.startswith("ait-")
    )
    if invalid_skill_names:
        fail(
            "all product-owned .apm skills must use the ait- prefix: "
            + ", ".join(invalid_skill_names),
        )
    missing_skills = sorted(REQUIRED_SKILLS - actual_skills)
    if missing_skills:
        fail(f"missing .apm skills: {', '.join(missing_skills)}")
    for skill in sorted(actual_skills):
        if not (skill_root / skill / "SKILL.md").is_file():
            fail(f"missing .apm/skills/{skill}/SKILL.md")
    skill_index = skill_root / "ait-routing" / "references" / "skill-index.md"
    if not skill_index.is_file():
        fail("missing .apm/skills/ait-routing/references/skill-index.md")

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


def check_organization_principles_contract() -> None:
    reference = (
        ROOT
        / ".apm/skills/ait-architecture/references"
        / "organization-principles.md"
    )
    if not reference.is_file():
        fail("missing the authoritative organization-principles reference")

    reference_text = reference.read_text(encoding="utf-8")
    required_reference_markers = (
        "## 1. Единственное авторитетное представление знания (DRY)",
        "## 2. Высокая связность",
        "## 3. Слабое сопряжение",
        "проверяющая призма, а не мандат",
    )
    for marker in required_reference_markers:
        if marker not in reference_text:
            fail(f"organization-principles reference is missing {marker!r}")

    canonical_definitions = required_reference_markers[:3]
    for path in (ROOT / ".apm").rglob("*.md"):
        if path == reference:
            continue
        text = path.read_text(encoding="utf-8")
        for definition in canonical_definitions:
            if definition in text:
                fail(
                    f"{path.relative_to(ROOT)} duplicates canonical "
                    f"organization principle {definition!r}",
                )

    for skill in sorted(ORGANIZATION_PRINCIPLE_SKILLS):
        path = ROOT / ".apm/skills" / skill / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        if "organization-principles.md" not in text:
            fail(f"{path.relative_to(ROOT)} does not use organization principles")

    copied_paraphrases = (
        "Держи вместе то, что меняется вместе",
        "у каждого сведения один источник истины",
    )
    for skill in sorted(ORGANIZATION_PRINCIPLE_SKILLS):
        path = ROOT / ".apm/skills" / skill / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        for paraphrase in copied_paraphrases:
            if paraphrase in text:
                fail(
                    f"{path.relative_to(ROOT)} repeats organization principle "
                    f"instead of applying the reference: {paraphrase!r}",
                )

    requirement = ROOT / "docs/requirements/rules/pr-6.md"
    requirement_text = requirement.read_text(encoding="utf-8")
    for marker in (
        "Ссылка не считается соблюдением DRY",
        "Шесть профильных навыков",
        "Отрицательная проверка",
    ):
        if marker not in requirement_text:
            fail(f"{requirement.relative_to(ROOT)} is missing {marker!r}")


def check_decision_status_contract() -> None:
    status_paths = (
        ROOT / "docs/requirements/functional/ft-7.md",
        ROOT / ".apm/skills/ait-decisions/SKILL.md",
        ROOT / ".apm/skills/ait-decisions/references/decision-workflow.md",
        ROOT / ".apm/skills/ait-decisions/references/decision-templates.md",
    )
    for path in status_paths:
        text = path.read_text(encoding="utf-8")
        for status in DECISION_STATUSES:
            if f"`{status}`" not in text:
                fail(
                    f"{path.relative_to(ROOT)} is missing decision status "
                    f"{status!r}",
                )

    concepts = (ROOT / "knowledge/concepts.yml").read_text(encoding="utf-8")
    if "id: decision-record-status" not in concepts or "ADR-0003" not in concepts:
        fail("knowledge/concepts.yml does not reconcile the decision status model")

    evals = (
        ROOT / ".apm/skills/ait-decisions/evals/result-scenarios.json"
    ).read_text(encoding="utf-8")
    if "ait-decisions-decisions-result-rejected-status" not in evals:
        fail("ait-decisions has no result scenario for a rejected decision")


def check_decision_initiative_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-8.md": (
            "setup.decision_records.status: declined",
            "договор журнала",
            "первое принятое решение",
            "незаписанное решение",
        ),
        "docs/requirements/functional/ft-7.md": (
            "?DR-NNNN.md",
            "Существующее соглашение проекта",
            "решения о миграции",
        ),
        ".apm/skills/ait-setup/SKILL.md": (
            "setup.decision_records",
            "?DR-NNNN.md",
            "status: declined",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "decision_records:",
            "record_pattern: ADR-NNNN.md",
            "setup.decision_records.status: declined",
        ),
        ".apm/skills/ait-docs-structure-design/SKILL.md": (
            "Сначала предложи договор журнала",
            "Первую запись предлагай только",
            "Отказ заказчика",
            "без нового запроса",
        ),
        ".apm/skills/ait-docs-structure-design/evals/result-scenarios.json": (
            "ait-docs-structure-design-result-decision-journal-contract",
            "не помещать общий порядок принятия решений в ADR",
        ),
        ".apm/skills/ait-decisions/SKILL.md": (
            "не выдавай договор журнала за",
            "при первом значимом решении",
            "ретроспективную запись",
        ),
        ".apm/skills/ait-decisions/evals/result-scenarios.json": (
            "ait-decisions-decisions-result-journal-kind-and-first-record",
            "не использовать нейтральное имя 0001-decision-governance.md",
        ),
        ".apm/skills/ait-decisions/evals/triggers.json": (
            "ait-decisions-decisions-positive-first-accepted-initiative",
            "ait-decisions-decisions-positive-missing-record-initiative",
        ),
        ".apm/skills/ait-setup/evals/result-scenarios.json": (
            "ait-setup-result-decision-records-declined",
            "ait-setup-result-typed-decision-journal-contract",
            "setup.decision_records.status: declined",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing decision initiative marker "
                    f"{marker!r}",
                )


def check_decision_before_action_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-9.md": (
            "Самопроверка автора не засчитывается",
            "остановку до решения человека",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "Если задача содержит значимый выбор",
            "протокол «решение до действия»",
        ),
        ".apm/skills/ait-decisions/SKILL.md": (
            "Самопроверка автора не считается вторым взглядом",
            "кто и когда принял запись",
            "заменяет решение человека.",
        ),
        ".apm/skills/ait-decisions/evals/result-scenarios.json": (
            "ait-decisions-decisions-result-review-before-action",
            "ait-decisions-decisions-result-human-stop-on-close-options",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing decision-before-action marker "
                    f"{marker!r}",
                )


def check_interface_quality_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-10.md": (
            "обязательной проверки веб-интерфейса",
            "Сценарий ручной приёмки",
            "предлагает UI Kit",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "ait-interface-design",
            "ait-ui-kit",
            "платформенные правила",
        ),
        ".apm/skills/ait-interface-design/SKILL.md": (
            "setup.interface_checks.level",
            "required`, `recommended` или `manual`",
            "не выдавай ручную приёмку за уже состоявшуюся",
        ),
        ".apm/skills/ait-setup/SKILL.md": (
            "setup.interface_checks.level",
            "уровень интерфейсных проверок",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "interface_checks:",
            "level: recommended",
        ),
        ".apm/skills/ait-interface-design/evals/result-scenarios.json": (
            "ait-interface-design-interface-design-result-required-web-checks",
            "ait-interface-design-interface-design-result-manual-acceptance",
        ),
        ".apm/skills/ait-ui-kit/SKILL.md": (
            "не нужен`, `нужен стартовый набор`",
            "экспериментальный`, `стабильный` и `устаревающий",
            "Несовместимое изменение",
        ),
        ".apm/skills/ait-ui-kit/evals/result-scenarios.json": (
            "ait-ui-kit-result-create-maintain-use",
            "ait-ui-kit-result-breaking-change-stop",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing interface quality marker "
                    f"{marker!r}",
                )


def check_setup_dialogue_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-18.md": (
            "setup.project_profile",
            "несколько форм",
            "ответить номером",
            "подменяет недоступный механизм",
            "фактически развёрнутую APM-копию",
        ),
        "knowledge/concepts.yml": (
            "id: project-profile",
            "характер проекта",
            "SREQ-138",
        ),
        ".apm/skills/ait-setup/SKILL.md": (
            "профиль проекта",
            "разрешай ответить номером",
            "не подменяй меню",
            "активного `ait-setup`",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "## Договор вопросов",
            "## Профиль проекта",
            "setup.project_profile",
            "## Уровень интерфейсных проверок",
        ),
        ".apm/skills/ait-setup/evals/result-scenarios.json": (
            "ait-setup-result-vague-project-profile",
            "ait-setup-result-interface-checks-explained-choice",
            "ait-setup-result-deployed-version-drift-stop",
            "ait-setup-result-commit-message-scheme-sequential-question",
            "варианты пронумерованы и разрешён ответ номером",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing setup dialogue marker "
                    f"{marker!r}",
                )


def check_commit_message_scheme_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-17.md": (
            "нескольких поддерживаемых схем",
            "setup.commit_messages",
            "рабочее правило проекта",
            "не объединяет",
        ),
        "docs/pdr/README.md": (
            "Product Decision Record (PDR)",
            "PDR-0001",
            "PDR-0002",
            "PDR-0003",
        ),
        "docs/pdr/PDR-0001-conventional-commits.md": (
            "Статус:",
            "## Достоинства",
            "## Недостатки",
            "## Решение",
        ),
        "docs/pdr/PDR-0002-gitmoji.md": (
            "Статус:",
            "## Достоинства",
            "## Недостатки",
            "## Решение",
        ),
        "docs/pdr/PDR-0003-pro-git-commit-guidelines.md": (
            "Статус:",
            "## Достоинства",
            "## Недостатки",
            "## Решение",
        ),
        ".apm/skills/ait-setup/SKILL.md": (
            "conventional-commits",
            "gitmoji",
            "pro-git",
            "setup.commit_messages",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "## Схема сообщений коммитов",
            "setup.commit_messages.scheme",
            "setup.commit_messages.emoji_format",
        ),
        ".apm/skills/ait-commit-messages/SKILL.md": (
            "setup.commit_messages",
            "расходятся",
            "фактический состав коммита",
        ),
        ".apm/skills/ait-commit-messages/evals/triggers.json": (
            "ait-commit-messages-positive-compose",
            "ait-commit-messages-boundary-setup",
        ),
        ".apm/skills/ait-commit-messages/evals/result-scenarios.json": (
            "ait-commit-messages-result-conventional-commits",
            "ait-commit-messages-result-gitmoji-shortcode",
            "ait-commit-messages-result-pro-git-russian",
            "ait-commit-messages-result-conflicting-settings-stop",
        ),
        ".apm/skills/ait-setup/evals/result-scenarios.json": (
            "ait-setup-result-commit-message-scheme-choice",
            "не выбирать схему молча",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing commit message scheme marker "
                    f"{marker!r}",
                )

    allowed_pdr_statuses = {
        "Предложено",
        "Принято",
        "Отклонено",
        "Устарело",
        "Заменено",
    }
    for relative_path in (
        "docs/pdr/PDR-0001-conventional-commits.md",
        "docs/pdr/PDR-0002-gitmoji.md",
        "docs/pdr/PDR-0003-pro-git-commit-guidelines.md",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        status_match = re.search(r"^- Статус: (.+)$", text, re.MULTILINE)
        if status_match is None or status_match.group(1) not in allowed_pdr_statuses:
            fail(f"{relative_path} has an unsupported PDR status")


def check_requirements_elicitation_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-11.md": (
            "требования-кандидаты с типом, основанием и статусом",
            "не допускает выдавать черновик за утверждённую",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "ait-req-elicitation",
            "Учитывай класс проекта",
        ),
        ".apm/skills/ait-req-elicitation/SKILL.md": (
            "Верни черновик требований-кандидатов",
            "основание или источник и статус",
            "им статус утверждённой спецификации",
        ),
        ".apm/skills/ait-req-elicitation/evals/result-scenarios.json": (
            "ait-req-elicitation-requirements-elicitation-result-free-form-request",
            "черновик требований-кандидатов с типом, основанием и статусом",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing requirements elicitation "
                    f"marker {marker!r}",
                )


def check_twelve_factor_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-12.md": (
            "предлагает создать ADR",
            "не создаёт и не принимает ADR без согласия",
            "TFA-014",
        ),
        ".apm/skills/ait-twelve-factor/SKILL.md": (
            "статус: `применима`, `частично применима` или `неприменима`",
            "предложи создать ADR до проектирования решений по факторам",
            "принимай ADR без согласия владельца проекта",
        ),
        ".apm/skills/ait-twelve-factor/evals/result-scenarios.json": (
            "ait-twelve-factor-result-early-applicable-saas-adr",
            "ait-twelve-factor-result-inapplicable-library-no-adr",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "включи `ait-twelve-factor` для проверки применимости",
            "предложить ADR об использовании всей",
        ),
        "knowledge/data/tfa/items/normalized-tfa-source.md/statements.yml": (
            "id: TFA-014",
            "SaaS-приложений",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing Twelve-Factor marker "
                    f"{marker!r}",
                )


def check_reconstructability_contract() -> None:
    required_markers = {
        "docs/requirements/functional/ft-19.md": (
            "канонические входы, контур исполнения",
            "поведенческая\nэквивалентность",
            "Обычная ветка текущего рабочего дерева не",
            "SDDP-001",
        ),
        ".apm/skills/ait-reconstructability/SKILL.md": (
            "статус применимости: `применима`, `частично применима`",
            "Побитовую идентичность требуй только",
            "пользовательские данные ради проверки",
            "Обычная ветка в текущем рабочем дереве не считается изоляцией",
            "Не создавай и не принимай запись без решения владельца",
        ),
        ".apm/skills/ait-reconstructability/evals/result-scenarios.json": (
            "ait-reconstructability-result-applicable-safe-slice",
            "ait-reconstructability-result-prototype-no-heavy-process",
            "ait-reconstructability-result-unsafe-current-branch-stop",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "включи `ait-reconstructability`",
            "Наличие документации, тестов или агента ИИ",
        ),
        "knowledge/data/sddp/items/paper/statements.yml": (
            "id: SDDP-003",
            "id: SDDP-004",
        ),
        "knowledge/data/augr/items/guide/statements.yml": (
            "id: AUGR-002",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing reconstructability marker "
                    f"{marker!r}",
                )


def check_connection_effort_contract() -> None:
    required_markers = {
        "docs/requirements/quality/kach-1.md": (
            "## Единица измерения",
            "отдельная смысловая операция",
            "Конец пути — продукт установлен",
            "смысловых действий или переносом",
        ),
        ".apm/skills/ait-readme/SKILL.md": (
            "каждый обязательный выбор или ввод",
            "установленного, настроенного и проверенного проекта",
            "Скрипт или составная команда не уменьшают",
        ),
        ".apm/skills/ait-readme/evals/installation-vs-project-connection.md": (
            "## Сравнение трудоёмкости подключения",
            "Отрицательный случай",
            "Такой путь нельзя объявлять более",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing connection effort marker "
                    f"{marker!r}",
                )


def check_portability_contract() -> None:
    manifest = read_yaml(ROOT / "apm.yml")
    if set(manifest.get("targets", [])) != {"claude", "codex"}:
        fail("apm.yml must validate the portable package for claude and codex")

    required_markers = {
        "docs/requirements/quality/kach-2.md": (
            "Инструментальное исключение допустимо",
            "условие пересмотра или удаления исключения",
            "для `codex` и",
        ),
        ".apm/instructions/ai-dev-team-connection.instructions.md": (
            "# Маршрутизация ai-dev-team",
            "Полный протокол маршрутизации",
            "ait-routing/SKILL.md",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "## Объяснение маршрута человеку",
            "ai-work-result-evaluation",
        ),
        "apm.yml": (
            "apm compile --validate --local-only --target codex",
            "apm compile --validate --local-only --target claude",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing portability marker {marker!r}",
                )


def check_codex_routing_reachability() -> None:
    """Проверяет загрузчик в фактически скомпилированном корневом AGENTS.md."""
    with tempfile.TemporaryDirectory(prefix="ai-dev-team-codex-") as temporary:
        output_root = Path(temporary)
        completed = subprocess.run(
            [
                "apm",
                "compile",
                "--local-only",
                "--target",
                "codex",
                "--root",
                str(output_root),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            fail(f"cannot compile Codex routing loader: {detail}")
        agents = output_root / "AGENTS.md"
        if not agents.is_file():
            fail("Codex compilation did not create a root AGENTS.md")
        text = agents.read_text(encoding="utf-8")
    required_markers = (
        ".agents/skills/ait-routing/SKILL.md",
        "Режим менеджера: лёгкий|полный.",
        "Не начинай предметную работу до этого шага.",
    )
    for marker in required_markers:
        if marker not in text:
            fail(f"compiled Codex AGENTS.md is missing routing loader {marker!r}")
    if "## Передача результата" in text:
        fail("compiled Codex AGENTS.md contains the routing protocol instead of a loader")


def check_deployed_skill_references() -> None:
    for path in sorted((ROOT / ".apm" / "skills").glob("*/SKILL.md")):
        if "../../context/" in path.read_text(encoding="utf-8"):
            fail(
                f"{path.relative_to(ROOT)} refers to ../../context/, which is "
                "not deployed with installed skills",
            )


def check_internal_structure_independence_contract() -> None:
    required_markers = {
        "docs/requirements/quality/kach-3.md": (
            "К публичному контракту относятся",
            "Внутренними считаются расположение исходников",
            "не создаёт действий в целевом проекте",
        ),
        ".apm/skills/ait-changelog/SKILL.md": (
            "изменение документированной структуры целевого проекта",
            "перенос исходника, справки или шаблона внутри",
            "признай утечку контракта",
        ),
        ".apm/skills/ait-changelog/evals/result-scenarios.json": (
            "ait-changelog-result-skip-non-user-visible-change",
            "не добавлены действия в целевом проекте",
            "не объявлять внутренний путь публичным контрактом",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing internal structure marker "
                    f"{marker!r}",
                )


def check_human_readable_communication_contract() -> None:
    required_markers = {
        "docs/requirements/quality/kach-4.md": (
            "сначала называет смысл понятными словами",
            "конфигурация и машинный вывод",
            "объяснения цели этих элементов.",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "## Обязательный первый ответ",
            "Режим менеджера: лёгкий|полный.",
            "начальный маршрут по запросу",
            "## Объяснение маршрута человеку",
            "проверка требований",
            "сохраняй точное написание",
        ),
        ".apm/instructions/ai-dev-team-connection.instructions.md": (
            "Режим менеджера: лёгкий|полный.",
            "Маршрут: ...",
        ),
        ".apm/agents/project-manager.agent.md": (
            "сначала называй смысл этапа",
            "Не заменяй объяснение списком внутренних",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing human-readable communication "
                    f"marker {marker!r}",
                )


def check_concise_text_contract() -> None:
    required_markers = {
        "docs/requirements/quality/kach-5.md": (
            "Удаление допустимо",
            "Лаконичность не служит основанием",
            "требует домысливания",
        ),
        ".apm/skills/ait-writing/SKILL.md": (
            "можно ли удалить каждый повтор",
            "не удалены ли ради краткости",
            "Не ставь целевой процент сокращения",
        ),
        ".apm/skills/ait-writing/evals/result-scenarios.json": (
            "ait-writing-result-user-doc-keeps-meaning-level",
            "без потери условий, ограничений, точных команд и проверки",
            "не удалять ради краткости условия",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing concise text marker {marker!r}",
                )


def check_decision_record_quality_contract() -> None:
    required_markers = {
        "docs/requirements/quality/kach-6.md": (
            "вариант без него или проверенное",
            "При общей «дыре»",
            "не выдумывая фиктивный вариант",
            "внутренняя работа агента",
        ),
        ".apm/skills/ait-decisions/SKILL.md": (
            "Для каждого существенного недостатка",
            "неизбежен для всего",
            "Контекст начни с краткой формулировки",
        ),
        ".apm/skills/ait-decisions/references/decision-workflow.md": (
            "проверенное ограничение",
            "неизбежным для всего пространства",
            "Не превращай контекст в конспект всей работы над записью",
        ),
        ".apm/skills/ait-decisions/evals/result-scenarios.json": (
            "ait-decisions-decisions-result-option-space-gap",
            "общий существенный недостаток",
            "не принимать запись с незакрытой дырой",
            "ait-decisions-decisions-result-concise-context-boundaries",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} is missing decision record quality "
                    f"marker {marker!r}",
                )


def check_knowledge_basis_contract() -> None:
    required_markers = {
        "docs/requirements/rules/pr-4.md": (
            "Значимым считается изменение",
            "Формального сообщения",
            "validate-knowledge-operational.py",
        ),
        ".apm/agents/project-manager.agent.md": (
            "Проверка основания в корпусе знаний",
            "проверяемый след",
            "не имитируй проверку",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "Проверить основание в корпусе знаний",
            "область поиска",
            "не имитируй проверку",
        ),
        ".apm/skills/ait-routing/evals/result-scenarios.json": (
            "ait-routing-routing-result-significant-change-checks-corpus",
            "ASKL-001",
            "ASKL-002",
        ),
        "apm.yml": ("validate-knowledge-operational.py",),
        "knowledge/operational-check.yml": (
            "data/gist/items/7c8f65572930a21efa62623557d83f6e/index.html",
            "spdx-oslbp-022525a.headers.txt",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing knowledge-basis contract surface: {relative_path}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover knowledge-basis marker "
                    f"{marker!r}",
                )


def check_self_application_contract() -> None:
    required_markers = {
        "docs/requirements/rules/pr-5.md": (
            "Авторитетный переносимый источник",
            "apm install --frozen",
            "тело каждой продуктовой роли",
        ),
        "AGENTS.md": (
            "## Самоприменение продукта",
            "изменяй только в `.apm/`",
            "apm audit --ci",
        ),
        "docs/development.md": (
            "## Самоприменение продукта",
            "правьте сгенерированную копию",
            "mini_mechanical",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover self-application marker "
                    f"{marker!r}",
                )

    source_skills = ROOT / ".apm/skills"
    deployed_skills = ROOT / ".agents/skills"
    skill_dirs = sorted(
        path for path in source_skills.iterdir() if path.is_dir()
    )
    for skill_dir in skill_dirs:
        source = skill_dir / "SKILL.md"
        deployed = deployed_skills / skill_dir.name / "SKILL.md"
        if not deployed.is_file():
            fail(
                "self-application skill projection is missing: "
                f"{deployed.relative_to(ROOT)}",
            )
        if source.read_bytes() != deployed.read_bytes():
            fail(
                "self-application skill projection is stale: "
                f"{deployed.relative_to(ROOT)}",
            )

    for source in sorted((ROOT / ".apm/agents").glob("*.agent.md")):
        agent_name = source.name.removesuffix(".agent.md")
        match = re.match(
            rb"^---\r?\n.*?\r?\n---\r?\n(.*)$",
            source.read_bytes(),
            flags=re.S,
        )
        if not match:
            fail(f"cannot read role body from {source.relative_to(ROOT)}")
        deployed = ROOT / ".codex/agents" / f"{agent_name}.toml"
        if not deployed.is_file():
            fail(
                "self-application role projection is missing: "
                f"{deployed.relative_to(ROOT)}",
            )
        with deployed.open("rb") as stream:
            role = tomllib.load(stream)
        deployed_body = role.get("developer_instructions", "").strip().encode()
        if deployed_body != match.group(1).strip():
            fail(
                "self-application role projection is stale: "
                f"{deployed.relative_to(ROOT)}",
            )


def check_user_development_journey_contract() -> None:
    required_markers = {
        "docs/requirements/user/pt-1.md": (
            "Подключение включает не только установку",
            "не обязан заранее знать",
            "обычная задача проходит путь",
        ),
        "README.md": (
            "## Работа с проектом",
            "Продукт сам подберёт специалистов",
            "Подтвердите работу или",
        ),
        ".apm/skills/ait-readme/evals/installation-vs-project-connection.md": (
            "продолжить путь первой обычной задачей",
            "технические имена ролей или навыков",
            "явной приёмке",
        ),
        ".apm/agents/project-manager.agent.md": (
            "Менеджер всегда запускает задачу через единый входной этап",
            "Передаёт человеку результаты на приёмку",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover user journey marker "
                    f"{marker!r}",
                )


def check_free_form_goal_contract() -> None:
    required_markers = {
        "docs/requirements/user/pt-2.md": (
            "достаточно описать хотя бы один",
            "обязательная анкета до начала",
            "не становится утверждённой спецификацией",
        ),
        "README.md": (
            "Опишите цель, проблему или ожидаемый результат обычными словами",
        ),
        ".apm/skills/ait-req-elicitation/SKILL.md": (
            "Для начала достаточно",
            "обязательную анкету",
        ),
        ".apm/skills/ait-req-elicitation/evals/result-scenarios.json": (
            "ait-req-elicitation-requirements-elicitation-result-free-form-request",
            "хотя бы цель, проблему или ожидаемый результат",
            "обязательную анкету",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover free-form goal marker "
                    f"{marker!r}",
                )


def check_client_target_contract() -> None:
    required_markers = {
        "docs/requirements/user/pt-3.md": (
            "содержит ровно одну цель",
            "не считается согласием настроить оба",
            "проверяется для `claude` и `codex`",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "определи ровно один выбранный клиент",
            "не считай само по себе наличие",
            "останови настройку на одном вопросе о клиенте",
        ),
        ".apm/skills/ait-setup/evals/result-scenarios.json": (
            "Результат использует ровно один явно выбранный клиент",
            "не настраивать несколько клиентских целей",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover client target marker "
                    f"{marker!r}",
                )

    user_surfaces = (
        ROOT / "README.md",
        ROOT
        / ".apm/skills/ait-readme/evals"
        / "installation-vs-project-connection.md",
    )
    forbidden_targets = (
        "--target all",
        "--target claude,codex",
        "--target codex,claude",
    )
    for path in user_surfaces:
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_targets:
            if fragment in text:
                fail(
                    f"{path.relative_to(ROOT)} contains multiple-client "
                    f"installation target {fragment!r}",
                )
        for line in text.splitlines():
            if "apm install mekras/ai-dev-team" not in line:
                continue
            if not re.search(r"--target (?:claude|codex)(?:\s|$|`)", line):
                fail(
                    f"{path.relative_to(ROOT)} contains installation command "
                    "without one explicit client target",
                )


def check_result_acceptance_contract() -> None:
    required_markers = {
        "docs/requirements/user/pt-4.md": (
            "Для статуса `готов к приёмке`",
            "Статус `принят` появляется только после явного решения",
            "Промежуточный результат можно передать следующей роли",
        ),
        ".apm/agents/project-manager.agent.md": (
            "### Передача результата на приёмку",
            "Статус `готов к приёмке` допустим",
            "Статус `принят` ставится только после явного решения человека",
            "Частично проверенный результат нельзя выдавать",
        ),
        ".apm/skills/ait-routing/evals/result-scenarios.json": (
            "ait-routing-routing-result-handoff-for-acceptance",
            "не выдавать успешные автоматические тесты за решение заказчика",
        ),
        ".apm/skills/ait-routing/SKILL.md": (
            "ai-work-result-evaluation",
            "маршрут последним этапом перед передачей",
            "допустим только после этой проверки",
            "критерии приёмки и свидетельства",
            "пропущенные проверки, ограничения и остаточные риски",
        ),
        ".agents/skills/ai-work-result-evaluation/SKILL.md": (
            "Принять решение: `accept`, `revise`, `reject`,",
            "проверяемые артефакты или след выполнения",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing result acceptance surface: {relative_path}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover result acceptance "
                    f"marker {marker!r}",
                )

    manifest = read_yaml(ROOT / "apm.yml")
    apm_dependencies = manifest.get("dependencies", {}).get("apm", [])
    if not any(
        dependency.startswith("mekras/ai-agent-supervisor#")
        for dependency in apm_dependencies
    ):
        fail(
            "apm.yml must provide ai-work-result-evaluation through "
            "mekras/ai-agent-supervisor",
        )


def check_end_to_end_business_contract() -> None:
    required_markers = {
        "docs/requirements/business/bt-1.md": (
            "Бизнес-результат подключения",
            "Контур считается целостным",
            "Недоступная специализация, обязательная",
            "Сквозная проверка начинает обычную задачу",
        ),
        "docs/requirements/functional/ft-1.md": (
            "помогать человеку формулировать цель",
            "В сквозном сценарии заказчик описывает цель",
        ),
        "README.md": (
            "Опишите цель, проблему или ожидаемый результат",
            "проведённые проверки и оставшиеся ограничения",
        ),
        ".apm/agents/project-manager.agent.md": (
            "Менеджер всегда запускает задачу через единый входной этап",
            "### Передача результата на приёмку",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover end-to-end business "
                    f"marker {marker!r}",
                )


def check_business_effect_evidence_contract() -> None:
    required_markers = {
        "docs/requirements/business/bt-2.md": (
            "Ожидаемый бизнес-эффект",
            "свойством каждого подключения продукта",
            "не доказывают снижение",
            "## Показатели эффекта",
            "продукт против того же клиентского инструмента",
            "новая версия продукта против предыдущей принятой версии",
            "До выбора числа повторов и числовых порогов",
            "Без таких данных сообщается снижение",
            "с неполным доказательством",
        ),
        "BACKLOG.md": (
            "Для проверки бизнес-эффекта из `БТ-2`",
            "число повторов, допустимый разброс",
            "наблюдаемые показатели",
        ),
        ".agents/skills/ai-work-result-evaluation/SKILL.md": (
            "Укажи критерии проверки, метрику и порог пригодности",
            "Сравни с базовой линией",
        ),
        "evals/product-scenarios.yml": (
            '"owner_reply"',
            '"expected_artifact_groups"',
            '"required_commands"',
        ),
        "tools/run-product-evals.py": (
            'VARIANTS = ("bare", "current", "previous")',
            '"needs_human_decision"',
            '"unauthorized_decisions"',
            '"rework_returns"',
            '"critical_violations"',
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing business effect evidence surface: {relative_path}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover business effect "
                    f"evidence marker {marker!r}",
                )

    requirement_text = (
        ROOT / "docs/requirements/business/bt-2.md"
    ).read_text(encoding="utf-8")
    unsupported_claims = (
        "системное применение практик уменьшает число дефектов",
        "успешные тесты доказывают снижение стоимости",
    )
    for claim in unsupported_claims:
        if claim in requirement_text:
            fail(f"bt-2.md contains unsupported business effect claim {claim!r}")

    manifest = read_yaml(ROOT / "apm.yml")
    evals = manifest.get("scripts", {}).get("evals", "")
    if "run-skill-evals.py" not in evals:
        fail("apm.yml must retain the optional model evaluation command")


def check_priority_tradeoff_contract() -> None:
    required_markers = {
        "docs/requirements/business/bt-3.md": (
            "надёжность и качество являются",
            "обязательными ограничениями",
            "Эффективность применения",
            "Критическое ухудшение надёжности или качества блокирует",
            "явному решению владельца",
            "компенсирует критическое ухудшение",
            "## Проверка требования",
        ),
        ".apm/agents/project-manager.agent.md": (
            "### Выбор между вариантами",
            "Эффективность сравнивается только среди вариантов",
            "неправомерное решение",
            "сопровождении их не компенсирует",
        ),
        ".apm/skills/ait-routing/evals/result-scenarios.json": (
            "priority-constraints-before-efficiency",
            "вариант Б отклонён",
            "вариант В передан владельцу",
            "не выбирать более быстрый вариант с критическим ухудшением",
        ),
        "CHANGELOG.md": (
            "Надёжность и качество не компенсируются скоростью",
            "расходом токенов или будущими затратами на сопровождение",
        ),
    }
    for relative_path, markers in required_markers.items():
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing priority trade-off surface: {relative_path}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover priority trade-off "
                    f"marker {marker!r}",
                )

    requirement_text = (
        ROOT / "docs/requirements/business/bt-3.md"
    ).read_text(encoding="utf-8")
    if "Прочие требования и задачи не должны ухудшать эти качества" in (
        requirement_text
    ):
        fail("bt-3.md retains an untestable absolute non-regression rule")


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


def check_dependency_migration_contract() -> None:
    legacy_skills = ("ru-dev", "ai-application-check")
    paths = [ROOT / "AGENTS.md"]
    paths.extend(
        path
        for path in (ROOT / ".apm").rglob("*")
        if path.is_file() and path.suffix in TEXT_SUFFIXES
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for legacy_skill in legacy_skills:
            if legacy_skill in text:
                fail(
                    f"{path.relative_to(ROOT)} still references removed skill "
                    f"{legacy_skill}",
                )

    required_markers = {
        ".apm/skills/ait-setup/SKILL.md": (
            "неигнорируемые изменения или только изменения агента",
            "по умолчанию 30 дней",
        ),
        ".apm/skills/ait-setup/references/setup-dialogue.md": (
            "## Политика индекса Git",
            "Отсутствующую или нечитаемую дату",
        ),
        ".apm/skills/ait-setup/evals/result-scenarios.json": (
            "ait-setup-result-git-index-policy-choice",
            "ait-setup-result-subagent-policy-review-lifecycle",
        ),
    }
    for relative_path, markers in required_markers.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(
                    f"{relative_path} does not cover dependency migration "
                    f"marker {marker!r}",
                )


def check_portable_core_boundary() -> None:
    apm_root = ROOT / ".apm"
    for path in apm_root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern, description in PORTABLE_CORE_FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                fail(
                    f"{path.relative_to(ROOT)} leaks {description} into "
                    "portable .apm core",
                )
        for marker in PORTABLE_CORE_FORBIDDEN_TEXT:
            if marker in text:
                fail(
                    f"{path.relative_to(ROOT)} leaks repository-only marker "
                    f"{marker!r} into portable .apm core",
                )


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


def check_installation_contract() -> None:
    manifest = read_yaml(ROOT / "apm.yml")
    if manifest.get("name") != "ai-dev-team":
        fail("apm.yml must declare the logical package name ai-dev-team")
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        fail("apm.yml must declare a package version")

    paths = (
        ROOT / "README.md",
        ROOT
        / ".apm/skills/ait-readme/evals"
        / "installation-vs-project-connection.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in ("claude", "codex"):
            command = (
                f"apm install mekras/ai-dev-team#^{version} "
                f"--target {target}"
            )
            if command not in text:
                fail(
                    f"{path.relative_to(ROOT)} does not contain the current "
                    f"{target} installation command",
                )
        if "github.com/mekras/ai-dev-team#master" in text:
            fail(f"{path.relative_to(ROOT)} contains the legacy installation ref")
        forbidden_installation_fragments = (
            "apm install ./",
            "apm install ../",
            "apm install /",
            "apm install file:",
            "#master --target",
            "#main --target",
            "ai-dev-team#^" + version + " --dev",
            "--channel",
        )
        for fragment in forbidden_installation_fragments:
            if fragment in text:
                fail(
                    f"{path.relative_to(ROOT)} contains non-logical "
                    f"installation fragment {fragment!r}",
                )


def main() -> None:
    check_manifest()
    check_tree()
    check_organization_principles_contract()
    check_decision_status_contract()
    check_decision_initiative_contract()
    check_decision_before_action_contract()
    check_interface_quality_contract()
    check_setup_dialogue_contract()
    check_commit_message_scheme_contract()
    check_requirements_elicitation_contract()
    check_twelve_factor_contract()
    check_reconstructability_contract()
    check_connection_effort_contract()
    check_portability_contract()
    check_codex_routing_reachability()
    check_deployed_skill_references()
    check_internal_structure_independence_contract()
    check_human_readable_communication_contract()
    check_concise_text_contract()
    check_decision_record_quality_contract()
    check_knowledge_basis_contract()
    check_self_application_contract()
    check_user_development_journey_contract()
    check_free_form_goal_contract()
    check_client_target_contract()
    check_result_acceptance_contract()
    check_end_to_end_business_contract()
    check_business_effect_evidence_contract()
    check_priority_tradeoff_contract()
    check_forbidden_references()
    check_dependency_migration_contract()
    check_portable_core_boundary()
    check_project_readme_regression()
    check_installation_contract()
    print("APM package structure OK")


if __name__ == "__main__":
    main()
