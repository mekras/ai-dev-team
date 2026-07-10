#!/usr/bin/env python3
"""Regression tests for the portable corpus operations controller."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".apm" / "skills" / "kc-pipeline" / "scripts" / "run-corpus-operations.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")


def build_corpus(root: Path) -> None:
    write(
        root / "knowledge" / "corpus.yml",
        """
        contract_version: 1
        tracked_data:
          root: data
        local_data:
          local_file_pattern: "*.local.*"
        source_units:
          document:
            unit: document
            path_pattern: data/<source>/documents/<slug>
        indexes:
          items: index/items.yml
          statements: index/statements.yml
        workflow_stages:
          - indexed
          - needs_fetch
          - fetched
          - needs_transcript
          - raw_transcribed
          - normalized
          - statements_extracted
          - source_checked
          - blocked
          - rejected
        """,
    )
    write(
        root / "knowledge" / "catalog.yml",
        """
        sources:
          - id: TEST
            title: "Тестовый источник"
            path: data/test
        """,
    )
    write(
        root / "knowledge" / "data" / "test" / "source.yml",
        """
        id: TEST
        slug: test
        title: "Тестовый источник"
        access:
          default: "Открытый тестовый источник."
        status: active
        carrier_type: document
        source_kind: reference
        adapter: builtin.local-file
        locator: "file:///tmp/test-source.txt"
        reliability: test
        refresh_policy: manual
        """,
    )
    write(
        root / "knowledge" / "data" / "test" / "items.yml",
        """
        items:
          - id: TEST-FETCH
            title: "Нужно получить"
            access: "Открытый тестовый источник."
            status: active
            workflow_stage: needs_fetch
          - id: TEST-NORMALIZED
            title: "Нормализован"
            access: "Открытый тестовый источник."
            status: active
            workflow_stage: normalized
            path: documents/normalized
          - id: TEST-BLOCKED
            title: "Нужен владелец"
            access: "Открытый тестовый источник."
            status: blocked
            workflow_stage: blocked
          - id: TEST-UNKNOWN
            title: "Неизвестная стадия"
            access: "Открытый тестовый источник."
            status: active
            workflow_stage: custom_stage
          - id: TEST-STATEMENTS
            title: "С утверждениями"
            access: "Открытый тестовый источник."
            status: active
            workflow_stage: statements_extracted
            path: documents/statements
        """,
    )
    write(
        root / "knowledge" / "data" / "test" / "documents" / "normalized" / "item.yml",
        """
        id: TEST-NORMALIZED
        title: "Нормализован"
        access: "Открытый тестовый источник."
        status: active
        workflow_stage: normalized
        """,
    )
    write(root / "knowledge" / "data" / "test" / "documents" / "normalized" / "normalized.md", "Тестовый текст.\n")
    write(
        root / "knowledge" / "data" / "test" / "documents" / "statements" / "item.yml",
        """
        id: TEST-STATEMENTS
        title: "С утверждениями"
        access: "Открытый тестовый источник."
        status: active
        workflow_stage: statements_extracted
        """,
    )
    write(
        root / "knowledge" / "data" / "test" / "documents" / "statements" / "statements.yml",
        """
        source_id: TEST
        item_id: TEST-STATEMENTS
        statements:
          - id: TEST-001
            source_id: TEST
            item_id: TEST-STATEMENTS
            status: candidate
            kind: fact
            text: "Тестовое утверждение."
            artifact: normalized.md
            checked_at: 2026-07-10
        """,
    )
    write(
        root / "adapter.py",
        """
        import json
        import sys
        from pathlib import Path

        source_id, locator = sys.argv[1:]
        Path("knowledge/data/test/adapter-marker.yml").write_text("locator: " + locator + "\\n", encoding="utf-8")
        print(json.dumps({
            "contract_version": 1,
            "source_id": source_id,
            "adapter": "builtin.local-file",
            "status": "changed",
            "message": "Паспорт локального файла обновлён.",
            "artifacts": ["knowledge/data/test/adapter-marker.yml"],
        }))
        """,
    )
    write(
        root / "operations.yml",
        f"""
        operations_version: 1
        report:
          path: .local/reports/operations.md
        stages:
          source_sync:
            commands:
              - id: create-marker
                argv:
                  - {sys.executable}
                  - -c
                  - "from pathlib import Path; Path('knowledge/data/test/marker.txt').write_text('ok', encoding='utf-8')"
                working_directory: .
                write_paths:
                  - knowledge/data/test
                required: true
        adapters:
          builtin.local-file:
            argv:
              - {sys.executable}
              - adapter.py
              - "{{source_id}}"
              - "{{locator}}"
            working_directory: .
            write_paths:
              - knowledge/data/test
        """,
    )


def run(root: Path, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "knowledge", "--operations", "operations.yml", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"Ожидался код {expected}, получен {result.returncode}.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        build_corpus(root)
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)

        plan = run(root)
        for expected_line in ("- fetch: 1", "- statements: 1", "- source_check: 1", "- human_decision: 2"):
            if expected_line not in plan.stdout:
                raise AssertionError(f"В плане нет строки: {expected_line}")
        if (root / ".local").exists() or (root / "knowledge" / "index").exists():
            raise AssertionError("Планирование без параметров не должно записывать файлы.")

        run(root, "--rebuild-indexes", "--write-report")
        items_index = (root / "knowledge" / "index" / "items.yml").read_text(encoding="utf-8")
        statements_index = (root / "knowledge" / "index" / "statements.yml").read_text(encoding="utf-8")
        report = (root / ".local" / "reports" / "operations.md").read_text(encoding="utf-8")
        if "TEST-NORMALIZED" not in items_index or "TEST-001" not in statements_index:
            raise AssertionError("Пересобранные индексы не содержат исходные записи.")
        if "# Операционный отчёт корпуса" not in report:
            raise AssertionError("Локальный отчёт не записан.")

        marker = root / "knowledge" / "data" / "test" / "marker.txt"
        if marker.exists():
            raise AssertionError("Команды нельзя выполнять без --run-commands.")
        run(root, "--run-commands")
        if marker.read_text(encoding="utf-8") != "ok":
            raise AssertionError("Явно разрешённая команда не выполнилась.")

        adapter_marker = root / "knowledge" / "data" / "test" / "adapter-marker.yml"
        adapters = run(root, "--run-adapters", "--source", "TEST")
        if "TEST (builtin.local-file): changed" not in adapters.stdout or not adapter_marker.is_file():
            raise AssertionError("Исполняемый адаптер не вернул структурированный результат.")

        source_path = root / "knowledge" / "data" / "test" / "source.yml"
        source_path.write_text(
            source_path.read_text(encoding="utf-8").replace("adapter: builtin.local-file", "adapter: project.unknown"),
            encoding="utf-8",
        )
        unsupported = run(root, "--run-adapters")
        if "TEST (project.unknown): unsupported-adapter" not in unsupported.stdout:
            raise AssertionError("Неизвестный адаптер не получил явный статус.")
        source_path.write_text(
            source_path.read_text(encoding="utf-8").replace("adapter: project.unknown", "adapter: builtin.local-file"),
            encoding="utf-8",
        )
        operations_path = root / "operations.yml"
        operations_path.write_text(
            operations_path.read_text(encoding="utf-8") + "\ntoken: secret-value\n",
            encoding="utf-8",
        )
        secret = run(root, "--run-adapters", expected=2)
        if "поле с секретом" not in secret.stderr:
            raise AssertionError("Настройки с явным секретом не были отклонены.")
        operations_path.write_text(
            operations_path.read_text(encoding="utf-8").replace("\ntoken: secret-value\n", "\n"),
            encoding="utf-8",
        )

        write(root / "knowledge" / "data" / "test" / "source-contact.md", "Контакт источника: +7 (999) 123-45-67\n")
        write(root / "knowledge" / "data" / "test" / "leak.md", "api_key=super-secret-value\n")
        write(root / "knowledge" / "data" / "test" / "leak.local.md", "api_key=local-secret-value\n")
        source_path.write_text(
            source_path.read_text(encoding="utf-8") + "contact: source@example.test\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        marker.unlink()
        checked = run(root, "--operational-check", "--run-commands", expected=1)
        if "блокеры доступа: 1" not in checked.stdout or "super-secret-value" in checked.stdout:
            raise AssertionError("Операционная проверка не обезличила блокер доступа.")
        if marker.exists():
            raise AssertionError("Блокер доступа не остановил команду до записи.")
        if "предупреждения качества: 1" not in checked.stdout:
            raise AssertionError("Содержательные контактные данные не стали предупреждением качества.")

        write(
            root / "knowledge" / "operational-check.yml",
            """
            rules:
              - kind: access-secret
                path: data/test/leak.md
                action: suppress
                reason: "Тестовый маркер ложного срабатывания."
            """,
        )
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        suppressed = run(
            root,
            "--operational-check",
            "--operational-policy",
            "knowledge/operational-check.yml",
            expected=1,
        )
        if "блокеры доступа: 0" not in suppressed.stdout or "подавлено правилом или метаданными: 2" not in suppressed.stdout:
            raise AssertionError("Документированное подавление не применилось.")

        items_path = root / "knowledge" / "data" / "test" / "items.yml"
        items_path.write_text(
            items_path.read_text(encoding="utf-8").replace(
                "path: documents/normalized",
                "path: ../outside",
                1,
            ),
            encoding="utf-8",
        )
        rejected = run(root, expected=2)
        if "относительным путём внутри корпуса" not in rejected.stderr:
            raise AssertionError("Выход за пределы источника не был отклонён.")

    print("Проверки операционного контура корпуса прошли.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
