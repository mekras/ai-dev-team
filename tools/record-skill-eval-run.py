#!/usr/bin/env python3
"""Записать дату прогона сценариев качества результата навыков.

Вызывается после успешного `apm run evals`, чтобы обновить хранимую запись о
прогонах для `tools/report-skill-eval-freshness.py`. Основание:
docs/06-architecture/adr/0013-product-evidence-levels.md, раздел «Решение»
пункт 4 (вариант 6 — учёт давности фактического исполнения).
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Отметить сегодняшним днём прогон сценариев результата.",
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
        "--today",
        type=str,
        default=None,
        help="Дата прогона в формате ISO (YYYY-MM-DD). По умолчанию сегодня.",
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


def collect_case_ids(skill_dirs: list[Path]) -> set[str]:
    case_ids: set[str] = set()
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
        for case in cases:
            if isinstance(case, dict) and isinstance(case.get("id"), str):
                case_ids.add(case["id"])
    return case_ids


def load_record(record_path: Path) -> dict[str, str]:
    if not record_path.exists():
        return {}
    data = json.loads(record_path.read_text(encoding="utf-8"))
    runs = data.get("runs")
    return dict(runs) if isinstance(runs, dict) else {}


def save_record(record_path: Path, runs: dict[str, str]) -> None:
    record_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "runs": dict(sorted(runs.items()))}
    record_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    roots = args.paths or [REPO_ROOT / ".apm" / "skills"]
    skill_dirs = find_skill_dirs(roots)
    case_ids = collect_case_ids(skill_dirs)

    if args.today is not None:
        today = date.fromisoformat(args.today)
    else:
        today = datetime.now(timezone.utc).date()

    runs = load_record(args.record)
    for case_id in case_ids:
        runs[case_id] = today.isoformat()
    save_record(args.record, runs)

    print(f"Записан прогон {today.isoformat()} для {len(case_ids)} сценариев.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
