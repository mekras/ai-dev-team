#!/usr/bin/env python3
"""Сверяет предметные роли продукта с локальными маршрутами подагентов."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(root: Path) -> int:
    config = root / ".ai-dev-team/local/subagents.local.toml"
    try:
        stream = config.open("rb")
    except FileNotFoundError:
        print("Сверка маршрутов подагентов пропущена: локальной настройки нет.")
        return 0
    except OSError as error:
        print(f"Не удалось открыть локальную настройку: {error}", file=sys.stderr)
        return 1

    try:
        with stream:
            policy = tomllib.load(stream)
        runtime = policy.get("policy_runtime", {})
        assignments = policy.get("roles", {})
        if not isinstance(runtime, dict) or not isinstance(assignments, dict):
            raise ValueError("policy_runtime и roles должны быть таблицами TOML")
        if not all(isinstance(assignment, dict) for assignment in assignments.values()):
            raise ValueError("каждое назначение в roles должно быть таблицей TOML")

        routes = runtime.get("routes", [])
        if not isinstance(routes, list) or not all(isinstance(route, dict) for route in routes):
            raise ValueError("policy_runtime.routes должен быть списком таблиц TOML")
        named_routes = [route["role"] for route in routes if "role" in route]
        if not all(isinstance(name, str) and name.strip() for name in named_routes):
            raise ValueError("имя роли в маршруте должно быть непустой строкой")

        product_roles = {
            path.name.removesuffix(".agent.md")
            for path in (root / ".apm/agents").iterdir()
            if path.name.endswith(".agent.md") and path.is_file()
        }
    except (OSError, ValueError) as error:
        print(f"Не удалось сверить маршруты подагентов: {error}", file=sys.stderr)
        return 1

    routed_roles = set(named_routes)
    local_roles = {
        name for name, assignment in assignments.items()
        if assignment.get("local_only") is True
    }
    product_routes = (routed_roles & assignments.keys()) - local_roles
    unrouted_roles = product_roles - product_routes - {"project-manager"}
    findings = (
        ("Предметные роли без настроенного маршрута", unrouted_roles),
        ("Маршруты к ролям, которых нет в продукте", routed_roles - product_roles - local_roles),
        ("Именованные маршруты без назначения", routed_roles - assignments.keys()),
    )
    for label, names in findings:
        if names:
            print(f"{label}: {', '.join(sorted(names))}.")
    if not any(names for _, names in findings):
        print("Локальные маршруты подагентов соответствуют составу ролей продукта.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check(ROOT))
