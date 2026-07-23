#!/usr/bin/env python3
"""Reject generated Python artifacts recorded in tracked APM lockfiles."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment failure
    raise SystemExit("Для проверки файлов блокировки нужен PyYAML.") from exc


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(key)
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def is_generated_python_artifact(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return "__pycache__" in path.parts or path.suffix == ".pyc"


def scan_lockfile(path: Path) -> list[str]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"{path}: файл блокировки не прочитан: {exc}") from exc

    return sorted(
        {
            value
            for value in iter_strings(data)
            if is_generated_python_artifact(value)
        }
    )


def tracked_lockfiles() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "apm.lock.yaml", "*/apm.lock.yaml"],
        check=True,
        capture_output=True,
    )
    return [
        Path(item.decode())
        for item in result.stdout.split(b"\0")
        if item
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Проверить файлы apm.lock.yaml на __pycache__ и байткод Python."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Проверяемые файлы. По умолчанию отслеживаемые apm.lock.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = args.paths or tracked_lockfiles()
    errors: list[str] = []

    for path in paths:
        try:
            artifacts = scan_lockfile(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for artifact in artifacts:
            errors.append(
                f"{path}: файл блокировки содержит генерируемый артефакт: "
                f"{artifact}",
            )

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"Файлы блокировки не содержат артефактов Python: {len(paths)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
