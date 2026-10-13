#!/usr/bin/env python3
"""Проверить, что производные указатели корпуса знаний собраны из данных.

Указатели `index/items.yml` и `index/statements.yml` выводятся из
`data/*/items.yml` и не ведутся как самостоятельный источник. Пересобирает их
переносимое средство корпуса `kc-pipeline`, поэтому здесь нет второй реализации
договора: скрипт вызывает то же средство и сравнивает результат с тем, что
лежит в репозитории.

Рабочим каталогом при вызове должен быть корень проекта: средство проверяет
допуск источников по решениям, хранящимся за пределами корпуса. Адреса
утверждений в указателе остаются относительными к корню корпуса.

Валидатор раскладки сверяет с данными только указатель единиц. Расхождение
указателя утверждений он не обнаруживает, и эту проверку закрывает данный
скрипт.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
REBUILD_TOOL = (
    ROOT / ".agents" / "skills" / "kc-pipeline" / "scripts" / "run-corpus-operations.py"
)
INDEX_FILES = ("items.yml", "statements.yml")


def snapshot(index_dir: Path) -> dict[Path, str | None]:
    saved: dict[Path, str | None] = {}
    for name in INDEX_FILES:
        path = index_dir / name
        saved[path] = path.read_text(encoding="utf-8") if path.exists() else None
    return saved


def restore(saved: dict[Path, str | None]) -> None:
    for path, content in saved.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(content, encoding="utf-8")


def rebuild(corpus_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REBUILD_TOOL), corpus_root.name, "--rebuild-indexes"],
        cwd=corpus_root.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def normalize_statement_paths(index: Path, corpus_name: str) -> None:
    if not index.is_file():
        return
    content = index.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?m)^(  path: ){re.escape(corpus_name)}/")
    normalized = pattern.sub(r"\1", content)
    if normalized != content:
        index.write_text(normalized, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Сверить производные указатели корпуса знаний с данными.",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=KNOWLEDGE,
        help="корень корпуса знаний (по умолчанию knowledge)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="оставить пересобранные указатели вместо восстановления прежних",
    )
    args = parser.parse_args(argv)

    corpus_root = args.corpus_root
    if not (corpus_root / "corpus.yml").is_file():
        print(f"ERROR: не найден договор корпуса: {corpus_root / 'corpus.yml'}")
        return 2
    if not REBUILD_TOOL.is_file():
        print(f"ERROR: не найдено переносимое средство корпуса: {REBUILD_TOOL}")
        print("Выполните apm install --frozen и повторите проверку.")
        return 2

    index_dir = corpus_root / "index"
    saved = snapshot(index_dir)

    result = rebuild(corpus_root)
    if result.returncode != 0:
        restore(saved)
        print("ERROR: переносимая пересборка указателей завершилась с ошибкой.")
        print(result.stderr.strip() or result.stdout.strip())
        return 2

    normalize_statement_paths(index_dir / "statements.yml", corpus_root.name)

    drifted = []
    for path, content in saved.items():
        rebuilt = path.read_text(encoding="utf-8") if path.exists() else None
        if rebuilt != content:
            drifted.append(path.name)

    if not drifted:
        print("Проверка указателей корпуса: расхождений с данными нет.")
        return 0

    if args.write:
        print(f"Указатели пересобраны из данных: {', '.join(drifted)}.")
        return 0

    restore(saved)
    print(f"DRIFT: указатели разошлись с данными корпуса: {', '.join(drifted)}.")
    print(
        "Пересоберите их командой "
        "python3 tools/check-knowledge-index.py --write и проверьте различия."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
