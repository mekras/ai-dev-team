#!/usr/bin/env python3
"""Проверить классификацию участия компонентов в полной проверке."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_CLASSIFICATION = (
    ".apm/skills/ait-project-revalidation/references/capabilities.json"
)
KINDS = {"role", "skill", "rule"}
PARTICIPATION = {
    "check",
    "constraint",
    "preparation",
    "correction",
    "not_applicable",
}
APPLICABILITY = {"always", "model", "never"}
CRITERION_COVERAGE = {"each_subject", "surface"}


class CapabilityError(ValueError):
    """Классификация не соответствует договору."""


def load_document(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityError(f"не удалось прочитать {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CapabilityError("корень классификации должен быть объектом")
    return data


def actual_components(root: Path) -> dict[str, tuple[str, Path]]:
    components: dict[str, tuple[str, Path]] = {}
    patterns = (
        ("role", ".apm/agents", "*.agent.md"),
        ("skill", ".apm/skills", "*"),
        ("rule", ".apm/instructions", "*"),
    )
    for kind, directory, pattern in patterns:
        base = root / directory
        if not base.is_dir():
            raise CapabilityError(f"не найден каталог {directory}")
        for path in sorted(base.glob(pattern)):
            if kind == "skill" and not path.is_dir():
                continue
            if kind != "skill" and not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            components[relative] = (kind, path)
    return components


def require_string(entry: dict[str, Any], key: str, identifier: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapabilityError(f"{identifier}: поле {key} должно быть строкой")
    return value


def validate(root: Path, classification: Path) -> None:
    data = load_document(classification)
    if data.get("version") != 1:
        raise CapabilityError("поддерживается только версия схемы 1")

    stages = data.get("stages")
    if (
        not isinstance(stages, list)
        or not stages
        or not all(isinstance(stage, str) and stage for stage in stages)
        or len(stages) != len(set(stages))
    ):
        raise CapabilityError("stages должен содержать уникальные строки")
    stage_names = set(stages)

    entries = data.get("capabilities")
    if not isinstance(entries, list):
        raise CapabilityError("capabilities должен быть массивом")

    actual = actual_components(root)
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            raise CapabilityError(f"запись {index} должна быть объектом")
        identifier = require_string(raw_entry, "id", f"запись {index}")
        if identifier in seen_ids:
            raise CapabilityError(f"повторяющийся id: {identifier}")
        seen_ids.add(identifier)

        kind = require_string(raw_entry, "kind", identifier)
        if kind not in KINDS:
            raise CapabilityError(f"{identifier}: неизвестный kind {kind}")
        path = require_string(raw_entry, "path", identifier)
        if path in seen_paths:
            raise CapabilityError(f"повторяющийся путь: {path}")
        seen_paths.add(path)
        if path not in actual:
            raise CapabilityError(f"{identifier}: компонент не существует: {path}")
        if actual[path][0] != kind:
            raise CapabilityError(
                f"{identifier}: вид {kind} не соответствует пути {path}",
            )

        require_string(raw_entry, "purpose", identifier)
        participation = require_string(raw_entry, "participation", identifier)
        if participation not in PARTICIPATION:
            raise CapabilityError(
                f"{identifier}: неизвестный participation {participation}",
            )
        applicability = require_string(raw_entry, "applicability", identifier)
        if applicability not in APPLICABILITY:
            raise CapabilityError(
                f"{identifier}: неизвестный applicability {applicability}",
            )
        stage = raw_entry.get("stage")
        if stage is not None and stage not in stage_names:
            raise CapabilityError(f"{identifier}: неизвестный этап {stage}")
        if participation == "not_applicable" and applicability != "never":
            raise CapabilityError(
                f"{identifier}: not_applicable требует applicability never",
            )
        discovery_required = raw_entry.get(
            "subject_discovery_required",
            False,
        )
        if not isinstance(discovery_required, bool):
            raise CapabilityError(
                f"{identifier}: subject_discovery_required должен быть bool",
            )
        review_criteria = raw_entry.get("review_criteria", [])
        if not isinstance(review_criteria, list):
            raise CapabilityError(
                f"{identifier}: review_criteria должен быть массивом",
            )
        seen_criteria: set[str] = set()
        for criterion_index, criterion in enumerate(review_criteria):
            if not isinstance(criterion, dict):
                raise CapabilityError(
                    f"{identifier}: критерий {criterion_index} должен быть объектом",
                )
            criterion_id = require_string(
                criterion,
                "id",
                f"{identifier}: критерий {criterion_index}",
            )
            if criterion_id in seen_criteria:
                raise CapabilityError(
                    f"{identifier}: повторяющийся критерий {criterion_id}",
                )
            seen_criteria.add(criterion_id)
            require_string(
                criterion,
                "description",
                f"{identifier}: критерий {criterion_id}",
            )
            coverage = require_string(
                criterion,
                "coverage",
                f"{identifier}: критерий {criterion_id}",
            )
            if coverage not in CRITERION_COVERAGE:
                raise CapabilityError(
                    f"{identifier}: неизвестный охват критерия {coverage}",
                )
        if review_criteria and participation != "check":
            raise CapabilityError(
                f"{identifier}: review_criteria допустимы только для check",
            )
        if discovery_required and participation != "check":
            raise CapabilityError(
                f"{identifier}: обнаружение области допустимо только для check",
            )
        ontology_scope = raw_entry.get("ontology_scope")
        if ontology_scope is not None:
            node_kinds = (
                ontology_scope.get("node_kinds")
                if isinstance(ontology_scope, dict)
                else None
            )
            if (
                not isinstance(node_kinds, list)
                or not node_kinds
                or not all(isinstance(kind, str) and kind for kind in node_kinds)
            ):
                raise CapabilityError(
                    f"{identifier}: ontology_scope требует node_kinds",
                )
            if participation != "check" or stage is None:
                raise CapabilityError(
                    f"{identifier}: ontology_scope допустима только для проверки этапа",
                )

    missing = sorted(set(actual) - seen_paths)
    if missing:
        raise CapabilityError(
            "нет классификации для компонентов: " + ", ".join(missing),
        )
    orphaned = sorted(seen_paths - set(actual))
    if orphaned:
        raise CapabilityError(
            "классификация ссылается на отсутствующие компоненты: "
            + ", ".join(orphaned),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--classification", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    classification = args.classification
    if classification is None:
        classification = root / DEFAULT_CLASSIFICATION
    try:
        validate(root, classification.resolve())
    except CapabilityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("Project review capabilities OK")


if __name__ == "__main__":
    main()
