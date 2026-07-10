#!/usr/bin/env python3
"""Plan corpus work, run explicitly configured commands, and rebuild indexes.

The script supports the optional portable corpus layout. Project-specific
adapters remain project code: this controller only reads their declarative
commands and never invokes them unless --run-commands is given.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the target project environment.
    yaml = None


DEFAULT_NORMALIZED_ARTIFACTS = ("normalized.md", "message.md", "stenogram.txt")
QUEUE_ORDER = ("fetch", "transcribe", "normalize", "statements", "source_check", "human_decision")
ADAPTER_STATUSES = {
    "synced",
    "partial",
    "changed",
    "unchanged",
    "new",
    "removed",
    "manual-required",
    "access-limited",
    "fetch-error",
    "unsupported-adapter",
    "invalid-registry",
}
SENSITIVE_SETTING_NAMES = {"token", "password", "cookie", "secret", "authorization", "api_key", "apikey"}


class OperationsError(RuntimeError):
    """The project operations contract or its observable state is invalid."""


@dataclass(frozen=True)
class CorpusItem:
    source_id: str
    source_dir: Path
    index_item: dict[str, Any]
    item_dir: Path | None
    item_card: dict[str, Any] | None

    def value(self, key: str, default: Any = None) -> Any:
        if self.item_card is not None and key in self.item_card:
            return self.item_card[key]
        return self.index_item.get(key, default)

    @property
    def item_id(self) -> str:
        value = self.value("id")
        return value if isinstance(value, str) else "<unknown>"

    @property
    def stage(self) -> str:
        value = self.value("workflow_stage")
        return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class CorpusSource:
    source_id: str
    source_dir: Path
    card: dict[str, Any]

    @property
    def adapter(self) -> str:
        value = self.card.get("adapter")
        return value if isinstance(value, str) else ""

    @property
    def locator(self) -> str:
        value = self.card.get("locator", self.card.get("url", ""))
        return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    returncode: int
    changed_paths: tuple[str, ...]
    output: str


@dataclass(frozen=True)
class AdapterResult:
    source_id: str
    adapter: str
    status: str
    message: str
    changed_paths: tuple[str, ...]


@dataclass(frozen=True)
class OperationalCheckResult:
    returncode: int
    contract_errors: tuple[str, ...]
    blockers: tuple[dict[str, Any], ...]
    quality_warnings: tuple[dict[str, Any], ...]
    suppressed: tuple[dict[str, Any], ...]


def require_yaml() -> None:
    if yaml is None:
        raise OperationsError("Для работы нужен пакет PyYAML.")


def load_yaml(path: Path) -> Any:
    require_yaml()
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OperationsError(f"Не удалось прочитать {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise OperationsError(f"Файл YAML содержит ошибку: {path}: {exc}") from exc


def dump_yaml_atomically(path: Path, data: Any) -> None:
    require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(rendered)
        temporary_path = Path(stream.name)
    try:
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def repo_relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise OperationsError(f"Путь выходит за пределы проекта: {path}") from exc


def resolve_inside(root: Path, raw_path: str, label: str) -> Path:
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise OperationsError(f"{label} выходит за пределы проекта: {raw_path}") from exc
    return candidate


def relative_path(raw_path: str, label: str) -> PurePosixPath:
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise OperationsError(f"{label} должен быть относительным путём внутри корпуса: {raw_path}")
    return path


def corpus_paths(corpus_root: Path) -> tuple[Path, Path, Path]:
    contract_path = corpus_root / "corpus.yml"
    catalog_path = corpus_root / "catalog.yml"
    if not contract_path.is_file() or not catalog_path.is_file():
        raise OperationsError("В корне корпуса нужны corpus.yml и catalog.yml.")
    contract = load_yaml(contract_path)
    if not isinstance(contract, dict):
        raise OperationsError("corpus.yml должен быть словарём YAML.")
    tracked_data = contract.get("tracked_data")
    if not isinstance(tracked_data, dict) or not isinstance(tracked_data.get("root"), str):
        raise OperationsError("corpus.yml должен задавать tracked_data.root.")
    return contract_path, catalog_path, corpus_root / tracked_data["root"]


def source_directories(corpus_root: Path) -> list[Path]:
    _, _, data_root = corpus_paths(corpus_root)
    if not data_root.exists():
        return []
    return sorted(path.parent for path in data_root.glob("*/source.yml"))


def load_sources(corpus_root: Path) -> list[CorpusSource]:
    sources: list[CorpusSource] = []
    for source_dir in source_directories(corpus_root):
        source = load_yaml(source_dir / "source.yml")
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise OperationsError(f"Карточка источника должна задавать строковый id: {source_dir / 'source.yml'}")
        sources.append(CorpusSource(source["id"], source_dir, source))
    return sources


def load_items(corpus_root: Path) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    for source_dir in source_directories(corpus_root):
        source = load_yaml(source_dir / "source.yml")
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            continue
        source_items_path = source_dir / "items.yml"
        if not source_items_path.is_file():
            continue
        source_items = load_yaml(source_items_path)
        rows = source_items.get("items") if isinstance(source_items, dict) else None
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_dir: Path | None = None
            item_card: dict[str, Any] | None = None
            raw_item_path = row.get("path")
            if isinstance(raw_item_path, str):
                item_dir = source_dir / relative_path(raw_item_path, "path единицы")
                item_path = item_dir / "item.yml"
                if item_path.is_file():
                    loaded = load_yaml(item_path)
                    if isinstance(loaded, dict):
                        item_card = loaded
            items.append(CorpusItem(source["id"], source_dir, row, item_dir, item_card))
    return items


def load_operations(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise OperationsError("Файл настроек операций должен быть словарём YAML.")
    version = data.get("operations_version")
    if version != 1:
        raise OperationsError("Поддерживается только operations_version: 1.")
    reject_sensitive_settings(data)
    return data


def reject_sensitive_settings(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower().replace("-", "_") in SENSITIVE_SETTING_NAMES:
                raise OperationsError(f"В настройках операций запрещено поле с секретом: {path}{key}")
            reject_sensitive_settings(child, f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_settings(child, f"{path}{index}.")
    elif isinstance(value, str) and ("?token=" in value.lower() or "authorization:" in value.lower()):
        raise OperationsError(f"В настройках операций найдено значение, похожее на секрет: {path.rstrip('.')}")


def normalized_artifacts(operations: dict[str, Any]) -> tuple[str, ...]:
    value = operations.get("normalized_artifacts")
    if value is None:
        return DEFAULT_NORMALIZED_ARTIFACTS
    if not isinstance(value, list) or not value or not all(isinstance(name, str) and name for name in value):
        raise OperationsError("normalized_artifacts должен быть непустым списком имён файлов.")
    return tuple(value)


def has_normalized_artifact(item: CorpusItem, names: tuple[str, ...]) -> bool:
    return bool(item.item_dir and any((item.item_dir / name).is_file() for name in names))


def has_raw_transcript(item: CorpusItem) -> bool:
    return bool(item.item_dir and (item.item_dir / "transcript.txt").is_file())


def has_statements(item: CorpusItem) -> bool:
    return bool(item.item_dir and (item.item_dir / "statements.yml").is_file())


def queue_name(item: CorpusItem, normalized_names: tuple[str, ...]) -> tuple[str, str] | None:
    stage = item.stage
    if stage == "needs_fetch":
        return "fetch", "workflow_stage=needs_fetch"
    if stage == "indexed" and item.value("processing_scope") == "full" and item.item_dir is None:
        return "fetch", "полная обработка без локальной папки единицы"
    if stage == "needs_transcript":
        if has_statements(item):
            return "source_check", "утверждения уже есть, требуется сверка стадии"
        if has_normalized_artifact(item, normalized_names):
            return "statements", "подготовленный артефакт уже есть"
        if has_raw_transcript(item):
            return "normalize", "сырая расшифровка уже есть"
        return "transcribe", "workflow_stage=needs_transcript"
    if stage in {"fetched", "raw_transcribed"}:
        return "normalize", f"workflow_stage={stage}"
    if stage == "normalized":
        return ("source_check", "утверждения уже есть, требуется сверка стадии") if has_statements(item) else (
            "statements",
            "материал нормализован, утверждения отсутствуют",
        )
    if stage == "statements_extracted":
        return "source_check", "workflow_stage=statements_extracted"
    if stage == "blocked":
        return "human_decision", "workflow_stage=blocked"
    if stage in {"source_checked", "rejected", ""}:
        return None
    return "human_decision", f"неизвестная или неподдерживаемая стадия: {stage}"


def build_queues(items: list[CorpusItem], normalized_names: tuple[str, ...], root: Path) -> dict[str, list[dict[str, str]]]:
    queues = {name: [] for name in QUEUE_ORDER}
    for item in items:
        result = queue_name(item, normalized_names)
        if result is None:
            continue
        name, reason = result
        relative_path = repo_relative(root, item.item_dir) if item.item_dir else ""
        queues[name].append(
            {
                "id": item.item_id,
                "source_id": item.source_id,
                "path": relative_path,
                "title": str(item.value("title", "")),
                "reason": reason,
            }
        )
    return queues


def index_paths(corpus_root: Path) -> tuple[Path, Path]:
    contract = load_yaml(corpus_root / "corpus.yml")
    indexes = contract.get("indexes") if isinstance(contract, dict) else None
    if not isinstance(indexes, dict):
        return corpus_root / "index" / "items.yml", corpus_root / "index" / "statements.yml"
    items = indexes.get("items", "index/items.yml")
    statements = indexes.get("statements", "index/statements.yml")
    if not isinstance(items, str) or not isinstance(statements, str):
        raise OperationsError("Пути indexes.items и indexes.statements должны быть строками.")
    return corpus_root / relative_path(items, "indexes.items"), corpus_root / relative_path(
        statements,
        "indexes.statements",
    )


def rebuild_indexes(corpus_root: Path, root: Path) -> tuple[int, int]:
    item_rows: list[dict[str, Any]] = []
    statement_rows: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    seen_statement_ids: set[str] = set()
    for item in load_items(corpus_root):
        item_id = item.index_item.get("id")
        if not isinstance(item_id, str):
            raise OperationsError("В индексе источника найдена единица без строкового id.")
        if item_id in seen_item_ids:
            raise OperationsError(f"Повторяющийся id единицы: {item_id}")
        seen_item_ids.add(item_id)
        path = repo_relative(root, item.item_dir) if item.item_dir else None
        item_rows.append(
            {
                "id": item_id,
                "source_id": item.source_id,
                "path": path,
                "title": item.index_item.get("title"),
                "date_published": item.index_item.get("date_published"),
                "workflow_stage": item.index_item.get("workflow_stage"),
                "access": item.index_item.get("access"),
            }
        )
        if not item.item_dir or not (item.item_dir / "statements.yml").is_file():
            continue
        data = load_yaml(item.item_dir / "statements.yml")
        statements = data.get("statements") if isinstance(data, dict) else None
        if not isinstance(statements, list):
            raise OperationsError(f"statements.yml должен содержать список statements: {item.item_id}")
        for statement in statements:
            if not isinstance(statement, dict) or not isinstance(statement.get("id"), str):
                raise OperationsError(f"В statements.yml найдена запись без строкового id: {item.item_id}")
            statement_id = statement["id"]
            if statement_id in seen_statement_ids:
                raise OperationsError(f"Повторяющийся id утверждения: {statement_id}")
            seen_statement_ids.add(statement_id)
            statement_rows.append(
                {
                    "id": statement_id,
                    "source_id": statement.get("source_id", item.source_id),
                    "item_id": statement.get("item_id", item.item_id),
                    "path": repo_relative(root, item.item_dir / "statements.yml"),
                    "status": statement.get("status"),
                    "kind": statement.get("kind"),
                    "text": statement.get("text"),
                    "artifact": statement.get("artifact"),
                    "checked_at": statement.get("checked_at"),
                }
            )
    items_path, statements_path = index_paths(corpus_root)
    dump_yaml_atomically(items_path, {"items": item_rows})
    dump_yaml_atomically(statements_path, {"statements": statement_rows})
    return len(item_rows), len(statement_rows)


def git_status_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=root,
        capture_output=True,
        text=False,
    )
    if result.returncode != 0:
        raise OperationsError("Для --run-commands проект должен быть рабочей областью Git.")
    paths: set[str] = set()
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        text = record.decode("utf-8", errors="replace")
        if len(text) >= 4:
            paths.add(text[3:])
    return paths


def configured_commands(operations: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    stages = operations.get("stages")
    if not isinstance(stages, dict):
        return []
    stage_data = stages.get(stage)
    if not isinstance(stage_data, dict):
        return []
    commands = stage_data.get("commands", [])
    if not isinstance(commands, list):
        raise OperationsError(f"stages.{stage}.commands должен быть списком.")
    return [command for command in commands if isinstance(command, dict)]


def command_paths_allowed(paths: set[str], allowed_prefixes: list[str]) -> bool:
    return all(any(path == prefix or path.startswith(f"{prefix}/") for prefix in allowed_prefixes) for path in paths)


def run_commands(root: Path, operations: dict[str, Any], stage: str) -> list[CommandResult]:
    results: list[CommandResult] = []
    for position, command in enumerate(configured_commands(operations, stage), start=1):
        command_id = command.get("id")
        argv = command.get("argv")
        write_paths = command.get("write_paths")
        cwd = command.get("working_directory", ".")
        if not isinstance(command_id, str) or not command_id:
            raise OperationsError(f"Команда #{position} должна иметь непустой id.")
        if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
            raise OperationsError(f"Команда {command_id} должна задавать непустой argv.")
        if not isinstance(write_paths, list) or not write_paths or not all(isinstance(path, str) and path for path in write_paths):
            raise OperationsError(f"Команда {command_id} должна задавать write_paths.")
        if not isinstance(cwd, str):
            raise OperationsError(f"Команда {command_id} должна задавать working_directory строкой.")
        for path in write_paths:
            resolve_inside(root, path, f"write_paths команды {command_id}")
        command_cwd = resolve_inside(root, cwd, f"working_directory команды {command_id}")
        before = git_status_paths(root)
        process = subprocess.run(argv, cwd=command_cwd, capture_output=True, text=True)
        after = git_status_paths(root)
        changed = after - before
        if not command_paths_allowed(changed, write_paths):
            paths = ", ".join(sorted(changed)) or "нет"
            raise OperationsError(f"Команда {command_id} изменила файлы вне write_paths: {paths}")
        output = "\n".join(part for part in (process.stdout.strip(), process.stderr.strip()) if part)
        results.append(CommandResult(command_id, process.returncode, tuple(sorted(changed)), output))
        if process.returncode != 0 and command.get("required", True):
            break
    return results


def adapter_definitions(operations: dict[str, Any]) -> dict[str, dict[str, Any]]:
    adapters = operations.get("adapters", {})
    if not isinstance(adapters, dict):
        raise OperationsError("adapters должен быть словарём определений адаптеров.")
    definitions: dict[str, dict[str, Any]] = {}
    for name, definition in adapters.items():
        if not isinstance(name, str) or not name or not isinstance(definition, dict):
            raise OperationsError("Каждый адаптер должен иметь строковое имя и словарь настроек.")
        definitions[name] = definition
    return definitions


def format_adapter_argv(argv: list[str], source: CorpusSource, root: Path) -> list[str]:
    values = {
        "source_id": source.source_id,
        "source_dir": repo_relative(root, source.source_dir),
        "locator": source.locator,
    }
    try:
        return [part.format(**values) for part in argv]
    except KeyError as exc:
        raise OperationsError(f"В argv адаптера используется неизвестный параметр: {exc.args[0]}") from exc


def validate_adapter_result(data: Any, source: CorpusSource, changed_paths: set[str]) -> AdapterResult:
    if not isinstance(data, dict):
        raise OperationsError(f"Адаптер {source.adapter} источника {source.source_id} должен вернуть JSON-объект.")
    if data.get("contract_version") != 1:
        raise OperationsError(f"Адаптер {source.adapter} источника {source.source_id} вернул неподдерживаемую версию договора.")
    if data.get("source_id") != source.source_id or data.get("adapter") != source.adapter:
        raise OperationsError(f"Адаптер {source.adapter} вернул результат для другого источника.")
    status = data.get("status")
    message = data.get("message")
    if status not in ADAPTER_STATUSES or not isinstance(message, str) or not message:
        raise OperationsError(f"Адаптер {source.adapter} источника {source.source_id} вернул неполный статус.")
    artifacts = data.get("artifacts", [])
    if not isinstance(artifacts, list) or not all(isinstance(path, str) for path in artifacts):
        raise OperationsError(f"Адаптер {source.adapter} источника {source.source_id} вернул неверный список artifacts.")
    return AdapterResult(source.source_id, source.adapter, status, message, tuple(sorted(changed_paths)))


def run_adapters(root: Path, corpus_root: Path, operations: dict[str, Any], selected_ids: set[str]) -> list[AdapterResult]:
    definitions = adapter_definitions(operations)
    sources = load_sources(corpus_root)
    known_ids = {source.source_id for source in sources}
    unknown_ids = selected_ids - known_ids
    if unknown_ids:
        raise OperationsError(f"Не найден источник для --source: {', '.join(sorted(unknown_ids))}")
    results: list[AdapterResult] = []
    for source in sources:
        if selected_ids and source.source_id not in selected_ids:
            continue
        definition = definitions.get(source.adapter)
        if definition is None:
            results.append(AdapterResult(source.source_id, source.adapter, "unsupported-adapter", "Адаптер не зарегистрирован в настройках операций.", ()))
            continue
        argv = definition.get("argv")
        write_paths = definition.get("write_paths")
        cwd = definition.get("working_directory", ".")
        if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
            raise OperationsError(f"Адаптер {source.adapter} должен задавать непустой argv.")
        if not isinstance(write_paths, list) or not write_paths or not all(isinstance(path, str) and path for path in write_paths):
            raise OperationsError(f"Адаптер {source.adapter} должен задавать write_paths.")
        if not isinstance(cwd, str):
            raise OperationsError(f"Адаптер {source.adapter} должен задавать working_directory строкой.")
        for path in write_paths:
            resolve_inside(root, path, f"write_paths адаптера {source.adapter}")
        command_cwd = resolve_inside(root, cwd, f"working_directory адаптера {source.adapter}")
        before = git_status_paths(root)
        process = subprocess.run(format_adapter_argv(argv, source, root), cwd=command_cwd, capture_output=True, text=True)
        after = git_status_paths(root)
        changed = after - before
        if not command_paths_allowed(changed, write_paths):
            paths = ", ".join(sorted(changed)) or "нет"
            raise OperationsError(f"Адаптер {source.adapter} изменил файлы вне write_paths: {paths}")
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or f"Команда завершилась с кодом {process.returncode}."
            results.append(AdapterResult(source.source_id, source.adapter, "fetch-error", message, tuple(sorted(changed))))
            continue
        try:
            result_data = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise OperationsError(f"Адаптер {source.adapter} источника {source.source_id} вернул не JSON: {exc.msg}") from exc
        results.append(validate_adapter_result(result_data, source, changed))
    return results


def run_operational_check(
    root: Path, corpus_root: Path, policy: Path | None
) -> OperationalCheckResult:
    validator = Path(__file__).resolve().parents[2] / "kc-inventory" / "scripts" / "validate-corpus-layout.py"
    argv = [sys.executable, str(validator), str(corpus_root), "--operational", "--output", "json"]
    if policy is not None:
        argv.extend(["--operational-policy", repo_relative(corpus_root, policy)])
    process = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise OperationsError(f"Операционная проверка корпуса не вернула JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise OperationsError("Операционная проверка корпуса вернула неверный JSON.")
    def findings(name: str) -> tuple[dict[str, Any], ...]:
        value = data.get(name, [])
        if not isinstance(value, list) or not all(isinstance(entry, dict) for entry in value):
            raise OperationsError(f"Операционная проверка вернула неверное поле {name}.")
        return tuple(value)
    errors = data.get("contract_errors", [])
    if not isinstance(errors, list) or not all(isinstance(entry, str) for entry in errors):
        raise OperationsError("Операционная проверка вернула неверные ошибки договора.")
    return OperationalCheckResult(process.returncode, tuple(errors), findings("blockers"), findings("quality_warnings"), findings("suppressed"))


def render_report(
    corpus_root: Path,
    queues: dict[str, list[dict[str, str]]],
    command_results: list[CommandResult],
    index_counts: tuple[int, int] | None,
    adapter_results: list[AdapterResult] | None = None,
    operational_check: OperationalCheckResult | None = None,
) -> str:
    lines = [
        "# Операционный отчёт корпуса",
        "",
        f"Создан: {datetime.now(UTC).isoformat()}",
        f"Корень корпуса: {corpus_root}",
        "",
        "## Очереди",
        "",
    ]
    for name in QUEUE_ORDER:
        entries = queues[name]
        lines.append(f"- {name}: {len(entries)}")
        for entry in entries[:10]:
            location = f" ({entry['path']})" if entry["path"] else ""
            lines.append(f"  - {entry['id']}{location}: {entry['reason']}")
    if command_results:
        lines.extend(["", "## Команды", ""])
        for result in command_results:
            changed = ", ".join(result.changed_paths) or "нет"
            lines.append(f"- {result.command_id}: код {result.returncode}; изменено: {changed}")
    if adapter_results:
        lines.extend(["", "## Адаптеры", ""])
        for result in adapter_results:
            changed = ", ".join(result.changed_paths) or "нет"
            lines.append(f"- {result.source_id} ({result.adapter}): {result.status}; {result.message}; изменено: {changed}")
    if index_counts is not None:
        lines.extend(["", "## Индексы", "", f"- единиц: {index_counts[0]}", f"- утверждений: {index_counts[1]}"])
    if operational_check is not None:
        lines.extend(
            [
                "",
                "## Предзапусковая проверка",
                "",
                f"- ошибки договора: {len(operational_check.contract_errors)}",
                f"- блокеры доступа: {len(operational_check.blockers)}",
                f"- предупреждения качества: {len(operational_check.quality_warnings)}",
                f"- подавлено правилом или метаданными: {len(operational_check.suppressed)}",
            ]
        )
        for finding in (*operational_check.blockers, *operational_check.quality_warnings)[:10]:
            lines.append(f"  - {finding.get('path')}:{finding.get('line')}: {finding.get('kind')}")
    lines.extend(["", "## Продолжение", "", "Следующий запуск начинает с указанных очередей. Необработанная единица остаётся в своей стадии, пока проектная команда или человек не изменят её состояние.", ""])
    return "\n".join(lines)


def report_path(root: Path, operations: dict[str, Any], explicit: Path | None) -> Path | None:
    if explicit is not None:
        return resolve_inside(root, str(explicit), "Путь отчёта")
    report = operations.get("report")
    if not isinstance(report, dict) or not isinstance(report.get("path"), str):
        return None
    return resolve_inside(root, report["path"], "report.path")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Спланировать или выполнить операции переносимого корпуса знаний.")
    parser.add_argument("corpus", type=Path, help="Корень корпуса с corpus.yml.")
    parser.add_argument("--operations", type=Path, help="Необязательный файл настроек операций.")
    parser.add_argument("--stage", default="source_sync", help="Стадия проектных команд для --run-commands.")
    parser.add_argument("--run-commands", action="store_true", help="Явно выполнить команды указанной стадии.")
    parser.add_argument("--run-adapters", action="store_true", help="Явно выполнить зарегистрированные адаптеры источников.")
    parser.add_argument("--source", action="append", default=[], help="Идентификатор источника для --run-adapters; можно повторять.")
    parser.add_argument("--rebuild-indexes", action="store_true", help="Атомарно пересобрать производные индексы.")
    parser.add_argument(
        "--operational-check",
        action="store_true",
        help="Запустить переносимую проверку tracked-слоя и добавить безопасную сводку в отчёт.",
    )
    parser.add_argument(
        "--operational-policy",
        type=Path,
        help="Репо-относительный YAML-файл правил подавления для --operational-check.",
    )
    parser.add_argument("--report", type=Path, help="Репо-относительный путь локального отчёта.")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Записать отчёт по пути report.path из настроек операций.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    corpus_root = resolve_inside(root, str(args.corpus), "Корень корпуса")
    corpus_paths(corpus_root)
    operations_path = resolve_inside(root, str(args.operations), "Файл настроек операций") if args.operations else None
    operations = load_operations(operations_path)
    items = load_items(corpus_root)
    queues = build_queues(items, normalized_artifacts(operations), root)
    command_results: list[CommandResult] = []
    adapter_results: list[AdapterResult] = []
    operational_check: OperationalCheckResult | None = None
    if args.operational_policy and not args.operational_check:
        raise OperationsError("--operational-policy требует --operational-check.")
    if args.operational_check:
        policy = resolve_inside(root, str(args.operational_policy), "Файл правил операционной проверки") if args.operational_policy else None
        operational_check = run_operational_check(root, corpus_root, policy)
        if operational_check.returncode:
            report = render_report(corpus_root, queues, command_results, None, adapter_results, operational_check)
            destination = report_path(root, operations, args.report) if args.write_report or args.report else None
            if destination:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(report, encoding="utf-8")
                print(f"Отчёт записан: {repo_relative(root, destination)}")
            else:
                print(report)
            return 1
    if args.run_commands:
        if not operations_path:
            raise OperationsError("Для --run-commands нужен параметр --operations.")
        command_results = run_commands(root, operations, args.stage)
        if any(result.returncode != 0 for result in command_results):
            print(render_report(corpus_root, queues, command_results, None, adapter_results))
            return 1
        items = load_items(corpus_root)
        queues = build_queues(items, normalized_artifacts(operations), root)
    if args.run_adapters:
        if not operations_path:
            raise OperationsError("Для --run-adapters нужен параметр --operations.")
        adapter_results = run_adapters(root, corpus_root, operations, set(args.source))
        items = load_items(corpus_root)
        queues = build_queues(items, normalized_artifacts(operations), root)
    index_counts = rebuild_indexes(corpus_root, root) if args.rebuild_indexes else None
    report = render_report(corpus_root, queues, command_results, index_counts, adapter_results, operational_check)
    destination = report_path(root, operations, args.report) if args.write_report or args.report else None
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")
        print(f"Отчёт записан: {repo_relative(root, destination)}")
    else:
        print(report)
    return 1 if operational_check is not None and operational_check.returncode else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OperationsError as exc:
        print(f"Ошибка операций корпуса: {exc}", file=sys.stderr)
        raise SystemExit(2)
