#!/usr/bin/env python3
"""Отклонить сценарий качества результата, чьё задание или оракул оценивает
изменённый артефакт, которого сам сценарий не создаёт в рабочей копии.

Каждый случай объявляет полем "artifact_change", правит ли он существующий
артефакт. Объявление обязательно: определять это по формулировке задания нельзя,
потому что глагол правки часто стоит в пересказе просьбы пользователя, а
оценивается маршрут или разбор. При "artifact_change": true сценарий обязан сам
положить артефакт в рабочую копию через input_files с полем content.

Основание: docs/06-architecture/adr/0013-product-evidence-levels.md, раздел
«Решение» пункт 4 и раздел «Проверка» (вариант 5 — детерминированная проверка
исполнимости сценария).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
PATH_PATTERN = re.compile(r"`([^`\s]*/[^`\s]*)`")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Проверить, что каждый путь артефакта, упомянутый в задании или "
            "оракуле сценария evals/result-scenarios.json, доступен сценарию: "
            "существует в рабочей копии либо задан в input_files с content."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Каталоги навыков или корни для обхода. По умолчанию .apm/skills.",
    )
    return parser.parse_args()


def collect_skill_dirs(root: Path) -> Iterator[Path]:
    """Обойти дерево до границы пакета навыка, не спускаясь внутрь него."""
    if not root.is_dir():
        return
    for entry in sorted(root.iterdir()):
        if entry.name == ".git" or not entry.is_dir():
            continue
        if (entry / "SKILL.md").is_file():
            yield entry
        elif not entry.is_symlink():
            yield from collect_skill_dirs(entry)


def find_skill_dirs(paths: list[Path]) -> list[Path]:
    skill_dirs: set[Path] = set()
    for path in paths:
        path = path.resolve()
        if (path / "SKILL.md").is_file():
            skill_dirs.add(path)
            continue
        skill_dirs.update(collect_skill_dirs(path))
    return sorted(skill_dirs)


def referenced_paths(case: dict[str, Any]) -> set[str]:
    """Собрать пути артефактов, упомянутые в задании или оракуле сценария."""
    texts: list[str] = []
    prompt = case.get("prompt")
    if isinstance(prompt, str):
        texts.append(prompt)
    oracle = case.get("oracle")
    if isinstance(oracle, dict):
        for key in ("success_criteria", "failure_indicators"):
            for item in oracle.get(key) or []:
                if isinstance(item, str):
                    texts.append(item)
    expected_output = case.get("expected_output")
    if isinstance(expected_output, dict):
        for item in expected_output.get("report_structure") or []:
            if isinstance(item, str):
                texts.append(item)

    paths: set[str] = set()
    for text in texts:
        for candidate in PATH_PATTERN.findall(text):
            if candidate.endswith("/") or "*" in candidate:
                # Ссылка на каталог или маску графа влияния, а не на файл.
                continue
            paths.add(candidate)
    return paths


def content_by_path(case: dict[str, Any]) -> dict[str, str]:
    """Содержимое, которое сценарий сам записывает в рабочую копию."""
    content_by_path: dict[str, str] = {}
    for entry in case.get("input_files") or []:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        content = entry.get("content")
        if isinstance(path, str) and isinstance(content, str) and content != "":
            content_by_path[path] = content
    return content_by_path


def is_available(path: str, content_map: dict[str, str], repo_root: Path) -> bool:
    """Путь доступен, если сценарий сам создаёт его содержимое в рабочей
    копии, либо файл действительно существует в проекте."""
    if path in content_map:
        return True
    return (repo_root / path).is_file()


def declared_artifact_change(case: dict[str, Any]) -> bool | None:
    """Прочитать объявление сценария о правке существующего артефакта."""
    declared = case.get("artifact_change")
    return declared if isinstance(declared, bool) else None


def validate_case(
    case: Any,
    index: int,
    skill_name: str,
    repo_root: Path,
    errors: list[str],
) -> None:
    label = f"{skill_name}: cases[{index}]"
    if not isinstance(case, dict):
        return

    content_map = content_by_path(case)

    for path in sorted(
        path
        for path in referenced_paths(case)
        if not is_available(path, content_map, repo_root)
    ):
        errors.append(
            f"{label} ({case.get('id')!r}): артефакт {path!r} упомянут в "
            "задании или оракуле, но не создан в рабочей копии — нет "
            "content в input_files и нет такого файла в репозитории",
        )

    declared = declared_artifact_change(case)
    if declared is None:
        errors.append(
            f"{label} ({case.get('id')!r}): нет объявления artifact_change — "
            "укажите true, если задание или оракул оценивает правку "
            "существующего артефакта, иначе false",
        )
    elif declared and not content_map:
        errors.append(
            f"{label} ({case.get('id')!r}): объявлена правка существующего "
            "артефакта, но сценарий не кладёт его в рабочую копию — добавьте "
            "в input_files запись с полем content",
        )


def read_skill_name(skill_path: Path) -> str | None:
    in_frontmatter = False
    for line in skill_path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def validate_result_file(skill_dir: Path, repo_root: Path) -> list[str]:
    result_path = skill_dir / "evals" / "result-scenarios.json"
    if not result_path.exists():
        return []

    skill_name = read_skill_name(skill_dir / "SKILL.md") or skill_dir.name

    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{result_path}: invalid JSON: {exc}"]

    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        return []

    errors: list[str] = []
    for index, case in enumerate(cases):
        validate_case(case, index, skill_name, repo_root, errors)
    return errors


def main() -> int:
    args = parse_args()
    roots = args.paths or [REPO_ROOT / ".apm" / "skills"]
    skill_dirs = find_skill_dirs(roots)

    errors: list[str] = []
    checked = 0
    for skill_dir in skill_dirs:
        if (skill_dir / "evals" / "result-scenarios.json").exists():
            checked += 1
        errors.extend(validate_result_file(skill_dir, REPO_ROOT))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Проверена исполнимость сценариев результата: {checked}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
