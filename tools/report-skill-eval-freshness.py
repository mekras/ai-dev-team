#!/usr/bin/env python3
"""Сообщить, что сценарий качества результата не исполнялся дольше срока.

Не блокирует изменение: регистрация сценария и успешная структурная проверка
не доказывают, что сценарий когда-либо реально прогонялся через модель.
Основание: docs/06-architecture/adr/0013-product-evidence-levels.md, раздел
«Решение» пункт 4 и раздел «Проверка» (вариант 6 — учёт давности фактического
исполнения).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator

for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD_PATH = REPO_ROOT / ".ai-dev-team" / "skill-eval-runs.json"
DEFAULT_THRESHOLD_DAYS = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Сообщить о сценариях результата, которые не исполнялись дольше "
            "установленного срока, или никогда не исполнялись."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Каталоги навыков или корни для обхода. По умолчанию .apm/skills.",
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=DEFAULT_RECORD_PATH,
        help="Путь к хранимой записи о прогонах.",
    )
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=DEFAULT_THRESHOLD_DAYS,
        help=f"Срок давности в днях. По умолчанию {DEFAULT_THRESHOLD_DAYS}.",
    )
    parser.add_argument(
        "--today",
        type=str,
        default=None,
        help="Дата сравнения в формате ISO (YYYY-MM-DD). По умолчанию сегодня.",
    )
    return parser.parse_args()


def collect_skill_dirs(root: Path) -> Iterator[Path]:
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


def collect_case_ids(skill_dirs: list[Path]) -> dict[str, str]:
    """Вернуть {case_id: имя навыка}."""
    case_ids: dict[str, str] = {}
    for skill_dir in skill_dirs:
        result_path = skill_dir / "evals" / "result-scenarios.json"
        if not result_path.exists():
            continue
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cases = data.get("cases") if isinstance(data, dict) else None
        if not isinstance(cases, list):
            continue
        skill_name = data.get("skill_name") if isinstance(data, dict) else None
        for case in cases:
            if isinstance(case, dict) and isinstance(case.get("id"), str):
                case_ids[case["id"]] = skill_name or skill_dir.name
    return case_ids


def load_record(record_path: Path) -> dict[str, str]:
    if not record_path.exists():
        return {}
    data = json.loads(record_path.read_text(encoding="utf-8"))
    runs = data.get("runs")
    return dict(runs) if isinstance(runs, dict) else {}


def main() -> int:
    args = parse_args()
    roots = args.paths or [REPO_ROOT / ".apm" / "skills"]
    skill_dirs = find_skill_dirs(roots)
    case_ids = collect_case_ids(skill_dirs)
    runs = load_record(args.record)

    if args.today is not None:
        today = date.fromisoformat(args.today)
    else:
        today = datetime.now(timezone.utc).date()

    never_run: list[str] = []
    stale: list[tuple[str, str, int]] = []
    for case_id, skill_name in sorted(case_ids.items()):
        last_run = runs.get(case_id)
        if last_run is None:
            never_run.append(f"{skill_name}: {case_id}")
            continue
        age_days = (today - date.fromisoformat(last_run)).days
        if age_days > args.threshold_days:
            stale.append((skill_name, case_id, age_days))

    if never_run:
        print(f"Никогда не исполнялись ({len(never_run)}):")
        for line in never_run:
            print(f"  {line}")

    if stale:
        print(
            f"Не исполнялись дольше {args.threshold_days} дней "
            f"({len(stale)}):",
        )
        for skill_name, case_id, age_days in stale:
            print(f"  {skill_name}: {case_id} — {age_days} дн.")

    if not never_run and not stale:
        print(
            "Все сценарии результата исполнялись в пределах "
            f"{args.threshold_days} дней.",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
